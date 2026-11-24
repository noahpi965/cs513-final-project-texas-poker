"""07_build_deck_zh.py -- Chinese version of the presentation (same numbers, same figures)."""
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


def tb(slide, x, y, w, h, text="", size=18, bold=False, color=DARK, align=None, font="PingFang SC"):
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
        r = p.add_run(); r.text = "▪ " + head; r.font.size = Pt(size); r.font.bold = bool(tail); r.font.color.rgb = DARK; r.font.name = "PingFang SC"
        if tail:
            r2 = p.add_run(); r2.text = tail; r2.font.size = Pt(size); r2.font.color.rgb = GREY; r2.font.name = "PingFang SC"
        p.space_after = Pt(9)


def slide(title, notes=""):
    s = prs.slides.add_slide(BLANK)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(.18), prs.slide_height); bar.fill.solid(); bar.fill.fore_color.rgb = BLUE; bar.line.fill.background()
    tb(s, .55, .3, 12.3, .9, title, 28, True)
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

# 1 标题
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height); bg.fill.solid(); bg.fill.fore_color.rgb = DARK; bg.line.fill.background()
tb(s, .8, 1.3, 11.5, 1.4, "德州扑克:什么打法能赢钱?", 46, True, RGBColor(255, 255, 255))
tb(s, .8, 2.6, 11.5, 1.2, "挖掘 616,000 手真实线上无限注德扑牌局(3-9 人桌),找出赚钱的风格和具体打法", 22, False, RGBColor(0xC9, 0xD3, 0xE0))
ph = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(.8), Inches(4.5), Inches(2.3), Inches(2.3)); ph.fill.background(); ph.line.color.rgb = RGBColor(255, 255, 255); ph.line.dash_style = 4
tb(s, .8, 5.3, 2.3, .8, "[ 此处放照片 ]", 14, False, RGBColor(0xC9, 0xD3, 0xE0), PP_ALIGN.CENTER)
tb(s, 3.4, 4.7, 9.5, 1.8, ["[你的姓名]   ·   CS 513 期末项目", "数据:PHH HandHQ 档案(PokerStars NL50,2009 年 7 月)", "方法:聚类 · 加权回归 · kNN · 朴素贝叶斯 · CART/C5.0 · 随机森林 · 神经网络 · 梯度提升"], 16, False, RGBColor(0xC9, 0xD3, 0xE0))

# 2 问题
s = slide("研究问题:哪些打法真的赚钱?", "先讲扑克直觉,再说明我们要用真实牌局的证据,而不是理论。")
bullets(s, .6, 1.4, 7.6, 5, [
    "研究问题|  在无限注德扑里,哪种风格、哪些具体决策能提高胜率?",
    "难点|  扑克的运气成分极大:一个长期赢钱的玩家,几千手之内仍可能输。",
    "新意|  用真实牌谱(不是 UCI 的 Poker-Hand 玩具数据),跨 20 天追踪玩家,逐笔重算筹码结果。",
    "思路|  用前 10 天的风格去检验后 10 天的结果;再下钻到单个决策,那里有几百万条观察。",
], 18)
callout(s, 8.6, 1.5, 4.1, 1.5, "616,317", "分析的环桌牌局数(PokerStars NL50)"); callout(s, 8.6, 3.2, 4.1, 1.5, "32,886", "匿名玩家数", GREEN); callout(s, 8.6, 4.9, 4.1, 1.5, "4.0 M", "玩家-手牌记录,30 多个特征", RED)

# 3 数据
s = slide("数据工程:从行动记录重建每一个底池", "强调底牌是隐藏的,所以全部是行为特征。提到摊牌评估器和合理性检验。")
bullets(s, .6, 1.3, 6.6, 5.4, [
    "来源|  uoftcprg/phh-dataset 的 HandHQ 日志;玩家匿名但 ID 稳定。",
    "重放引擎|  解析每手牌,追踪每条街的下注、全下、未被跟注部分的退回、边池。",
    "底牌隐藏|  只有摊牌才公开底牌。派彩被剥掉的牌局(分析集的 20%,约 12.2 万手)用我们自己写的 7 张牌评估器判定胜负。",
    "每手特征|  VPIP、PFR、3-bet、偷盲、持续下注、面对持续下注弃牌、激进度、摊牌率、下注尺度、座位、筹码深度。",
    "数据漏斗|  1,231 个文件 → 解析 1,230,387 手 → 616,317 手环桌(3-9 人;单挑已排除)→ 32,886 名玩家。",
    "单位|  结果以大盲(bb)计,未扣抽水。",
], 15)
image(s, "f1_position_ev.png", 7.4, 1.5, 5.6, 4.1)
tb(s, 7.4, 5.7, 5.6, 1, "合理性检验:重建结果符合扑克常识——按钮位赚钱、盲注位亏钱,全体净盈亏之和为零。", 14, False, GREY)
tb(s, .6, 6.85, 12.3, .5, "数据来源: github.com/uoftcprg/phh-dataset  >  data/handhq/PS-2009-07-01_2009-07-23_50NLH_OBFU   |   完整档案: doi.org/10.5281/zenodo.10796885", 11, False, GREY)

# 4 噪声
s = slide("运气远大于技术,所以实验设计必须谨慎", "关键的方法论页:个人结果不具延续性。")
image(s, "f2_noise.png", .5, 1.3, 8.3, 4.2)
bullets(s, 9.0, 1.5, 4.1, 5, [
    f"r = {noise['corr_A_B']:+.2f}|  同一玩家前 10 天与后 10 天盈利的相关系数",
    f"运气标准差约 {noise['luck_sd']:.0f} bb/100|  对比技术标准差约 {noise['skill_sd']:.0f}",
    "结论|  预测个人是否会赢几乎不可能;要用汇总检验和手牌级数据。",
], 15)
tb(s, .6, 5.7, 8, 1.2, "设计:前 10 天提取风格特征 → 后 10 天计算结果(bb/100)。共 1,498 名玩家,两段各至少 100 手(853k + 880k 条玩家-手牌记录)。", 14, False, GREY)

# 5 聚类
s = slide("无监督:四类玩家,但盈利差异并不确凿", "k-means 用轮廓系数选 k,Ward 做交叉验证;要诚实:p = 0.12。")
image(s, "f4_clusters.png", .4, 1.2, 8.6, 3.9)
bullets(s, 9.1, 1.4, 4.0, 5.2, [
    "方法|  k-means(k=4,轮廓系数 0.23,不同随机种子 ARI 0.99)对比 Ward(ARI 0.57);对 VPIP/PFR/3-bet/持续下注/AF/摊牌率取对数后聚类。",
    "激进常客|  (VPIP 23、PFR 15、3-bet 5%)赚得最多:+9.6 bb/100。",
    "置换检验|  p = 0.12:方向明确,但统计上不显著。",
], 14)
image(s, "f4b_archetype_heatmap.png", .6, 5.1, 8.2, 2.2)

# 6 效应
s = slide("连续视角:翻前进攻性与盈利同向变化", "按手数加权,因为方差与手数成反比。只有 PFR/3-bet/偷盲单独显著,多重检验校正后都不显著,要如实说。")
image(s, "f5_style_effects.png", .5, 1.3, 7.6, 5.6)
bullets(s, 8.3, 1.5, 4.7, 5, [
    "PFR 高 1 个标准差|  约 +2.7 bb/100(p = 0.005)",
    "3-bet 高 1 个标准差|  约 +2.1 bb/100(p = 0.014)",
    "平跟入池(limp)|  约 -2.2 bb/100(p = 0.07)",
    "注意|  Benjamini-Hochberg 校正后 q 均 ≥ 0.06,完整模型只解释约 1% 的方差(R²)。",
    "含义|  方向一致,幅度很小。",
], 15)

# 7 路线
s = slide("证据最强的地方:决策本身,而不是玩家是谁", "这是主结论。几百万个决策让置信区间很窄。提到选择偏差(好牌才加注)。")
image(s, "f6_preflop_lines.png", .4, 1.3, 8.3, 4.5)
callout(s, 9.0, 1.4, 4.0, 1.6, f"+{wp['mean_diff']:.2f} bb", f"每手:加注优于平跟(同一玩家、同一位置;{int(wp['n_players'])} 名玩家中 {wp['share_positive']:.0%} 如此,p < 1e-15)", GREEN)
bullets(s, 9.0, 3.2, 4.0, 3.5, [
    "主动开池加注|  早位 +0.8 bb 到按钮位 +1.2 bb",
    "平跟入池|  早位 -0.2 到 -0.3 bb",
    "跟注别人的加注|  盲注位亏损(约 -0.55 bb)",
    "3-bet|  +3.3 到 +4.5 bb(含强牌选择效应)",
], 14)
tb(s, .6, 5.9, 8.2, 1, "每手实际收益;弃牌 = 0(盲注位 -0.5 / -0.7)。误差线为 95% 置信区间。", 13, False, GREY)

# 8 模型
s = slide("模型对比:同一套工具,两个截然不同的问题", "E1 所有模型都在随机水平;E2 约 0.71。E2 里模型差距很小;朴素贝叶斯最差,因为特征相关。")
image(s, "f8_models.png", .3, 1.2, 12.7, 3.5)
e1b = E1[E1.model != "Majority (baseline)"].sort_values("auc", ascending=False).iloc[0]; e2b = E2.sort_values("auc", ascending=False).iloc[0]
bullets(s, .6, 4.9, 12.2, 2.4, [
    f"E1 谁会赢?(1,498 名玩家,25 轮交叉验证)|  最佳 AUC {e1b.auc:.3f}({e1b.model}),都在 0.5 的噪声范围内 → 仅凭风格选不出赢家。",
    f"E2 这手牌会赢钱吗?(6 万手,按玩家分组交叉验证)|  最佳 AUC {e2b.auc:.3f}({e2b.model});kNN、神经网络、随机森林、C5.0、逻辑回归相差不到 0.01。",
    "调参|  超参数在另一批互不重叠的玩家上选定;朴素贝叶斯最弱(特征相关)。",
], 14)

# 9 消融
s = slide("座位 + 路线承载了信号;玩家身份几乎没有增量", "消融实验,然后用可解释的 C5.0 式决策树作为打法手册。")
a = E3.pivot(index="features", columns="model", values="auc").loc[["Player style only", "Seat + line only", "Seat + line + style"]]
zh = {"Player style only": "仅玩家风格", "Seat + line only": "仅座位 + 路线", "Seat + line + style": "座位 + 路线 + 风格"}
tbl = s.shapes.add_table(len(a) + 1, 3, Inches(.6), Inches(1.5), Inches(5.6), Inches(1.9)).table
for j, h in enumerate(["特征", "随机森林", "梯度提升"]): tbl.cell(0, j).text = h
for i, (idx, r) in enumerate(a.iterrows(), start=1):
    tbl.cell(i, 0).text = zh[idx]; tbl.cell(i, 1).text = f"{r['Random forest']:.3f}"; tbl.cell(i, 2).text = f"{r['Gradient boosting']:.3f}"
for r_ in tbl.rows:
    for c_ in r_.cells:
        for p in c_.text_frame.paragraphs:
            for run in p.runs: run.font.size = Pt(14); run.font.name = "PingFang SC"
bullets(s, .6, 3.7, 5.6, 3.3, [
    "仅风格|  AUC 0.58",
    "座位 + 路线|  AUC 0.71",
    "再加风格|  仅提高 0.001 到 0.007",
    "要点|  你在这手牌里怎么打,比你是谁更重要。",
], 16)
image(s, "f9_tree.png", 6.4, 1.3, 6.7, 5.4)

# 10 建议
s = slide("那么什么能赢?一份有数据支撑的打法手册", "用可执行的规则收尾,并对应到前面的页面。")
bullets(s, .6, 1.4, 12.2, 5.3, [
    "1  翻前要么加注,要么弃牌。|  同一玩家同一位置,加注比平跟每手多赚约 1 bb;除按钮位外,平跟处处为负。",
    "2  位置价值约每手 1 bb。|  按钮位 +0.24,大盲位 -0.38 bb/手:后位多玩,前位少玩。",
    "3  盲注位不要冷跟注加注。|  每次约 -0.55 bb;要么 3-bet,要么弃牌。",
    "4  做进攻方。|  翻前加注者在翻牌圈持续下注,收益远高于过牌(+2.8 对 +0.3 bb,部分是选择效应)。",
    "5  参考画像|  VPIP ≈ 22、PFR ≈ 15、3-bet ≈ 5%、AF ≈ 3(“激进常客”类型,+9.6 bb/100)。",
], 19)

# 11 局限
s = slide("局限与诚实的说明", "可信度页:提前回答显而易见的质疑。")
bullets(s, .6, 1.4, 12.2, 5.3, [
    "底牌隐藏|  我们衡量的是行为,而不是牌力:强牌才加注,所以路线收益里混着“打得好”和“牌好”。同一玩家内部对比能减弱、但不能消除这一点。",
    "观察性数据|  只能说明关联,不是因果;盈利还取决于同桌对手。",
    "幸存者偏差|  两段各至少 100 手的玩家多为常客(平均 +8.0 bb/100),提前离场的弱玩家被排除。",
    "抽水前结果|  真实抽水会让所有人下移;只覆盖 2009 年 NL50。",
    "聚类不稳|  显著性会随特征选择变化;我们报告预先设定的方案,p = 0.12。",
], 17)

# 12 总结
s = slide("总结", "")
callout(s, .8, 1.6, 3.8, 2.2, "运气 ≫ 技术", "风格无法预测谁会赢(AUC ≈ 0.52);个人结果不延续(r ≈ 0)", RED)
callout(s, 4.8, 1.6, 3.8, 2.2, "进攻有回报", "PFR、3-bet、偷盲为正,平跟为负;加注比平跟多赚 1.06 bb(p<1e-15)", GREEN)
callout(s, 8.8, 1.6, 3.8, 2.2, "决策 > 身份", "座位+路线 AUC 0.71,仅风格 0.58;五种模型结论一致", BLUE)
bullets(s, .8, 4.3, 12, 2.5, [
    "方法|  k-means/Ward、带稳健标准误和 BH 校正的加权回归、kNN、朴素贝叶斯、CART、C5.0 式、随机森林、神经网络,另有逻辑回归和梯度提升(课外)、置换检验、自助法置信区间、按玩家分组的交叉验证。",
    "下一步|  加入抽水和其他赛季;用摊牌底牌建模牌力;在“路线”层面做聚类。",
], 15)

# ------------------------------------------------------------------ 附录
s = slide("附录:数据来源与参考")
bullets(s, .6, 1.4, 12.2, 5, [
    "数据集|  PHH 数据集(扑克牌谱),多伦多大学 CPSRG。https://github.com/uoftcprg/phh-dataset",
    "所用子集|  HandHQ 日志,PokerStars NL50($0.25/$0.50),2009 年 7 月 1-23 日:data/handhq/PS-2009-07-01_2009-07-23_50NLH_OBFU(文件 1-1299,下载 1,231 个)。",
    "完整档案|  https://doi.org/10.5281/zenodo.10796885(含 GitHub 上被剔除的内容)。",
    "格式规范|  https://phh.readthedocs.io/en/stable/",
    "代码与结果|  https://github.com/noahpi965/cs513-final-project-texas-poker",
    "处理说明|  仅 3-9 人桌;底池由行动重建;无派彩的摊牌用 7 张牌评估器判定;结果以大盲计、未扣抽水。",
], 15)

s = slide("附录:源代码"); tb(s, .6, 1.5, 12, 3, ["01_parse.py - 重放引擎、牌力评估器、每手特征", "02_features.py - 玩家风格表 + 前后两段切分",
   "03_eda_cluster.py - 探索分析、k-means / Ward、置换检验", "04_style_effects.py - 加权回归、翻前路线收益、同一玩家内部检验",
   "05_models.py - kNN / 朴素贝叶斯 / CART / C5.0 / 随机森林 / 神经网络 / 梯度提升 对比", "06_build_deck.py / 07_build_deck_zh.py - 英文版 / 中文版演示文稿"], 18)
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

out = os.path.join(ROOT, "Texas_Holdem_Final_Presentation_ZH.pptx")
prs.save(out); print("saved", out, "slides:", len(prs.slides))
