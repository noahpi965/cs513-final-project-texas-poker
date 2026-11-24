"""Shared paths, plotting style and helpers."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
FIG = os.path.join(ROOT, "figures")
RES = os.path.join(ROOT, "results")
for d in (FIG, RES):
    os.makedirs(d, exist_ok=True)

# one consistent, colour-blind-safe palette
C = dict(blue="#2F6DB5", orange="#E8833A", green="#3C9D6B", red="#C8423B",
         purple="#7E5BA6", grey="#8A8F98", dark="#1F2933", teal="#2A9D9D")
PAL = [C["blue"], C["orange"], C["green"], C["red"], C["purple"], C["teal"]]

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 200, "savefig.bbox": "tight",
    "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "axes.axisbelow": True,
    "axes.prop_cycle": matplotlib.cycler(color=PAL),
})

STYLE_FEATURES = ["VPIP", "PFR", "ThreeBet", "Steal", "CBet", "FoldToCBet",
                  "AF", "WTSD", "Limp", "FoldTo3Bet"]


CLUSTER_FEATURES = ["VPIP", "PFR", "ThreeBet", "CBet", "AF", "WTSD"]


def load_hands(min_players=3):
    df = pd.read_pickle(os.path.join(DATA, "player_hands.pkl"))
    return df[df.n_players >= min_players].copy()


def load_split():
    return pd.read_csv(os.path.join(DATA, "players_split.csv"), index_col=0)


def savefig(name):
    path = os.path.join(FIG, name)
    plt.savefig(path)
    plt.close()
    print("saved", path)
