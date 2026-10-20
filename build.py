"""把 engine.html ＋ 范文.py 组成 HTML，输出到本目录（合集即 index.html，供 GitHub Pages）：
  · 每篇有 single 的：单独一份（给学生订正功课）
  · 全部 17 篇：一份复习合集
用法：python build.py
组装前会检查：每篇四段的红勾数是否 3／3／2／2、文中「X月X日（星期X）」的星期是否正确。
"""
import datetime, json, pathlib, re, sys
sys.stdout.reconfigure(encoding="utf-8")  # Windows 终端默认 cp1252，印中文会崩
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from 范文 import ESSAYS

HERE = pathlib.Path(__file__).parent
OUT = HERE
engine = (HERE / "engine.html").read_text(encoding="utf-8")

WEEK = "一二三四五六日"
TITLE_SUFFIX = ("董事长", "总编辑", "主席", "主任", "校长", "主编", "会长", "院长", "馆长", "经理")

def flip(date):                       # 2026年6月20日 → 6月20日2026年（乱稿常见错误）
    y, m, d = re.match(r"(\d+)年(\d+)月(\d+)日", date).groups()
    return f"{m}月{d}日{y}年"

def dashes(date):
    y, m, d = re.match(r"(\d+)年(\d+)月(\d+)日", date).groups()
    return f"{d}-{m}-{y}"

def check(e):
    """回传问题清单。"""
    bad = []
    counts = [len(p) for p in e["paras"]]
    if counts != [3, 3, 2, 2]:
        bad.append(f"红勾数 {counts}，应为 [3,3,2,2]")
    year = int(e["date"][:4])
    text = "".join(t for p in e["paras"] for t, *_ in p)
    for y, m, d, w in re.findall(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日（星期([一二三四五六日])", text):
        real = WEEK[datetime.date(int(y or year), int(m), int(d)).weekday()]
        if real != w:
            bad.append(f"{y or year}年{m}月{d}日 写成星期{w}，实为星期{real}")
    return bad

def compile_doc(e):
    g, name = e["genre"], e["sig"][1]
    unit = e["sig"][0]
    personal = not (unit and any(unit.endswith(s) for s in TITLE_SUFFIX))
    els, steps = [{"k": "q", "type": "text", "messy": {"show": False}}], []
    S = lambda fix, h, r, m, focus: steps.append({"fix": fix, "h": h, "r": r, "m": m, "focus": focus})

    # ── 抬头 ──
    if g in ("公函", "启事"):
        snd = e["sender"]
        messy_a1 = e.get("messy_sender") or (None if personal else unit)
        for i, line in enumerate(snd):
            el = {"k": f"a{i+1}", "type": "line", "text": line}
            if i == 0:
                el["blankBefore"] = 1
                if messy_a1: el["messy"] = {"text": messy_a1}
            els.append(el)
        els.append({"k": "div", "type": "divider", "blankBefore": 1, "messy": {"show": False}})
    if g == "公函":
        for i, line in enumerate(e["recipient"]):
            el = {"k": f"r{i+1}", "type": "line", "text": line}
            if i == 0: el["blankBefore"] = 1
            if i == 1: el["messy"] = {"show": False}
            els.append(el)
        last = f"r{len(e['recipient'])}"
        els.append({"k": "date", "type": "line", "text": e["date"], "attach": last,
                    "messy": {"text": dashes(e["date"]), "align": "right", "before": "a1", "blankBefore": 1}})
        els.append({"k": "salute", "type": "line", "text": e["salute"], "blankBefore": 1,
                    "messy": {"text": "尊敬的" + e["salute"].rstrip("：:")}})
        els.append({"k": "title", "type": "line", "text": e["title"], "ul": True, "blankBefore": 1,
                    "messy": {"text": "（" + e["title"] + "）。"}})
    elif g == "启事":
        els.append({"k": "date", "type": "line", "text": e["date"], "align": "right", "blankBefore": 1,
                    "messy": {"text": flip(e["date"]), "align": "left"}})
        els.append({"k": "to", "type": "line", "text": e.get("to_messy", "致：各界人士"), "messyOnly": True,
                    "blankBefore": 1, "messy": {"before": "title"}})
        els.append({"k": "title", "type": "line", "text": e["title"], "ul": True, "blankBefore": 1,
                    "messy": {"text": "（" + re.sub("启事$", "", e["title"]) + "）"}})
    else:  # 通告
        els.append({"k": "date", "type": "line", "text": e["date"], "align": "right", "blankBefore": 1,
                    "messy": {"text": flip(e["date"]), "align": "left"}})
        els.append({"k": "to", "type": "line", "text": "致：" + e["to"], "blankBefore": 1,
                    "messy": {"text": "致:" + e["to"] + "，"}})
        els.append({"k": "title", "type": "line", "text": e["title"], "ul": True, "blankBefore": 1,
                    "messy": {"text": "（" + re.sub("通告$", "", e["title"]) + "）", "before": "to"}})

    # ── 正文四段 ──
    names = ["首段", "第二段", "第三段", "末段"]
    nums = [None, "2.", "3.", None]
    messy = [{"num": "1."}, {"num": ""}, {"num": "（二）"}, {"indent": True}]
    for i, p in enumerate(e["paras"]):
        el = {"k": f"p{i+1}", "type": "para", "name": names[i], "blankBefore": 1, "messy": messy[i],
              "segs": [list(s) for s in p]}
        if nums[i]: el["num"] = nums[i]
        els.append(el)

    # ── 署名（＋附件） ──
    lines = ([unit] if unit else []) + [name + "　启", "（" + name + "）"]
    suffix = next((s for s in TITLE_SUFFIX if unit.endswith(s)), "")
    sig_keys = []
    for i, line in enumerate(lines):
        k = f"sig{i+1}"; sig_keys.append(k)
        el = {"k": k, "type": "line", "text": line}
        if i == 0:
            el["blankBefore"] = 3
            el["messy"] = {"text": name + suffix + "启", "align": "right"}
        else:
            el["messy"] = {"show": False}
        els.append(el)
    for i, line in enumerate(e.get("attach", [])):
        k = f"att{i+1}"; sig_keys.append(k)
        els.append({"k": k, "type": "line", "text": line, "blankBefore": 1 if i == 0 else 0, "messy": {"show": False}})

    # ── 归位步骤 ──
    S(["blank"], "起手式：先留空行",
      {"公函": "动笔前先把空行留好：第一行留空；发信人地址与横线之间、横线与收信人之间、称呼、标题、各段之间各空一行；署名前空三行。",
       "启事": "动笔前先把空行留好：第一行留空；地址与横线之间、横线与日期之间、标题、各段之间各空一行；署名前空三行。",
       "通告": "动笔前先把空行留好：第一行留空；日期、致、标题、各段之间各空一行；署名前空三行。"}[g],
      "红色 ✕ 就是批改时逐行检查的空行。空行一到位，其他部分只要搬进格子里。", "blanks")
    S(["q"], "题号＋抄题（技术分）",
      "「原试题号码」括号里写题号；平时练习把题目抄在最上面，抄完空一行再开始写。考试时只写题号、不抄题。",
      "漏写题号扣技术分。抄题才知道题目给了哪些关键词：哪些照抄不给分，不跟着写又会离题。", ["qno", "q"])
    if g in ("公函", "启事"):
        who = "发信人" if g == "公函" else "启事者"
        if personal:
            S([f"a{i+1}" for i in range(len(e["sender"]))], f"{who}地址 → 左上",
              "以个人名义发信：左上只写地址，与边线平齐，不写团体名称、单位或职衔。", "常见失分：把身份或职衔写进地址。", ["a1"])
        else:
            S([f"a{i+1}" for i in range(len(e["sender"]))], f"{who}地址 → 左上",
              f"{who}地址靠左写在最上面，与边线平齐；第一行只写最高单位（{e['sender'][0]}）。",
              f"常见失分：写成「{messy_a1}」——单位和职衔只写在署名。", ["a1"])
        S(["div"], "分割横线", "地址下面画一条长横线，横线上下各空一行。", "常见失分：漏画横线、横线上下没空行。", ["div"])
    if g == "公函":
        S(["r2"], "收信人", "横线下靠左：第一行姓名，第二行团体名称，接着写地址。", "常见失分：只写姓名、漏写团体名称（会扣分）。", ["r2"])
        S(["date"], "日期 → 收信人地址最后一行的右边", "日期写在收信人地址最后一行的右边，跟边线对齐，按「年 月 日」的顺序写。",
          f"常见失分：日期写在右上角、写成「{dashes(e['date'])}」。", ["date"])
        S(["salute"], "称呼", f"姓＋职称＋冒号，例如「{e['salute']}」，靠左。", "常见失分：加「尊敬的」、漏冒号、称呼叫错人。", ["salute"])
        S(["title"], "标题", "标题靠左，简明扼要，下画横线，不加括号或任何标点。", "常见失分：加括号、加句号、没画线。", ["title"])
        S(["p1", "p4"], "首段与末段", "首段和末段都不编号、不缩进，靠左顶格写。", "常见失分：首段写「1.」、末段缩进。", ["p1", "p4"])
        S(["p2", "p3"], "中间段编号", "第二段起编号「2.」「3.」，编号后空两格再写；转行回到最左边。", "常见失分：不编号、写成「（一）（二）」或「二、」。", ["p2#n", "p3#n"])
    elif g == "启事":
        S(["date"], "日期 → 横线下右边", "启事日期写在横线下方，靠右对齐，按「年 月 日」的顺序写。",
          f"常见失分：写成「{flip(e['date'])}」、写在左边。", ["date"])
        S(["to"], "启事没有「致」", "启事是公开告知大众的，不写对象；「致：……」是通告才有的。", "常见失分：把通告的「致：全体……」搬进启事。", [])
        S(["title"], "标题", "标题靠左，以「启事」结尾，下画横线，不加括号或任何标点，10字以内。", "常见失分：加括号、没画线、漏写「启事」。", ["title"])
        S(["p1", "p4"], "首段与末段", "首段和末段都不编号、不缩进，靠左顶格写。", "常见失分：首段写「1.」、末段缩进。", ["p1", "p4"])
        S(["p2", "p3"], "中间段编号", "第二段起编号「2.」「3.」，编号后空两格再写；转行回到最左边。", "常见失分：不编号、写成「（一）（二）」或「二、」。", ["p2#n", "p3#n"])
    else:
        S(["date"], "日期 → 右上角", "日期写在右上角，靠右对齐，按「年 月 日」的顺序写。", f"常见失分：写成「{flip(e['date'])}」、写在左边。", ["date"])
        S(["to"], "通告对象", f"「致：{e['to']}」靠左顶格；冒号用「：」，后面不加任何标点。", "常见失分：冒号写错、末尾多一个逗号、照抄成「全体XXX」。", ["to"])
        S(["title"], "标题", "标题放在通告对象下面，靠左；以「通告」结尾，下画横线，不加括号或任何标点，10字以内。", "常见失分：标题放在「致」上面、没画线、加括号。", ["title"])
        S(["p1"], "首段", "首段不编号、不缩进，靠左顶格写。", "常见失分：首段写「1.」、开头空两格。", ["p1"])
        S(["p2", "p3"], "中间段编号", "第二段起编号「2.」「3.」，编号后空两格再写；转行回到最左边。", "常见失分：不编号、写成「（一）（二）」或「二、」。", ["p2#n", "p3#n"])
        S(["p4"], "末段", "末段跟首段一样：不编号、不缩进。通告末段写呼吁＋「敬请垂注」或「特此通告」，不需致谢。", "常见失分：末段缩进；漏写末段（会被倒扣）。", ["p4"])
    if not personal:
        sig_rule = "署名靠左，三行紧挨着写：单位＋职衔 ／ 姓名＋启 ／（姓名），三行全靠最左。"
    elif unit:
        sig_rule = f"以个人名义：署名靠左，三行紧挨着写：身份（{unit}）／ 姓名＋启 ／（姓名），全靠最左。不写单位或职衔。"
    else:
        sig_rule = "以个人名义：署名靠左，两行紧挨着写：姓名＋启 ／（姓名），全靠最左。不写单位或职衔。"
    if e.get("attach"): sig_rule += "附件写在署名下面，空一行。"
    S(sig_keys, "署名 → 格式满分", sig_rule, "常见失分：写在右边、漏写单位职衔、三行之间空行。到这一步，格式 2 分全拿。", sig_keys)

    note = f"{e['kind']}。3322：{e['structure']}。共 10√ ＝ 内容 5 分。"
    if g == "通告":
        note += "<br>倒扣检查：首段通告目的句 ✓　末段结束语 ✓　日期时间地点 ✓ → 不倒扣。<br>首段的事件或宗旨没有照抄题目。"
    return {"id": e["id"], "group": g, "label": e["label"], "title": f"{g}格式归位", "sub": f"把一{'封' if g == '公函' else '则' if g == '启事' else '份'}格式全乱的{g}，一步一步搬回作答纸上的正确位置。",
            "question": e["question"], "intro": f"这是一{'封' if g == '公函' else '则' if g == '启事' else '份'}内容写对、格式全错的{g}。按「下一步」，看每个部分怎样回到作答纸上的正确位置。",
            "qno": "1", "numWidth": "3em", "els": els, "from": {k: "sig1" for k in sig_keys[1:]}, "steps": steps, "tallyNote": note}

def write(name, docs, page):
    html = (engine.replace("/*DOCS*/", json.dumps(docs, ensure_ascii=False))
                  .replace("/*PAGE*/", json.dumps(page, ensure_ascii=False))
                  .replace("/*TITLE*/", page["title"]))
    out = OUT / ("index.html" if name == "初三复习合集" else f"应用文-{name}.html")
    out.write_text(html, encoding="utf-8")
    print("写出", out.name, f"（{len(docs)} 篇）")

problems = {e["label"]: check(e) for e in ESSAYS}
problems = {k: v for k, v in problems.items() if v}
if problems:
    for k, v in problems.items(): print("✗", k, "；".join(v))
    sys.exit(1)

docs = [compile_doc(e) for e in ESSAYS]
for e, d in zip(ESSAYS, docs):
    if e.get("single"):
        write(e["single"], [d], {"title": d["title"], "sub": d["sub"]})
write("初三复习合集", docs, {"title": "应用文格式归位·复习合集",
      "sub": f"公函 10 类、通告 3 类、启事 4 类，共 {len(docs)} 篇。选一篇，看格式一步一步归位。"})
