"""06_build_deck.py -- assemble the final presentation (python-pptx). Code goes in the appendix."""
import os, glob
import pandas as pd
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from common import *

DARK, BLUE, GREEN, RED, GREY, LIGHT = (RGBColor(0x1F, 0x29, 0x33), RGBColor(0x2F, 0x6D, 0xB5), RGBColor(0x3C, 0x9D, 0x6B),
                                       RGBColor(0xC8, 0x42, 0x3B), RGBColor(0x5F, 0x66, 0x70), RGBColor(0xF3, 0xF5, 0xF8))
prs = Presentation(); prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def tb(slide, x, y, w, h, text="", size=18, bold=False, color=DARK, align=None, font="Calibri"):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = box.text_frame; tf.word_wrap = True
    lines = text if isinstance(text, list) else [text]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run(); r.text = ln; r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = color; r.font.name = font
        if align: p.alignment = align
        p.space_after = Pt(6)
    return box


def bullets(slide, x, y, w, h, items, size=18):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = box.text_frame; tf.word_wrap = True
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        head, _, tail = it.partition("|")
        r = p.add_run(); r.text = "▪ " + head; r.font.size = Pt(size); r.font.bold = bool(tail); r.font.color.rgb = DARK; r.font.name = "Calibri"
        if tail:
            r2 = p.add_run(); r2.text = tail; r2.font.size = Pt(size); r2.font.color.rgb = GREY; r2.font.name = "Calibri"
        p.space_after = Pt(9)


def slide(title, notes=""):
    s = prs.slides.add_slide(BLANK)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(.18), prs.slide_height); bar.fill.solid(); bar.fill.fore_color.rgb = BLUE; bar.line.fill.background()
    tb(s, .55, .3, 12.3, .9, title, 30, True)
    if notes: s.notes_slide.notes_text_frame.text = notes
    return s


def image(s, name, x, y, w, h):
    path = os.path.join(FIG, name); iw, ih = Image.open(path).size
    sc = min(w / iw, h / ih); pw, ph = iw * sc, ih * sc
    s.shapes.add_picture(path, Inches(x + (w - pw) / 2), Inches(y + (h - ph) / 2), Inches(pw), Inches(ph))


def callout(s, x, y, w, h, big, small, color=BLUE):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)); sh.fill.solid(); sh.fill.fore_color.rgb = LIGHT; sh.line.color.rgb = color
    tb(s, x + .1, y + .08, w - .2, h * .55, big, 28, True, color, PP_ALIGN.CENTER)
    tb(s, x + .1, y + h * .55, w - .2, h * .45, small, 12.5, False, GREY, PP_ALIGN.CENTER)


# ------------------------------------------------------------------ numbers
noise = pd.read_csv(f"{RES}/noise_decomposition.csv", index_col=0).iloc[:, 0]
E1 = pd.read_csv(f"{RES}/E1_player_models.csv"); E2 = pd.read_csv(f"{RES}/E2_hand_models.csv"); E3 = pd.read_csv(f"{RES}/E3_ablation.csv")
wp = pd.read_csv(f"{RES}/within_player_raise_vs_limp.csv", index_col=0).iloc[:, 0]
clu = pd.read_csv(f"{RES}/cluster_profit.csv")

# 1 title
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height); bg.fill.solid(); bg.fill.fore_color.rgb = DARK; bg.line.fill.background()
tb(s, .8, 1.4, 11, 1.4, "What Wins at Texas Hold'em?", 48, True, RGBColor(255, 255, 255))
tb(s, .8, 2.7, 11, 1.2, "Data mining 1.2 million real online no-limit hold'em hands to find the style and plays that make money", 22, False, RGBColor(0xC9, 0xD3, 0xE0))
ph = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(.8), Inches(4.5), Inches(2.3), Inches(2.3)); ph.fill.background(); ph.line.color.rgb = RGBColor(255, 255, 255); ph.line.dash_style = 4
tb(s, .8, 5.3, 2.3, .8, "[ insert photo ]", 14, False, RGBColor(0xC9, 0xD3, 0xE0), PP_ALIGN.CENTER)
tb(s, 3.4, 4.7, 8, 1.5, ["[Your name]   ·   CS 513 Final Project", "Data: PHH HandHQ archive (PokerStars NL50, July 2009)", "Methods: clustering · WLS · kNN · Naive Bayes · CART/C5.0 · Random Forest · ANN · Gradient Boosting"], 16, False, RGBColor(0xC9, 0xD3, 0xE0))

# 2 question
s = slide("The question: which plays actually earn money?", "Open with the poker intuition, then say we want evidence from real hands, not solver theory.")
bullets(s, .6, 1.4, 7.4, 5, [
    "Research question|  Which playing style, and which concrete decisions, maximise win rate in no-limit hold'em?",
    "Why it is hard|  Poker is dominated by luck: a winning player still loses 40% of the time over thousands of hands.",
    "What is new here|  Real hand histories (not the UCI Poker-Hand toy set), player identity tracked across 20 days, results rebuilt chip-by-chip.",
    "Our angle|  Test style on FUTURE results (days 1-10 -> days 11-20), then drill down to individual decisions where we have millions of observations.",
], 19)
callout(s, 8.6, 1.5, 4.1, 1.5, "1,230,387", "hands replayed (PokerStars NL50)"); callout(s, 8.6, 3.2, 4.1, 1.5, "39,166", "distinct anonymised players", GREEN); callout(s, 8.6, 4.9, 4.1, 1.5, "5.2 M", "player-hand records with 30+ features", RED)

# 3 data
s = slide("Data engineering: rebuilding every pot from the action log", "Stress that hole cards are hidden - everything is behavioural. Mention the evaluator for showdowns and the sanity check.")
bullets(s, .6, 1.4, 6.6, 5.4, [
    "Source|  uoftcprg/phh-dataset - HandHQ logs, anonymised but consistent player IDs.",
    "Replay engine|  parse each hand (TOML), track street bets, all-ins, uncalled-bet refunds, side pots.",
    "Hidden cards|  Hole cards shown only at showdown. Where payouts were stripped (18% of hands) we settle with our own 7-card evaluator.",
    "Per-hand features|  VPIP, PFR, 3-bet, steal, c-bet, fold-to-c-bet, aggression, WTSD, bet sizes, seat, stack.",
    "Scope|  3-9 player tables only; results in big blinds, before rake.",
], 17)
image(s, "f1_position_ev.png", 7.4, 1.5, 5.6, 4.3)
tb(s, 7.4, 5.9, 5.6, 1, "Validation: the rebuilt results reproduce poker theory - button wins, blinds lose, and net results sum to zero.", 14, False, GREY)

# 4 noise
s = slide("Luck swamps skill - so the design has to be careful", "This is the key methodological slide. Individual results do not persist.")
image(s, "f2_noise.png", .5, 1.3, 8.3, 4.2)
bullets(s, 9.0, 1.5, 4.1, 5, [
    f"r = {noise['corr_A_B']:+.2f}|  between a player's result in days 1-10 and 11-20",
    f"Luck SD ≈ {noise['luck_sd']:.0f} bb/100|  vs. skill SD ≈ {noise['skill_sd']:.0f}",
    "Consequence|  predicting individual winners will be near-impossible; use pooled tests and hand-level data.",
], 16)
tb(s, .6, 5.7, 8, 1, "Design: style features from days 1-10  →  outcome (bb/100) from days 11-20.  1,498 players with ≥100 hands in each period.", 15, False, GREY)

# 5 clustering
s = slide("Unsupervised: four player archetypes, but profit gaps are not conclusive", "k-means with silhouette-chosen k, Ward as cross-check; be honest: p=0.12.")
image(s, "f4_clusters.png", .4, 1.2, 8.6, 3.9)
bullets(s, 9.1, 1.4, 4.0, 5.2, [
    "Method|  k-means (k=4, silhouette 0.23, seed ARI 0.99) vs Ward (ARI 0.57), log-scaled VPIP/PFR/3-bet/c-bet/AF/WTSD.",
    "Aggressive regulars|  (VPIP 23, PFR 15, 3-bet 5%) earn most: +9.6 bb/100.",
    "Permutation test|  p = 0.12: direction is clear, significance is not.",
], 15)
image(s, "f4b_archetype_heatmap.png", .6, 5.1, 8.2, 2.2)

# 6 effects
s = slide("Continuous view: preflop aggression is what correlates with profit", "WLS weights by hands because variance ∝ 1/hands. Only PFR/3-bet/steal are individually significant; none survives BH at 5% - say so.")
image(s, "f5_style_effects.png", .5, 1.3, 7.6, 5.6)
bullets(s, 8.3, 1.5, 4.7, 5, [
    "PFR +1 SD|  ≈ +2.7 bb/100 (p = 0.005)",
    "3-bet +1 SD|  ≈ +2.1 bb/100 (p = 0.014)",
    "Limping|  ≈ -2.2 bb/100 (p = 0.07)",
    "Caveat|  after Benjamini-Hochberg correction all q ≥ 0.06, and the full model explains only R² ≈ 1%.",
    "Message|  consistent direction, small size.",
], 16)

# 7 lines
s = slide("Where the evidence is strong: the decision, not the player", "This is the headline. 4.2M decisions give narrow CIs. Mention selection caveat (strong hands raise).")
image(s, "f6_preflop_lines.png", .4, 1.3, 8.3, 4.5)
callout(s, 9.0, 1.4, 4.0, 1.5, f"+{wp['mean_diff']:.2f} bb", f"per hand: raise instead of limp, same player & seat ({wp['share_positive']:.0%} of {int(wp['n_players'])} players, p < 1e-15)", GREEN)
bullets(s, 9.0, 3.2, 4.0, 3.5, [
    "Open-raise|  +0.8 bb (early seat) to +1.2 bb (button)",
    "Limp|  -0.2 to -0.3 bb in early seats",
    "Call a raise|  loses in the blinds (≈ -0.55 bb)",
    "3-bet|  +3.3 to +4.5 bb (strong-hand selection)",
], 15)
tb(s, .6, 5.9, 8.2, 1, "Realised EV per hand played; fold = 0 (blinds: -0.5 / -0.7). Bars = 95% CI.", 13, False, GREY)

# 8 models
s = slide("Model comparison: same toolbox, two very different problems", "E1 is chance-level for all; E2 is ~0.71. Differences among models in E2 are tiny; NB is worst because features are correlated.")
image(s, "f8_models.png", .3, 1.2, 12.7, 3.5)
e1b = E1[E1.model != "Majority (baseline)"].sort_values("auc", ascending=False).iloc[0]; e2b = E2.sort_values("auc", ascending=False).iloc[0]
bullets(s, .6, 4.9, 12.2, 2.4, [
    f"E1 - who wins? (1,498 players, 25 CV rounds)|  best AUC {e1b.auc:.3f} ({e1b.model}), all within noise of 0.5 → style alone cannot pick winners.",
    f"E2 - does this played hand win money? (60k hands, CV grouped by player)|  best AUC {e2b.auc:.3f} ({e2b.model}); kNN, ANN, RF, C5.0 and logistic regression within 0.01.",
    "Tuning|  hyper-parameters chosen on a disjoint set of players; Naive Bayes is weakest (correlated features).",
], 15)

# 9 ablation + tree
s = slide("Seat + line carry the signal; player identity adds almost nothing", "Ablation, then the interpretable C5.0-style tree as a playbook.")
a = E3.pivot(index="features", columns="model", values="auc").loc[["Player style only", "Seat + line only", "Seat + line + style"]]
rows, cols = len(a) + 1, 3
tbl = s.shapes.add_table(rows, cols, Inches(.6), Inches(1.5), Inches(5.6), Inches(1.9)).table
for j, h in enumerate(["Features", "Random forest", "Grad. boosting"]): tbl.cell(0, j).text = h
for i, (idx, r) in enumerate(a.iterrows(), start=1):
    tbl.cell(i, 0).text = idx; tbl.cell(i, 1).text = f"{r['Random forest']:.3f}"; tbl.cell(i, 2).text = f"{r['Gradient boosting']:.3f}"
for r_ in tbl.rows:
    for c_ in r_.cells:
        for p in c_.text_frame.paragraphs:
            for run in p.runs: run.font.size = Pt(14)
bullets(s, .6, 3.7, 5.6, 3.3, [
    "Style only|  0.58 AUC",
    "Seat + line|  0.71 AUC",
    "Adding style|  +0.001 to +0.007",
    "Takeaway|  what you DO in the hand beats WHO you are.",
], 16)
image(s, "f9_tree.png", 6.4, 1.3, 6.7, 5.4)

# 10 recommendations
s = slide("So what wins? A data-backed playbook", "Close with actionable rules and tie each to a slide.")
bullets(s, .6, 1.4, 12.2, 5.3, [
    "1  Raise or fold preflop.|  Open-raising beats limping by ≈ +1 bb/hand for the same player and seat; limping is negative everywhere except the button.",
    "2  Position is worth ~1 bb per hand.|  Button +0.24 vs big blind -0.38 bb/hand - play more hands late, fewer early.",
    "3  Do not cold-call raises from the blinds.|  ≈ -0.55 bb per call; 3-bet or fold.",
    "4  Be the aggressor.|  Preflop raisers who continuation-bet earn far more than those who check (+2.8 vs +0.3 bb, partly selection).",
    "5  Profile to copy|  VPIP ≈ 22, PFR ≈ 15, 3-bet ≈ 5%, AF ≈ 3  (the 'aggressive regular' archetype, +9.6 bb/100).",
], 20)

# 11 limitations
s = slide("Limitations and honest caveats", "Credibility slide - pre-empt the obvious questions.")
bullets(s, .6, 1.4, 12.2, 5.3, [
    "Hole cards are hidden|  we measure behaviour, not hand strength: strong hands raise, so line EVs mix 'good play' with 'good cards'. The within-player comparison reduces, not removes, this.",
    "Observational data|  associations, not causal effects; profit also depends on opponents at the table.",
    "Survivorship|  players with ≥100 hands in both periods are mostly regulars (mean +6.5 bb/100 vs the weaker players who vanish).",
    "Pre-rake results|  real rake would shift everyone down; 2009 NL50 only.",
    "Clustering is fragile|  significance flips with feature choice; we report the pre-specified design and p = 0.12.",
], 18)

# 12 summary
s = slide("Take-aways", "")
callout(s, .8, 1.6, 3.8, 2.2, "Luck ≫ skill", "style cannot predict who wins (AUC ≈ 0.52); individual results do not persist (r ≈ 0)", RED)
callout(s, 4.8, 1.6, 3.8, 2.2, "Aggression pays", "PFR, 3-bet, steal positive; limp negative; raise beats limp by +1.06 bb (p<1e-15)", GREEN)
callout(s, 8.8, 1.6, 3.8, 2.2, "Decisions > identity", "seat+line AUC 0.71 vs style-only 0.58; five models agree", BLUE)
bullets(s, .8, 4.3, 12, 2.5, [
    "Techniques|  k-means/Ward, WLS with robust SE + BH, kNN, Naive Bayes, CART, C5.0-style, RF, ANN, plus logistic regression and gradient boosting (beyond class), permutation tests, bootstrap CIs, grouped CV.",
    "Next|  add rake and later seasons; use showdown cards to model hand strength; cluster at the hand-line level.",
], 16)

# ------------------------------------------------------------------ appendix: code
s = slide("Appendix: source code"); tb(s, .6, 1.5, 12, 3, ["01_parse.py - replay engine, hand evaluator, per-hand features", "02_features.py - player style table + train/test period split",
   "03_eda_cluster.py - EDA, k-means / Ward, permutation test", "04_style_effects.py - WLS, preflop line EV, within-player test",
   "05_models.py - kNN / NB / CART / C5.0 / RF / ANN / GBM comparison", "06_build_deck.py - this presentation"], 20)
LINES = 46
for f in ["01_parse.py", "02_features.py", "03_eda_cluster.py", "04_style_effects.py", "05_models.py"]:
    code = open(os.path.join(os.path.dirname(__file__), f)).read().expandtabs(4).splitlines()
    pages = [code[i:i + LINES] for i in range(0, len(code), LINES)]
    for k, pg in enumerate(pages, 1):
        s = prs.slides.add_slide(BLANK)
        tb(s, .3, .08, 12, .4, f"{f}  ({k}/{len(pages)})", 12, True, BLUE)
        box = s.shapes.add_textbox(Inches(.3), Inches(.45), Inches(12.7), Inches(6.9)); tf = box.text_frame; tf.word_wrap = False
        for i, ln in enumerate(pg):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            r = p.add_run(); r.text = ln[:150] if ln else " "; r.font.size = Pt(8.5); r.font.name = "Courier New"; r.font.color.rgb = DARK
            p.space_after = Pt(0)

out = os.path.join(ROOT, "Texas_Holdem_Final_Presentation.pptx")
prs.save(out); print("saved", out, "slides:", len(prs.slides))
