"""
01_parse.py  --  PHH (Poker Hand History) HandHQ files  ->  one row per (player, hand)

Source: uoftcprg/phh-dataset, data/handhq/PS-2009-07-01_2009-07-23_50NLH_OBFU
        (PokerStars, NL50 = $0.25/$0.50 no-limit hold'em, July 2009, anonymised player ids)

For every hand we replay the action list, rebuild the pot, and emit per-player stats:
  position, stack, net result (in big blinds, pre-rake) and the usual "HUD" counters
  (VPIP, PFR, 3-bet, steal, c-bet, fold-to-c-bet, aggression, showdown ...).
Hole cards are hidden in this dataset (only some are shown at showdown), so every
feature is built from observable BEHAVIOUR only.
"""
import sys, glob, tomllib, os
from multiprocessing import Pool
import numpy as np
import pandas as pd

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "player_hands.pkl")


from itertools import combinations
RANKS = {c: i for i, c in enumerate("23456789TJQKA", start=2)}


def rank5(cards):
    """cards: list of 5 (rank, suit). Returns comparable tuple (category, tiebreakers...)."""
    rs = sorted((c[0] for c in cards), reverse=True)
    flush = len({c[1] for c in cards}) == 1
    uniq = sorted(set(rs), reverse=True)
    straight_hi = None
    if len(uniq) == 5:
        if uniq[0] - uniq[4] == 4:
            straight_hi = uniq[0]
        elif uniq == [14, 5, 4, 3, 2]:
            straight_hi = 5
    cnt = {}
    for r in rs:
        cnt[r] = cnt.get(r, 0) + 1
    groups = sorted(cnt.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    shape = [g[1] for g in groups]
    tb = [g[0] for g in groups]
    if straight_hi and flush: return (8, straight_hi)
    if shape == [4, 1]: return (7, *tb)
    if shape == [3, 2]: return (6, *tb)
    if flush: return (5, *rs)
    if straight_hi: return (4, straight_hi)
    if shape == [3, 1, 1]: return (3, *tb)
    if shape == [2, 2, 1]: return (2, *tb)
    if shape == [2, 1, 1, 1]: return (1, *tb)
    return (0, *rs)


def best7(cards):
    return max(rank5(list(c)) for c in combinations(cards, 5))


def parse_cards(s):
    return [(RANKS[s[k]], s[k + 1]) for k in range(0, len(s), 2)]


def settle_showdown(tot, folded, shown, board, n):
    """Side-pot aware settlement from revealed cards. Returns list of payouts (pre-rake) or None."""
    if len(board) != 5:
        return None
    strength = {}
    for k, hole in shown.items():
        if folded[k]:
            continue
        strength[k] = best7(hole + board)
    if not strength:
        return None
    levels = sorted({c for c in tot if c > 0})
    pay = [0.0] * n
    prev = 0.0
    for lv in levels:
        contrib = [min(c, lv) - min(c, prev) for c in tot]
        pot_lv = sum(contrib)
        elig = [k for k in range(n) if not folded[k] and tot[k] >= lv - 1e-9]
        shown_elig = [k for k in elig if k in strength]
        if not elig:
            # everyone eligible folded: dead money goes to next level winners -> keep simple
            prev = lv
            continue
        if len(elig) == 1:
            pay[elig[0]] += pot_lv            # uncalled / sole-eligible
        else:
            if not shown_elig:
                return None
            best = max(strength[k] for k in shown_elig)
            winners = [k for k in shown_elig if strength[k] == best]
            for k in winners:
                pay[k] += pot_lv / len(winners)
        prev = lv
    return pay


def position_names(n):
    """p1=SB, p2=BB, ..., p_n = BTN (PHH/HandHQ ordering)."""
    if n == 2:
        return ["HU_SB", "HU_BB"]
    names = ["SB", "BB"] + [None] * (n - 2)
    others = list(range(2, n))                 # UTG ... BTN
    names[n - 1] = "BTN"
    if n >= 4:
        names[n - 2] = "CO"
    early_mid = [i for i in others if names[i] is None]
    half = (len(early_mid) + 1) // 2
    for k, i in enumerate(early_mid):
        names[i] = "EP" if k < half else "MP"
    return names


def parse_hand(h):
    pl = h["players"]
    n = len(pl)
    if n < 2:
        return []
    stacks = [float(x) for x in h["starting_stacks"]]
    blinds = [float(x) for x in h["blinds_or_straddles"]]
    bb = max(blinds)
    if bb <= 0 or len(blinds) != n or len(stacks) != n:
        return []
    pos = position_names(n)

    tot = [min(b, s) for b, s in zip(blinds, stacks)]      # chips committed this hand
    sb_ = list(tot)                                       # chips committed this street
    folded = [False] * n
    street = 0
    raises = 0                       # raise count preflop
    last_raiser = None               # preflop aggressor
    opener = None
    entered = [False] * n            # voluntarily put money in preflop
    # per-player counters
    R = [dict(vpip=0, pfr=0, limp=0, opp3=0, bet3=0, opp_f3=0, f3=0, steal_opp=0, steal=0,
              saw_flop=0, cbet_opp=0, cbet=0, fcb_opp=0, fcb=0,
              post_bet=0, post_raise=0, post_call=0, post_check=0, post_fold=0,
              fold_opp=0, bet_frac_sum=0.0, bet_frac_n=0, open_size_sum=0.0, open_n=0,
              acted_pre=0) for _ in range(n)]
    flop_first_bet_by = None         # who made first bet on flop
    flop_aggr_acted = False
    voluntary_before = False         # any limp/raise so far preflop (for steal detection)
    to_call_pending_f3 = {}          # opener -> awaiting action vs 3bet
    board = []
    shown = {}

    for a in h["actions"]:
        t = a.split()
        if t[0] == "d":
            if t[1] == "db":
                street += 1
                board += parse_cards(t[2])
                sb_ = [0.0] * n
                if street == 1:
                    for i in range(n):
                        if not folded[i]:
                            R[i]["saw_flop"] = 1
            continue
        i = int(t[0][1:]) - 1
        if i < 0 or i >= n:
            continue
        kind = t[1]
        if kind == "sm":
            if "?" not in t[2]:
                shown[i] = parse_cards(t[2])
            continue
        cur_max = max(sb_)
        to_call = cur_max - sb_[i]
        room = stacks[i] - tot[i]
        pot_before = sum(tot)
        r = R[i]

        if street == 0:
            r["acted_pre"] = 1
            facing_raises = raises
            # --- 3-bet / fold-to-3bet opportunities
            if facing_raises == 1:
                r["opp3"] = 1
            if i in to_call_pending_f3 and facing_raises >= 2:
                r["opp_f3"] = 1
                if kind == "f":
                    r["f3"] = 1
                del to_call_pending_f3[i]
            # --- steal opportunity: folded to me (no voluntary action yet) from CO/BTN/SB
            if (not voluntary_before) and facing_raises == 0 and pos[i] in ("CO", "BTN", "SB", "HU_SB"):
                r["steal_opp"] = 1
            if kind == "f":
                folded[i] = True
            elif kind == "cc":
                amt = min(to_call, room)
                if to_call > 0:
                    r["vpip"] = 1
                    entered[i] = True
                    if facing_raises == 0:
                        r["limp"] = 1
                        voluntary_before = True
                sb_[i] += amt; tot[i] += amt
            elif kind == "cbr":
                x = float(t[2])
                amt = min(x - sb_[i], room)
                if facing_raises == 0:
                    opener = i
                    r["open_size_sum"] += x / bb; r["open_n"] += 1
                    to_call_pending_f3[i] = True
                    if r["steal_opp"]:
                        r["steal"] = 1
                if facing_raises == 1:
                    r["bet3"] = 1
                r["vpip"] = 1; r["pfr"] = 1
                entered[i] = True
                raises += 1
                voluntary_before = True
                last_raiser = i
                sb_[i] += amt; tot[i] += amt
        else:
            facing_bet = to_call > 1e-9
            if street == 1:
                if i == last_raiser and flop_first_bet_by is None and not facing_bet:
                    r["cbet_opp"] = 1
                    if kind == "cbr":
                        r["cbet"] = 1
                if (flop_first_bet_by is not None and flop_first_bet_by == last_raiser
                        and i != last_raiser and facing_bet and r["fcb_opp"] == 0):
                    r["fcb_opp"] = 1
                    if kind == "f":
                        r["fcb"] = 1
                if kind == "cbr" and flop_first_bet_by is None:
                    flop_first_bet_by = i
            if kind == "f":
                r["post_fold"] += 1; r["fold_opp"] += 1
                folded[i] = True
            elif kind == "cc":
                if facing_bet:
                    r["post_call"] += 1; r["fold_opp"] += 1
                    amt = min(to_call, room)
                else:
                    r["post_check"] += 1
                    amt = 0.0
                sb_[i] += amt; tot[i] += amt
            elif kind == "cbr":
                x = float(t[2])
                amt = min(x - sb_[i], room)
                if facing_bet:
                    r["post_raise"] += 1; r["fold_opp"] += 1
                else:
                    r["post_bet"] += 1
                    if pot_before > 0:
                        r["bet_frac_sum"] += amt / pot_before; r["bet_frac_n"] += 1
                sb_[i] += amt; tot[i] += amt

    # ---------------- result ----------------
    alive = [k for k in range(n) if not folded[k]]
    s = sorted(tot, reverse=True)
    eff = [min(c, s[1]) for c in tot]                    # uncalled excess is returned
    pot = sum(eff)
    net = [-e for e in eff]
    showdown = len(alive) >= 2
    settled_by_eval = False
    w = h.get("winnings") or [0] * n
    if showdown:
        sw = sum(w)
        if sw > 0:
            scale = pot / sw                              # winnings are after-rake: rescale to pre-rake pot
            for k in range(n):
                net[k] += w[k] * scale
        else:                                             # winnings stripped -> settle from revealed cards
            pay = settle_showdown(tot, folded, shown, board, n)
            if pay is None:
                return []
            net = [pay[k] - tot[k] for k in range(n)]     # payouts include the returned uncalled bet
            settled_by_eval = True
    else:
        if len(alive) != 1:
            return []
        net[alive[0]] += pot

    rows = []
    for k in range(n):
        r = R[k]
        row = dict(
            hand=h["hand"], day=h["day"], player=pl[k], pos=pos[k], n_players=n,
            stack_bb=stacks[k] / bb, net_bb=net[k] / bb,
            saw_showdown=int(showdown and not folded[k]),
            won_hand=int(net[k] > 1e-9),
            pot_bb=pot / bb, evaluated=int(settled_by_eval),
        )
        row.update(r)
        row["wtsd"] = int(showdown and not folded[k] and r["saw_flop"] == 1)
        rows.append(row)
    return rows


def parse_file(path):
    try:
        d = tomllib.loads(open(path, encoding="utf-8").read())
    except Exception as e:                                   # corrupt file
        sys.stderr.write(f"skip {path}: {e}\n")
        return []
    out = []
    for h in d.values():
        try:
            out.extend(parse_hand(h))
        except Exception as e:
            sys.stderr.write(f"hand err {e}\n")
    return out


if __name__ == "__main__":
    files = sorted(glob.glob(os.path.join(RAW, "ps50_*.phhs")))
    print("files:", len(files))
    with Pool() as p:
        chunks = p.map(parse_file, files, chunksize=4)
    rows = [r for c in chunks for r in c]
    df = pd.DataFrame(rows)
    df.to_pickle(OUT)
    print(df.shape, "hands:", df["hand"].nunique(), "players:", df["player"].nunique())
    print("net_bb sum (should be ~0):", df["net_bb"].sum())
    print(df.groupby("pos")["net_bb"].agg(["mean", "count"]))
