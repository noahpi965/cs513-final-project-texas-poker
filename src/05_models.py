"""
05_models.py -- supervised comparison with the CS513 toolbox (+ gradient boosting as the "beyond class" model)

 E1  PLAYER level : style (days 1-10)  ->  winner / loser (days 11-20)
 E2  HAND   level : seat + line + table + player style  ->  does this played hand make money?
                    (CV is grouped by player, so models are tested on players they have never seen)
 E3  ablation     : how much does PLAYER STYLE add on top of seat + line?
"""
import time, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import RepeatedStratifiedKFold, GroupKFold, GridSearchCV, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.dummy import DummyClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score
from common import *

warnings.filterwarnings("ignore")
rng = np.random.default_rng(513)
STYLE = STYLE_FEATURES + ["Position_spread", "BetSize", "OpenSize", "StackBB", "TableSize"]


def zoo(seed=0, tuned=None):
    """The model line-up. `tuned` overrides hyper-parameters picked on a separate tuning set."""
    t = tuned or {}
    imp = lambda: SimpleImputer(strategy="median")
    return {
        "Majority (baseline)": DummyClassifier(strategy="prior"),
        "Logistic regression": make_pipeline(imp(), StandardScaler(), LogisticRegression(C=t.get("lr_C", 0.1), max_iter=500)),
        "kNN": make_pipeline(imp(), StandardScaler(), KNeighborsClassifier(n_neighbors=t.get("knn_k", 50), weights="distance" if t.get("knn_w") else "uniform")),
        "Naive Bayes": make_pipeline(imp(), GaussianNB()),
        "CART (gini)": make_pipeline(imp(), DecisionTreeClassifier(max_depth=t.get("cart_d", 4), min_samples_leaf=t.get("leaf", 20), random_state=seed)),
        "C5.0-style (entropy)": make_pipeline(imp(), DecisionTreeClassifier(criterion="entropy", max_depth=t.get("c5_d", 4), min_samples_leaf=t.get("leaf", 20), random_state=seed)),
        "Random forest": make_pipeline(imp(), RandomForestClassifier(300, min_samples_leaf=t.get("rf_leaf", 10), max_features="sqrt", n_jobs=-1, random_state=seed)),
        "ANN (MLP 16-8)": make_pipeline(imp(), StandardScaler(), MLPClassifier((16, 8), alpha=t.get("ann_a", 1e-2), early_stopping=True, max_iter=400, random_state=seed)),
        "Gradient boosting": make_pipeline(imp(), HistGradientBoostingClassifier(max_depth=3, learning_rate=.05, max_iter=200, random_state=seed)),
    }


# =============================================================== E1: player level
split = load_split()
Xp = split[STYLE]; yp = split.win_B
base = yp.mean()
print(f"E1: {len(split)} players, {base:.1%} winners in days 11-20 (majority baseline)")
cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=0)
res1 = []
for name, mdl in zoo().items():
    s = cross_validate(mdl, Xp, yp, cv=cv, scoring=["roc_auc", "accuracy"], n_jobs=1)
    res1.append(dict(model=name, auc=s["test_roc_auc"].mean(), auc_sd=s["test_roc_auc"].std(),
                     acc=s["test_accuracy"].mean(), acc_sd=s["test_accuracy"].std()))
    print(f"  {name:24s} AUC {res1[-1]['auc']:.3f} +/- {res1[-1]['auc_sd']:.3f}   acc {res1[-1]['acc']:.3f}")
r1 = pd.DataFrame(res1); r1.to_csv(f"{RES}/E1_player_models.csv", index=False)

# =============================================================== E2: hand level
hands = load_hands()
B = hands[(hands.day > 10) & hands.player.isin(split.index) & (hands.vpip == 1)].copy()
B["line"] = np.select([B.bet3 == 1, B.open_n > 0, B.pfr == 1, B.limp == 1], ["3bet", "open", "4bet", "limp"], default="call")
for ln in ["limp", "call", "open", "3bet", "4bet"]:
    B[f"line_{ln}"] = (B.line == ln).astype(int)
for p in ["EP", "MP", "CO", "BTN", "SB", "BB"]:
    B[f"seat_{p}"] = (B.pos == p).astype(int)
B["open_size"] = np.where(B.open_n > 0, B.open_size_sum / B.open_n.clip(lower=1), 0.0)
B["log_stack"] = np.log(B.stack_bb.clip(lower=1))
B = B.join(split[STYLE].add_prefix("s_"), on="player")
B["y"] = (B.net_bb > 0).astype(int)

SIT = [c for c in B.columns if c.startswith("seat_") or c.startswith("line_")] + ["n_players", "log_stack", "open_size"]
STY = [f"s_{c}" for c in STYLE]
print(f"\nE2: {len(B):,} voluntarily-played hands by {B.player.nunique()} players; P(hand wins money) = {B.y.mean():.1%}")

# --- tune on a disjoint set of players, evaluate on the rest
players = B.player.unique(); rng.shuffle(players)
tune_p, eval_p = set(players[: len(players) // 4]), set(players[len(players) // 4:])
N_TUNE, N_EVAL = 25_000, 60_000
tune = B[B.player.isin(tune_p)].sample(N_TUNE, random_state=1)
evl = B[B.player.isin(eval_p)].sample(N_EVAL, random_state=2)
FEAT = SIT + STY

grids = {
    "kNN": ("knn_k", [25, 75, 200]), "CART (gini)": ("cart_d", [3, 5, 8]),
    "C5.0-style (entropy)": ("c5_d", [3, 5, 8]), "Random forest": ("rf_leaf", [5, 20, 60]),
    "ANN (MLP 16-8)": ("ann_a", [1e-3, 1e-2, 1e-1]),
}
tuned = {}
gk3 = GroupKFold(3)
for name, (key, vals) in grids.items():
    best, bs = None, -1
    for v in vals:
        mdl = zoo(tuned={**tuned, key: v})[name]
        sc = cross_validate(mdl, tune[FEAT], tune.y, groups=tune.player, cv=gk3, scoring="roc_auc")["test_score"].mean()
        if sc > bs: best, bs = v, sc
    tuned[key] = best
    print(f"  tuned {name}: {key} = {best}  (tune AUC {bs:.3f})")

gk = GroupKFold(5)
res2 = []
for name, mdl in zoo(tuned=tuned).items():
    t0 = time.time()
    s = cross_validate(mdl, evl[FEAT], evl.y, groups=evl.player, cv=gk, scoring=["roc_auc", "accuracy"])
    res2.append(dict(model=name, auc=s["test_roc_auc"].mean(), auc_sd=s["test_roc_auc"].std(),
                     acc=s["test_accuracy"].mean(), acc_sd=s["test_accuracy"].std(), seconds=time.time() - t0))
    print(f"  {name:24s} AUC {res2[-1]['auc']:.3f} +/- {res2[-1]['auc_sd']:.3f}   acc {res2[-1]['acc']:.3f}   {res2[-1]['seconds']:.0f}s")
r2 = pd.DataFrame(res2); r2.to_csv(f"{RES}/E2_hand_models.csv", index=False)

# =============================================================== E3: ablation (RF + GBM)
abl = []
for label, cols in {"Seat + line only": SIT, "Player style only": STY, "Seat + line + style": FEAT}.items():
    for mname in ["Random forest", "Gradient boosting"]:
        mdl = zoo(tuned=tuned)[mname]
        s = cross_validate(mdl, evl[cols], evl.y, groups=evl.player, cv=gk, scoring="roc_auc")["test_score"]
        abl.append(dict(features=label, model=mname, auc=s.mean(), sd=s.std()))
abl = pd.DataFrame(abl); abl.to_csv(f"{RES}/E3_ablation.csv", index=False)
print("\n", abl.round(3).to_string(index=False))

# =============================================================== importance + interpretable tree
rf = zoo(tuned=tuned)["Random forest"]
gtr, gte = next(iter(GroupKFold(4).split(evl[FEAT], evl.y, evl.player)))
rf.fit(evl.iloc[gtr][FEAT], evl.iloc[gtr].y)
pi = permutation_importance(rf, evl.iloc[gte][FEAT], evl.iloc[gte].y, scoring="roc_auc", n_repeats=8, random_state=0, n_jobs=-1)
imp = pd.DataFrame(dict(feature=FEAT, imp=pi.importances_mean, sd=pi.importances_std)).sort_values("imp", ascending=True).tail(14)
imp.to_csv(f"{RES}/E2_permutation_importance.csv", index=False)

fig, ax = plt.subplots(1, 3, figsize=(19, 5), gridspec_kw=dict(width_ratios=[1, 1, 1], wspace=.75))
# E1/E2 comparison
for a, r, ttl in ((ax[0], r1, "E1 Player: winner vs loser"), (ax[1], r2, "E2 Hand: does it win money?")):
    rr = r[r.model != "Majority (baseline)"].sort_values("auc")
    a.barh(rr.model, rr.auc, xerr=rr.auc_sd, color=[C["green"] if v == rr.auc.max() else C["blue"] for v in rr.auc], capsize=3)
    a.axvline(.5, color=C["red"], ls="--", lw=1); a.set_xlim(.45, max(.62, rr.auc.max() + .04))
    a.set_xlabel("ROC AUC (0.5 = coin flip)"); a.set_title(ttl)
    for i, v in enumerate(rr.auc):
        a.text(a.get_xlim()[1], i, f"{v:.3f}", va="center", ha="right", fontsize=9, fontweight="bold")
ax[2].barh(imp.feature, imp.imp, xerr=imp.sd, color=[C["orange"] if f.startswith("s_") else C["blue"] for f in imp.feature], capsize=2)
ax[2].set_xlabel("drop in AUC when shuffled"); ax[2].set_title("E2 drivers (blue seat/line, orange style)", fontsize=11)
savefig("f8_models.png")

# interpretable tree for the playbook (depth 3, entropy)
tree = DecisionTreeClassifier(criterion="entropy", max_depth=3, min_samples_leaf=800, random_state=0).fit(evl[SIT].fillna(0), evl.y)
txt = export_text(tree, feature_names=SIT, show_weights=True)
open(f"{RES}/E2_tree_rules.txt", "w").write(txt)
fig, ax = plt.subplots(figsize=(15, 6))
plot_tree(tree, feature_names=SIT, class_names=["lose", "win"], filled=True, rounded=True, fontsize=8, ax=ax, impurity=False, proportion=True)
savefig("f9_tree.png")
print(txt)
