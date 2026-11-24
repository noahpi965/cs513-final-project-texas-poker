"""
02_features.py  --  player-hand rows  ->  one row per player ("style profile")

Design (avoids the circularity of using the same hands for style and profit):
    Period A = days  1-10   -> STYLE features  (VPIP, PFR, 3-bet, c-bet, aggression, ...)
    Period B = days 11-20   -> OUTCOME label   (bb/100 = big blinds won per 100 hands, pre-rake)
Only players with >= MIN_A hands in A and >= MIN_B hands in B are kept.
A second table (all 20 days) is saved for purely descriptive work (clustering, EDA).
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(__file__)
SPLIT_DAY, MIN_A, MIN_B = 10, 100, 100


def safe_div(a, b):
    return np.where(b > 0, a / np.where(b > 0, b, 1), np.nan)


def style_features(g):
    """g = player-hand rows -> aggregated style statistics (DataFrame indexed by player)."""
    s = g.groupby("player").agg(
        hands=("hand", "size"),
        vpip_n=("vpip", "sum"), pfr_n=("pfr", "sum"), limp_n=("limp", "sum"),
        opp3=("opp3", "sum"), bet3=("bet3", "sum"),
        opp_f3=("opp_f3", "sum"), f3=("f3", "sum"),
        steal_opp=("steal_opp", "sum"), steal=("steal", "sum"),
        saw_flop=("saw_flop", "sum"), wtsd_n=("wtsd", "sum"),
        cbet_opp=("cbet_opp", "sum"), cbet=("cbet", "sum"),
        fcb_opp=("fcb_opp", "sum"), fcb=("fcb", "sum"),
        pb=("post_bet", "sum"), pr=("post_raise", "sum"), pc=("post_call", "sum"),
        pk=("post_check", "sum"), pf=("post_fold", "sum"), fold_opp=("fold_opp", "sum"),
        bfs=("bet_frac_sum", "sum"), bfn=("bet_frac_n", "sum"),
        osz=("open_size_sum", "sum"), on=("open_n", "sum"),
        stack_bb=("stack_bb", "mean"), n_players=("n_players", "mean"),
    )
    f = pd.DataFrame(index=s.index)
    f["hands"] = s.hands
    f["VPIP"] = 100 * s.vpip_n / s.hands
    f["PFR"] = 100 * s.pfr_n / s.hands
    f["VPIP_PFR_gap"] = f.VPIP - f.PFR
    f["Limp"] = 100 * s.limp_n / s.hands
    f["ThreeBet"] = 100 * safe_div(s.bet3, s.opp3)
    f["FoldTo3Bet"] = 100 * safe_div(s.f3, s.opp_f3)
    f["Steal"] = 100 * safe_div(s.steal, s.steal_opp)
    f["CBet"] = 100 * safe_div(s.cbet, s.cbet_opp)
    f["FoldToCBet"] = 100 * safe_div(s.fcb, s.fcb_opp)
    f["AF"] = safe_div(s.pb + s.pr, s.pc)                       # aggression factor (bets+raises)/calls
    f["AFq"] = 100 * safe_div(s.pb + s.pr, s.pb + s.pr + s.pc + s.pk + s.pf)
    f["FoldToBet"] = 100 * safe_div(s.pf, s.fold_opp)           # postflop fold when facing a bet
    f["SawFlop"] = 100 * s.saw_flop / s.hands
    f["WTSD"] = 100 * safe_div(s.wtsd_n, s.saw_flop)
    f["BetSize"] = safe_div(s.bfs, s.bfn)                       # avg postflop bet / pot
    f["OpenSize"] = safe_div(s.osz, s.on)                       # avg open-raise size in bb
    f["StackBB"] = s.stack_bb
    f["TableSize"] = s.n_players
    # positional discipline
    for name, poss in (("VPIP_early", ["EP"]), ("VPIP_late", ["CO", "BTN"]), ("VPIP_blinds", ["SB", "BB"])):
        sub = g[g.pos.isin(poss)].groupby("player")["vpip"].mean() * 100
        f[name] = sub
    f["Position_spread"] = f.VPIP_late - f.VPIP_early          # how much tighter UTG vs BTN
    return f


def main():
    df = pd.read_pickle(os.path.join(HERE, "..", "data", "player_hands.pkl"))
    df = df[df.n_players >= 3].copy()          # scope: ring games (3-9 players); heads-up is a different game

    A = df[df.day <= SPLIT_DAY]
    B = df[df.day > SPLIT_DAY]
    fa = style_features(A)
    nb = B.groupby("player").agg(hands_B=("net_bb", "size"), net_B=("net_bb", "sum"))
    out = fa.join(nb, how="inner")
    out["bb100_B"] = 100 * out.net_B / out.hands_B
    out["bb100_A"] = 100 * A.groupby("player")["net_bb"].mean().reindex(out.index)
    out = out[(out.hands >= MIN_A) & (out.hands_B >= MIN_B)].rename(columns={"hands": "hands_A"})
    out["win_B"] = (out.bb100_B > 0).astype(int)
    out.to_csv(os.path.join(HERE, "..", "data", "players_split.csv"))
    print("split table:", out.shape, " winners in B:", out.win_B.mean().round(3))

    # descriptive table: all days, players with >=1000 hands
    fall = style_features(df)
    fall["bb100"] = 100 * df.groupby("player")["net_bb"].mean()
    fall = fall[fall.hands >= 1000]
    fall.to_csv(os.path.join(HERE, "..", "data", "players_all.csv"))
    print("all-days table:", fall.shape)
    print(out[["VPIP", "PFR", "AF", "CBet", "WTSD", "bb100_A", "bb100_B"]].describe().round(2))


if __name__ == "__main__":
    main()
