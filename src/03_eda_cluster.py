"""
03_eda_cluster.py  --  EDA + unsupervised player archetypes (k-means vs Ward hierarchical)

Outputs figures f1..f5 and results/cluster_*.csv
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, dendrogram
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, adjusted_rand_score
from common import *

rng = np.random.default_rng(513)
hands = load_hands()
split = load_split()

# ------------------------------------------------------------------ F1: data sanity -> EV by seat
order = ["EP", "MP", "CO", "BTN", "SB", "BB"]
g = hands.groupby("pos")["net_bb"].agg(["mean", "std", "count"]).loc[order]
g["ci"] = 1.96 * g["std"] / np.sqrt(g["count"])
fig, ax = plt.subplots(figsize=(7, 4))
cols = [C["green"] if v > 0 else C["red"] for v in g["mean"]]
ax.bar(order, g["mean"], yerr=g["ci"], color=cols, capsize=4)
ax.axhline(0, color=C["dark"], lw=1)
ax.set_ylabel("average result (big blinds / hand)")
ax.set_title("Seat matters: BTN earns, blinds bleed")
for i, (m, c) in enumerate(zip(g["mean"], g["ci"])):
    ax.text(i, m + (c + 0.02 if m > 0 else -c - 0.06), f"{m:+.2f}", ha="center", fontsize=10)
savefig("f1_position_ev.png")
g.to_csv(f"{RES}/position_ev.csv")

# ------------------------------------------------------------------ F2: noise / persistence
r = split.bb100_A.corr(split.bb100_B)
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
ax[0].scatter(split.bb100_A, split.bb100_B, s=14, alpha=.55, color=C["blue"])
ax[0].axhline(0, color=C["dark"], lw=.8); ax[0].axvline(0, color=C["dark"], lw=.8)
ax[0].set_xlabel("bb/100 in days 1-10"); ax[0].set_ylabel("bb/100 in days 11-20")
ax[0].set_title(f"Results do not persist  (r = {r:+.2f})")

# reliability: how much of the observed spread is skill vs luck?
per_hand_sd = hands.net_bb.std()                       # ~ 9-10 bb per hand
se = 100 * per_hand_sd / np.sqrt(split.hands_B)         # luck SD per player in bb/100
var_obs = split.bb100_B.var()
var_luck = (se ** 2).mean()
var_skill = max(var_obs - var_luck, 0)
rel = var_skill / var_obs
ax[1].bar(["luck", "skill"], [var_luck ** .5, var_skill ** .5], color=[C["grey"], C["green"]])
ax[1].set_ylabel("std-dev in bb/100"); ax[1].set_title(f"Variance decomposition (reliability = {rel:.0%})")
for i, v in enumerate([var_luck ** .5, var_skill ** .5]):
    ax[1].text(i, v + .4, f"{v:.1f}", ha="center")
savefig("f2_noise.png")
pd.Series(dict(corr_A_B=r, per_hand_sd_bb=per_hand_sd, luck_sd=var_luck ** .5,
               skill_sd=var_skill ** .5, reliability=rel, n_players=len(split))).to_csv(f"{RES}/noise_decomposition.csv")
print(f"corr A-B {r:.3f} | luck sd {var_luck**.5:.1f} skill sd {var_skill**.5:.1f} reliability {rel:.2f}")

# ------------------------------------------------------------------ F3: VPIP vs PFR landscape
allp = pd.read_csv(f"{DATA}/players_all.csv", index_col=0)
fig, ax = plt.subplots(figsize=(7.2, 5.4))
sc = ax.scatter(allp.VPIP, allp.PFR, c=allp.bb100.clip(-40, 40), cmap="RdYlGn", s=allp.hands / 40,
                edgecolor="k", linewidth=.3, alpha=.85)
ax.plot([0, 60], [0, 60], color=C["grey"], ls="--", lw=1)
ax.set_xlim(0, 60); ax.set_ylim(0, 50)
ax.set_xlabel("VPIP  (% hands voluntarily played)"); ax.set_ylabel("PFR  (% hands raised preflop)")
ax.set_title("Who wins? Players with >= 1000 hands")
plt.colorbar(sc, label="bb/100 (clipped at +/-40)")
savefig("f3_vpip_pfr.png")

# ------------------------------------------------------------------ clustering
F = STYLE_FEATURES                                       # for profiling
CF = CLUSTER_FEATURES                                    # for clustering (chosen by silhouette + seed stability)
X = split[CF].copy(); X = X.fillna(X.median())
X = np.log1p(X.clip(lower=0))                            # skewed rates -> log scale
Z = StandardScaler().fit_transform(X)

ks = list(range(2, 9))
sil_km, sil_ward = [], []
for k in ks:
    sil_km.append(silhouette_score(Z, KMeans(k, n_init=30, random_state=0).fit_predict(Z)))
    sil_ward.append(silhouette_score(Z, AgglomerativeClustering(k, linkage="ward").fit_predict(Z)))
K = 4 + int(np.argmax(sil_km[2:]))                      # best silhouette among k>=4 (poker has >= 4 classic archetypes)
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
ax[0].plot(ks, sil_km, "o-", label="k-means"); ax[0].plot(ks, sil_ward, "s-", label="Ward")
ax[0].axvline(K, color=C["grey"], ls=":"); ax[0].set_xlabel("k"); ax[0].set_ylabel("silhouette")
ax[0].set_title("Choosing k"); ax[0].legend()
dendrogram(linkage(Z, "ward"), truncate_mode="lastp", p=30, no_labels=True, ax=ax[1], color_threshold=0, above_threshold_color=C["blue"])
ax[1].set_title("Ward dendrogram (truncated)"); ax[1].grid(False)
savefig("f4a_choose_k.png")
print("silhouette kmeans", np.round(sil_km, 3), "ward", np.round(sil_ward, 3), "-> K =", K)

km = KMeans(K, n_init=50, random_state=0).fit(Z)
ward = AgglomerativeClustering(K, linkage="ward").fit(Z)
ari = adjusted_rand_score(km.labels_, ward.labels_)
seeds = [adjusted_rand_score(km.labels_, KMeans(K, n_init=10, random_state=s).fit_predict(Z)) for s in range(10)]
print(f"ARI k-means vs Ward = {ari:.2f};  k-means seed stability = {np.mean(seeds):.2f}")

split["cl"] = km.labels_


def name_cluster(row):
    if row.CBet < 20: return "Never c-bets (outliers)"
    if row.VPIP >= 22 and row.PFR < 10: return "Loose-passive"
    if row.VPIP < 13: return "Nit (very tight)"
    if row.PFR >= 13: return "Aggressive regular"
    return "Tight-passive"


prof = split.groupby("cl")[F + ["TableSize"]].mean()
prof["n_players"] = split.groupby("cl").size()
prof["name"] = prof.apply(name_cluster, axis=1)
if prof["name"].duplicated().any():                      # disambiguate, keep order by VPIP
    prof["name"] = [f"{n} #{i+1}" if (prof["name"] == n).sum() > 1 else n
                    for i, n in enumerate(prof["name"])]
split["archetype"] = split.cl.map(prof["name"])

# ------------------------------------------------------------------ out-of-sample profit per archetype
pb = hands[(hands.day > 10) & hands.player.isin(split.index)]
ps = pb.groupby("player").net_bb.agg(net="sum", n="size").reindex(split.index)
split["net_B"], split["n_B"] = ps.net, ps.n


def pooled(sub):  # hands-weighted bb/100
    return 100 * sub.net_B.sum() / sub.n_B.sum()


rows = []
for c, sub in split.groupby("cl"):
    boots = [pooled(sub.iloc[rng.integers(0, len(sub), len(sub))]) for _ in range(2000)]
    rows.append(dict(cl=c, archetype=prof.loc[c, "name"], players=len(sub), hands_B=int(sub.n_B.sum()),
                     bb100_B=pooled(sub), lo=np.percentile(boots, 2.5), hi=np.percentile(boots, 97.5)))
res = pd.DataFrame(rows).set_index("cl").join(prof[F + ["TableSize"]])

# permutation test: do archetypes differ in out-of-sample bb/100 more than random labels would?
def spread(lbl):
    t = pd.DataFrame({"c": lbl, "net": split.net_B.values, "n": split.n_B.values}).groupby("c")[["net", "n"]].sum()
    v = 100 * t.net / t.n
    return float(np.average((v - v.mean()) ** 2, weights=t.n))


obs = spread(split.cl.values)
perm = [spread(rng.permutation(split.cl.values)) for _ in range(3000)]
p_perm = (np.sum(np.array(perm) >= obs) + 1) / (len(perm) + 1)
print(f"permutation test on archetype spread: p = {p_perm:.4f}")
res.to_csv(f"{RES}/cluster_profit.csv")
split[["cl", "archetype"]].to_csv(f"{RES}/player_archetypes.csv")
print(res.round(1).to_string())

# PCA map
pca = PCA(2).fit(Z); P = pca.transform(Z)
fig, ax = plt.subplots(1, 2, figsize=(13.5, 4.8), gridspec_kw=dict(width_ratios=[1, 1.15]))
for i, c in enumerate(sorted(prof.index)):
    m = split.cl.values == c
    ax[0].scatter(P[m, 0], P[m, 1], s=18, alpha=.7, color=PAL[i], label=f"{prof.loc[c,'name']} (n={m.sum()})")
ax[0].set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.0%})"); ax[0].set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.0%})")
ax[0].set_title("Player styles (PCA of 6 clustering stats)"); ax[0].legend(fontsize=9)
order_ = res.sort_values("bb100_B").index
yy = np.arange(len(order_))
cols = [PAL[sorted(prof.index).index(c)] for c in order_]
ax[1].barh(yy, res.loc[order_, "bb100_B"], color=cols,
           xerr=[res.loc[order_, "bb100_B"] - res.loc[order_, "lo"], res.loc[order_, "hi"] - res.loc[order_, "bb100_B"]], capsize=4)
ax[1].set_yticks(yy); ax[1].set_yticklabels([res.loc[c, "archetype"] for c in order_])
ax[1].axvline(0, color=C["dark"], lw=1)
ax[1].set_xlabel("out-of-sample bb/100 (days 11-20), 95% bootstrap CI")
ax[1].set_title(f"Out-of-sample profit by archetype (perm. p = {p_perm:.2f})", fontsize=11)
ax[1].set_xlim(-2, 32)
savefig("f4_clusters.png")

# profile heat-map (z-scores of centroids)
Xp = split[F].copy(); Xp = Xp.fillna(Xp.median())
cent = pd.DataFrame(StandardScaler().fit(Xp).transform(Xp), index=Xp.index, columns=F).groupby(split.cl).mean()
cent.index = [prof.loc[c, "name"] for c in cent.index]
fig, ax = plt.subplots(figsize=(9, 3.2))
im = ax.imshow(cent.values, cmap="coolwarm", vmin=-2, vmax=2, aspect="auto")
ax.set_xticks(range(len(F))); ax.set_xticklabels(F, rotation=35, ha="right")
ax.set_yticks(range(len(cent))); ax.set_yticklabels(cent.index); ax.grid(False)
for i in range(cent.shape[0]):
    for j in range(cent.shape[1]):
        ax.text(j, i, f"{cent.values[i,j]:+.1f}", ha="center", va="center", fontsize=8)
plt.colorbar(im, label="z-score vs. all players")
ax.set_title("Archetype fingerprints")
savefig("f4b_archetype_heatmap.png")
