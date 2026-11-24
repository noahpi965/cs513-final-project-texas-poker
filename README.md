# What wins at Texas Hold'em? — CS 513 final project

Data mining 616,317 real online ring-game hands (3-9 players; 4.0M player-hand records, 32,886 players) from PokerStars NL50, July 2009,
to find which style and decisions earn money.

**Data:** PHH HandHQ archive, [uoftcprg/phh-dataset](https://github.com/uoftcprg/phh-dataset) (subset `data/handhq/PS-2009-07-01_2009-07-23_50NLH_OBFU`);
full archive: [doi.org/10.5281/zenodo.10796885](https://doi.org/10.5281/zenodo.10796885); format: [phh.readthedocs.io](https://phh.readthedocs.io/en/stable/).
Funnel: 1,231 files → 1,230,387 hands parsed → 616,317 ring hands (heads-up excluded) → 1,498 players with ≥100 hands in both periods for the player-level tests.

## Key findings
- Luck dominates: a player's result in days 1-10 barely predicts days 11-20 (r ≈ 0.02).
- Raise or fold: open-raising beats limping by about +1.06 bb/hand for the same player and seat (p < 1e-15).
- Seat + line explain hand outcomes (AUC ≈ 0.71); player style adds almost nothing; style alone cannot pick winners (AUC ≈ 0.52).
- Models: k-means / Ward, WLS, kNN, Naive Bayes, CART, C5.0-style, Random Forest, ANN, plus logistic regression and gradient boosting.

## Reproduce
```
pip install pandas numpy scikit-learn scipy statsmodels matplotlib python-pptx pillow
sh src/00_download.sh          # ~820 MB of raw hand histories
cd src
python 01_parse.py && python 02_features.py && python 03_eda_cluster.py
python 04_style_effects.py && python 05_models.py && python 06_build_deck.py
```
Slides: `Texas_Holdem_Final_Presentation.pptx` · figures in `figures/` · result tables in `results/`.

Caveats: hole cards are hidden (behaviour only), observational data, results before rake, 2009 NL50 only.
