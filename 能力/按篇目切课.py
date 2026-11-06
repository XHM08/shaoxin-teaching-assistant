
import io
import json
import os
import re

from 地基 import 注册表
from 能力.写文件 import _定路 as 定文件路

字段词 = {
    "课时": ("课时", "课型"),
    "目标": ("教学目标", "学习目标", "知识目标", "能力目标", "情感目标", "三维目标"),
    "重难点": ("教学重难点", "重难点", "教学重点", "重点难点", "重点", "难点"),
    "教法教具": ("教学方法", "教法学法", "教法", "教具", "教学准备", "教学手段"),
    "过程": ("教学过程", "教学过程设计", "教学环节", "课堂设计", "过程设计"),
    "反思": ("教学反思", "课后反思", "反思"),
}
页头 = re.compile(r"^##\s*(P\d+\.(?:jpg|jpeg|png))\s*$", re.M)
课题行 = re.compile(r"课\s*题\s*[:：]\s*(.+)")
分隔行 = re.compile(r"^\s*(?:-{3,}|={3,})\s*$", re.M)


def _页们(原文):
    段们 = []
    位们 = [(m.start(), m.group(1)) for m in 页头.finditer(原文)]
    if not 位们:
        return [("（整份）", 原文)], 0
    for i, (起, 名) in enumerate(位们):
        止 = 位们[i + 1][0] if i + 1 < len(位们) else len(原文)
        段们.append((名, 原文[起:止]))
    return 段们, len(位们)


def _取字段(正文):
    行们 = 正文.split(chr(10))
    全部词 = [w for 词们 in 字段词.values() for w in 词们]
    出 = {名: [] for 名 in 字段词}
    当前 = None
    for 行 in 行们:
        if 当前 == "反思" and (课题行.search(行) or re.match(r"^\s*第[一二三四五六七八九十\d]+课时", 行)):
            当前 = None
            continue
        命中 = next((名 for 名, 词们 in 字段词.items() if any(w in 行 for w in 词们)), None)
        if 命中:
            当前 = 命中
            出[当前].append(行.strip())
            continue
        if any(w in 行 for w in 全部词):
            当前 = None
            continue
        if 当前:
            出[当前].append(行.rstrip())
    return {名: chr(10).join(行们).strip() for 名, 行们 in 出.items()}


def 处理(识图稿="", 分段规则="按课题", 输出名=""):
    路源, _根 = 定文件路(识图稿)
    if not os.path.isfile(路源):
        raise ValueError("识图稿不在：%s" % 识图稿)
    原文 = io.open(路源, encoding="utf-8-sig").read()
    if not 原文.strip():
        raise ValueError("识图稿是空的：%s" % 识图稿)

    规则 = str(分段规则 or "按课题").strip()
    if 规则 not in ("按课题", "按页", "按分隔线"):
        raise ValueError("分段规则只认 按课题 / 按页 / 按分隔线，现在给的是：%s" % 规则)

    页们, 页数 = _页们(原文)

    课们 = []
    if 规则 == "按页":
        课们 = [{"课题": "", "页们": [一]} for 一 in 页们]
    elif 规则 == "按分隔线":
        块们 = [块.strip() for 块 in 分隔行.split(原文) if 块.strip()]
        课们 = [{"课题": "", "页们": [(("块%d" % (i + 1)), 块)]} for i, 块 in enumerate(块们)]
    else:
        for 名, 正文 in 页们:
            m = 课题行.search(正文)
            if m and (not 课们 or 课们[-1]["课题"]):
                课们.append({"课题": m.group(1).strip(), "页们": [(名, 正文)]})
            elif m and 课们 and not 课们[-1]["课题"]:
                课们[-1]["课题"] = m.group(1).strip()
                课们[-1]["页们"].append((名, 正文))
            elif 课们:
                课们[-1]["页们"].append((名, 正文))
            else:
                课们.append({"课题": "", "页们": [(名, 正文)]})

    成品, 缺项 = [], {}
    for 序, 课 in enumerate(课们, 1):
        合并 = chr(10).join(正文 for _名, 正文 in 课["页们"])
        字段 = _取字段(合并)
        课题 = 课["课题"] or ""
        if not 课题:
            m = 课题行.search(合并)
            课题 = m.group(1).strip() if m else ""
        if re.match(r"^第[一二三四五六七八九十\d]+课时", 课题 or ""):
            课题 = "（课题位写的是课时）" + 课题
        if not 课题:
            课题 = "未标课题（第 %d 段）" % 序
        一条 = {"序号": 序, "课题": 课题, "源页": [名 for 名, _ in 课["页们"]],
                "课时": 字段["课时"], "目标": 字段["目标"], "重难点": 字段["重难点"],
                "教法教具": 字段["教法教具"], "过程": 字段["过程"], "反思": 字段["反思"]}
        for 名 in ("课时", "目标", "重难点", "教法教具", "过程", "反思"):
            if not 一条[名]:
                缺项[名] = 缺项.get(名, 0) + 1
        成品.append(一条)

    目录 = os.path.dirname(路源)
    名字 = str(输出名 or "").strip() or (os.path.splitext(os.path.basename(路源))[0] + "-切课.json")
    路出 = os.path.join(目录, 名字)
    with io.open(路出, "w", encoding="utf-8", newline=chr(10)) as 文件:
        文件.write(json.dumps({"来源": os.path.basename(路源), "分段规则": 规则,
                              "页数": 页数, "课数": len(成品), "课们": 成品},
                             ensure_ascii=False, indent=1))

    缺说 = ("，缺字段：" + "、".join("%s %d 课" % (名, 数) for 名, 数 in 缺项.items())) if 缺项 else "，六段字段都抽到了"
    预览 = "；".join("%d. %s（%s）" % (一["序号"], 一["课题"][:18], "、".join(一["源页"]))
                     for 一 in 成品[:4])
    return {"正文": "切出 %d 课（%d 页，%s）%s。JSON：%s。前几课：%s"
                    % (len(成品), 页数, 规则, 缺说, 路出, 预览),
            "课数": len(成品), "页数": 页数, "文件": 路出, "缺项": 缺项}


注册表.登记(
    代号="按篇目切课",
    标题="按篇目切课",
    说明="把批量识图稿按课题切成一课一块，抽出课时/目标/重难点/教法教具/过程/反思，输出 JSON。",
    参数=[
        {"代号": "识图稿", "标签": "识图稿 md 路径", "类型": "text", "必填": True,
         "示例": "材料/_批量识图/肖泽云-语文-全97张.md"},
        {"代号": "分段规则", "标签": "按课题 / 按页 / 按分隔线", "类型": "text", "必填": False,
         "示例": "按课题"},
        {"代号": "输出名", "标签": "输出文件名（留空自动）", "类型": "text", "必填": False,
         "示例": ""},
    ],
    处理函数=处理,
)
