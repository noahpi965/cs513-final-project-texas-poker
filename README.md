# What wins at Texas Hold'em? — CS 513 final project

Data mining 1.2M real online no-limit hold'em hands (PokerStars NL50, July 2009; PHH HandHQ archive,
[uoftcprg/phh-dataset](https://github.com/uoftcprg/phh-dataset)) to find which style and decisions earn money.

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
