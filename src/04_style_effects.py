"""
04_style_effects.py
  (a) player level: weighted least squares  bb/100(days 11-20) ~ style(days 1-10), forest plot, BH-adjusted p
  (b) hand level  : realised EV of preflop LINES (fold / limp / open / call / 3-bet) by seat, 4.2M decisions
  (c) hand level  : open-raise sizing, continuation-bet EV
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
import matplotlib.pyplot as plt
from common import *

hands = load_hands()
split = load_split()

# =============================================================== (a) player-level WLS
F = ["PFR", "VPIP", "ThreeBet", "Steal", "Limp", "CBet", "FoldToCBet", "AF", "WTSD", "BetSize", "OpenSize", "Position_spread"]
X = split[F].copy(); X = X.fillna(X.median())
Xs = (X - X.mean()) / X.std()
rows = []
for f in F:
    m = sm.WLS(split.bb100_B, sm.add_constant(Xs[[f]]), weights=split.hands_B).fit(cov_type="HC1")
    rows.append(dict(feature=f, effect=m.params[f], lo=m.conf_int().loc[f, 0], hi=m.conf_int().loc[f, 1], p=m.pvalues[f]))
eff = pd.DataFrame(rows)
eff["p_bh"] = multipletests(eff.p, method="fdr_bh")[1]
eff = eff.sort_values("effect")
eff.to_csv(f"{RES}/style_effects_wls.csv", index=False)
full = sm.WLS(split.bb100_B, sm.add_constant(Xs), weights=split.hands_B).fit(cov_type="HC1")
print(eff.round(3).to_string())
print(f"multivariate WLS: R2 = {full.rsquared:.3f}, adj R2 = {full.rsquared_adj:.3f}, F-test p = {full.f_pvalue:.3f}")

fig, ax = plt.subplots(figsize=(8, 5))
y = np.arange(len(eff))
col = [C["green"] if (e > 0 and p < .05) else C["red"] if (e < 0 and p < .05) else C["grey"] for e, p in zip(eff.effect, eff.p)]
ax.errorbar(eff.effect, y, xerr=[eff.effect - eff.lo, eff.hi - eff.effect], fmt="none", ecolor=C["grey"], capsize=3, zorder=1)
ax.scatter(eff.effect, y, c=col, s=60, zorder=2)
ax.axvline(0, color=C["dark"], lw=1)
ax.set_yticks(y); ax.set_yticklabels(eff.feature)
ax.set_xlabel("change in out-of-sample bb/100 per +1 std-dev of the stat   (95% CI)")
ax.set_title("What style predicts profit? (days 1-10 style -> days 11-20 result)")
for yi, (e, p) in enumerate(zip(eff.effect, eff.p)):
    if p < .05:
        ax.text(eff.hi.iloc[yi] + .3, yi, f"p={p:.3f}", va="center", fontsize=8.5, color=C["dark"])
savefig("f5_style_effects.png")

# =============================================================== (b) preflop line EV
h = hands.copy()
def line(r):
    pass

cond = [
    h.bet3 == 1,
    h.open_n > 0,
    h.pfr == 1,
    h.limp == 1,
    h.vpip == 1,
    (h.pos == "BB") & (h.saw_flop == 1),
]
names = ["3-bet", "Open-raise", "4-bet+", "Limp", "Call a raise", "BB check"]
h["line"] = np.select(cond, names, default="Fold")
order = ["EP", "MP", "CO", "BTN", "SB", "BB"]
tab = (h.groupby(["pos", "line"]).net_bb.agg(["mean", "std", "count"]).reset_index())
tab["se"] = tab["std"] / np.sqrt(tab["count"])
tab.to_csv(f"{RES}/preflop_line_ev.csv", index=False)
share = h.groupby("pos").line.value_counts(normalize=True).unstack().reindex(order)

lines_show = ["Fold", "Limp", "Call a raise", "Open-raise", "3-bet"]
fig, ax = plt.subplots(figsize=(11, 4.6))
w = .16
cmap = {"Fold": C["grey"], "Limp": C["red"], "Call a raise": C["orange"], "Open-raise": C["green"], "3-bet": C["blue"]}
for j, ln in enumerate(lines_show):
    vals, errs = [], []
    for p in order:
        r = tab[(tab.pos == p) & (tab.line == ln)]
        if len(r) and r["count"].iloc[0] >= 2000:
            vals.append(r["mean"].iloc[0]); errs.append(1.96 * r["se"].iloc[0])
        else:
            vals.append(np.nan); errs.append(0)
    ax.bar(np.arange(len(order)) + (j - 2) * w, vals, w, yerr=errs, color=cmap[ln], label=ln, capsize=2)
ax.axhline(0, color=C["dark"], lw=1)
ax.set_xticks(range(len(order))); ax.set_xticklabels(order)
ax.set_ylabel("realised result (bb per hand played)")
ax.set_title("Raise or fold:  realised EV of each preflop line, by seat")
ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(.5, -.1), frameon=False)
savefig("f6_preflop_lines.png")
print(tab[tab["count"] > 5000].round(3).sort_values(["pos", "mean"]).to_string())

# paired check: same player, same seat, raise vs limp (removes "good players raise" selection)
pl = h[h.pos.isin(["EP", "MP", "CO", "BTN"]) & h.line.isin(["Limp", "Open-raise"])]
pv = pl.groupby(["player", "line"]).net_bb.agg(["mean", "count"]).unstack()
pv = pv[(pv[("count", "Limp")] >= 30) & (pv[("count", "Open-raise")] >= 30)]
diff = pv[("mean", "Open-raise")] - pv[("mean", "Limp")]
print(f"\nwithin-player: open-raise minus limp = {diff.mean():+.2f} bb/hand (n players={len(diff)}, "
      f"{(diff > 0).mean():.0%} of players earn more raising; t-test p={__import__('scipy.stats').stats.ttest_1samp(diff, 0).pvalue:.2g})")
pd.Series(dict(mean_diff=diff.mean(), n_players=len(diff), share_positive=(diff > 0).mean())).to_csv(f"{RES}/within_player_raise_vs_limp.csv")

# =============================================================== (c) open size + c-bet
op = h[(h.open_n > 0) & h.pos.isin(["EP", "MP", "CO", "BTN", "SB"])].copy()
op["size"] = op.open_size_sum / op.open_n
bins = [0, 2.2, 2.7, 3.2, 4.0, 100]
labs = ["<2.2x", "2.2-2.7x", "2.7-3.2x", "3.2-4x", ">4x"]
op["sz"] = pd.cut(op["size"], bins, labels=labs)
sz = op.groupby("sz", observed=True).net_bb.agg(["mean", "std", "count"])
sz["ci"] = 1.96 * sz["std"] / np.sqrt(sz["count"])
print(sz.round(3))
sz.to_csv(f"{RES}/open_size_ev.csv")

cb = h[(h.cbet_opp == 1)].copy()
cb["act"] = np.where(cb.cbet == 1, "C-bet", "Check")
c_t = cb.groupby("act").net_bb.agg(["mean", "std", "count"]); c_t["ci"] = 1.96 * c_t["std"] / np.sqrt(c_t["count"])
c_t.to_csv(f"{RES}/cbet_ev.csv")
print(c_t.round(3))

fig, ax = plt.subplots(1, 2, figsize=(10.5, 4))
ax[0].bar(sz.index.astype(str), sz["mean"], yerr=sz["ci"], color=C["blue"], capsize=4)
ax[0].set_title("Open-raise size (x big blind)"); ax[0].set_ylabel("bb per open-raise")
ax[0].axhline(0, color=C["dark"], lw=1)
ax[1].bar(c_t.index, c_t["mean"], yerr=c_t["ci"], color=[C["green"], C["grey"]], capsize=4)
ax[1].set_title("Preflop raiser on the flop (checked to):"); ax[1].axhline(0, color=C["dark"], lw=1)
for i, (m, n) in enumerate(zip(c_t["mean"], c_t["count"])):
    ax[1].text(i, m + .05, f"{m:+.2f}\n(n={n:,})", ha="center", fontsize=9)
savefig("f7_sizing_cbet.png")
