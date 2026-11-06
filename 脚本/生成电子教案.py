
import io
import json
import os
import re
import sys

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)

from 地基 import 大模型, 配置

输出目录 = os.path.join(os.path.expanduser("~"), "Desktop", "电子教案-肖泽云语文")
识图稿 = os.path.join(根, "材料", "_批量识图", "肖泽云-语文-全97张.md")
切课稿 = os.path.join(根, "材料", "_批量识图", "肖泽云-语文-全97张-切课.json")

提示模板 = """下面是一位高中语文老师手写教案的逐页转录（可能有识别错字、表格残迹、页眉页脚重复）。

请把它整理成一份可用的电子教案，严格按这五段输出，段名不改、顺序不动：

## 一、三维目标
（知识目标 / 能力目标 / 情感目标 三条；原文有就照原文，没写就按本课内容补，补的条目末尾标「（据课文补充）」）

## 二、重点难点
（重点、难点各一条到三条）

## 三、教法教具
（原文写的教法、教具、课时数照录）

## 四、教学过程
（按环节分小标题：导入 / 初读 / 精读 / 品鉴 / 小结 / 作业 等，用原文的环节名；每环节写清「教师做什么、学生做什么」；
  原文里有的问题、板书要点、引用的诗句一律保留原话，用引号标出）

## 五、教学反思
（原文的反思照录；多页重复的合并成一条，去掉重复）

要求：
- 只用转录里有的内容，不许编造课文之外的知识点；确实缺的部分写「原文未写」
- 不要把「课题」「课时」写进正文，它们会在文件头单独列
- 输出纯 Markdown，不要开场白、不要总结语

本课课题：{课题}
本课覆盖的页：{源页}

下面是转录原文：
{原文}
"""


def _清理(文):
    行们 = []
    for 行 in 文.split(chr(10)):
        干 = 行.strip()
        if 干 in ("---", "|", "|-", "| :--- | :--- |"):
            continue
        if 干.startswith("| :---") or 干.startswith("|:---"):
            continue
        if 干.startswith("以下是图片") or 干.startswith("**【表头】**"):
            continue
        行们.append(行.rstrip())
    出, 空数 = [], 0
    for 行 in 行们:
        if not 行.strip():
            空数 += 1
            if 空数 > 1:
                continue
        else:
            空数 = 0
        出.append(行)
    return chr(10).join(出).strip()


def _安全名(文):
    名 = re.sub(r'[\\/:*?"<>|]', "－", str(文 or "").strip())
    return (名 or "未命名")[:40]


def 整理一课(一条, 原文全文):
    from 能力.按篇目切课 import 字段词
    过程词 = 字段词["过程"]
    反思词 = 字段词["反思"]
    小标题词 = ("导入", "初读", "精读", "品读", "品鉴", "赏析", "探究", "讨论",
              "小结", "作业", "板书", "齐读", "范读", "提问", "思考", "拓展", "环节")
    段们 = []
    for 页 in 一条["源页"]:
        m = re.search(r"^## " + re.escape(页) + r".*?$", 原文全文, re.M)
        if not m:
            continue
        起 = m.end()
        下 = re.search(r"^## ", 原文全文[起:], re.M)
        止 = 起 + (下.start() if 下 else len(原文全文) - 起)
        页文 = 原文全文[起:止]
        取到 = []
        for 行 in 页文.split(chr(10)):
            干 = 行.strip()
            if not 干:
                if 取到 and 取到[-1] != "":
                    取到.append("")
                continue
            if any(词 in 干 for 词 in 过程词 + 反思词) or any(干.startswith(词) for 词 in 小标题词):
                取到.append(干)
                continue
            if 取到 and not 干.startswith("（") and "以下是" not in 干:
                取到.append(干)
        块 = chr(10).join(取到).strip()
        if len(块) < 40:
            块 = _清理(页文)
        段们.append("【%s】" % 页 + chr(10) + 块)
    原料 = _清理(chr(10).join(段们))
    上限 = 26000
    截断 = len(原料) > 上限
    return 原料[:上限], 截断


def 疑点(课题, 原料):
    词们 = [一 for 一 in re.split(r"[\s·、：:（）()]+", str(课题 or "")) if len(一) >= 2]
    if not 词们:
        return ""
    自己 = max(原料.count(词) for 词 in 词们)
    if 自己 > 0:
        return ""
    名们 = ("声声慢", "念奴娇", "赤壁怀古", "永遇乐", "京口北固亭", "登高",
            "采薇", "插秧歌", "沁园春", "长沙")
    别的 = sorted(((名, 原料.count(名)) for 名 in 名们 if 名 not in 词们), key=lambda 对: -对[1])
    别的 = [(名, 数) for 名, 数 in 别的 if 数 >= 2]
    return ("本课转录里没有出现课题「%s」的任何原字，而 %s 出现多次。"
            "照片顺序可能和课时不对应，请对照原稿确认这一课收哪些页。"
            % (re.sub(r"\s", "", str(课题 or "")),
               "、".join("「%s」%d 次" % (名, 数) for 名, 数 in 别的[:3]) if 别的 else "其他课文词句"))


def 写md(路, 课题, 源页, 正文):
    头 = ["# 教案：" + 课题, "XR: C", "",
          "- 教师：肖泽云（新邵八中·语文）",
          "- 源页：" + "、".join(源页),
          "- 生成方式：逐页视觉识别 → 按篇目切课 → 按五段式整理，未改动原文事实",
          "", "---", ""]
    io.open(路, "w", encoding="utf-8", newline=chr(10)).write(chr(10).join(头) + 正文.strip() + chr(10))


def 写docx(路, 课题, 源页, 正文):
    from docx import Document
    文 = Document()
    文.core_properties.comments = "XR: C"
    文.add_heading("教案：" + 课题, level=0)
    文.add_paragraph("教师：肖泽云（新邵八中·语文）　源页：" + "、".join(源页))
    for 行 in 正文.split(chr(10)):
        干 = 行.strip()
        if not 干:
            continue
        if 干.startswith("## "):
            文.add_heading(干[3:].strip(), level=1)
        elif 干.startswith("### "):
            文.add_heading(干[4:].strip(), level=2)
        elif 干.startswith("- "):
            文.add_paragraph(干[2:], style="List Bullet")
        else:
            文.add_paragraph(干)
    文.save(路)


def 补原文附录(路, 原料):
    文 = io.open(路, encoding="utf-8").read()
    if 文.count("原文未写") < 3 or "附：本课转录原文" in 文:
        return False
    尾巴 = [chr(10) + "---" + chr(10),
            "## 附：本课转录原文（未经整理，供核对）" + chr(10),
            "> 上面有几段写了「原文未写」，说明这份转录里找不到对应内容；"
            "下面把本课所覆盖页的原文原样贴出，请对照手写稿确认该收哪些。" + chr(10),
            原料.strip()[:6000] + chr(10)]
    io.open(路, "a", encoding="utf-8", newline=chr(10)).write(chr(10).join(尾巴))
    return True


def main():
    if not os.path.isfile(切课稿):
        raise SystemExit("先跑「按篇目切课」：" + 切课稿)
    if not os.path.isfile(识图稿):
        raise SystemExit("识图稿不在：" + 识图稿)
    os.makedirs(输出目录, exist_ok=True)
    课们 = json.load(io.open(切课稿, encoding="utf-8"))["课们"]
    原文全文 = io.open(识图稿, encoding="utf-8").read()
    索引行 = ["# 电子教案索引：肖泽云（新邵八中·语文）", "XR: C", "",
              "- 来源：97 张手写教案照片，逐页视觉识别后按篇目切课整理",
              "- 本目录共 %d 课" % len(课们), ""]
    成了 = 0
    for 一条 in 课们:
        课文, 截断 = 整理一课(一条, 原文全文)
        课题 = 一条["课题"]
        提示 = 提示模板.replace("{课题}", 课题).replace("{源页}", "、".join(一条["源页"]))
        提示 = 提示.replace("{原文}", 课文)
        正文 = 大模型.问(提示, 随机度=0.2)
        提醒 = 疑点(课题, 课文)
        if 提醒:
            正文 = "> ⚠ " + 提醒 + chr(10) + chr(10) + 正文
        显示课题 = 课题
        if re.match(r"^（?第[一二三四五六七八九十\d]+课时", 课题 or ""):
            显示课题 = "未标篇目（原稿课题位写的是课时，%s–%s）" % (
                一条["源页"][0].split(".")[0], 一条["源页"][-1].split(".")[0])
        名基 = "%02d-%s" % (一条["序号"], _安全名(显示课题))
        md路 = os.path.join(输出目录, 名基 + ".md")
        docx路 = os.path.join(输出目录, 名基 + ".docx")
        写md(md路, 显示课题, 一条["源页"], 正文)
        if 补原文附录(md路, 课文):
            print("  （这一课模型说「原文未写」太多，已附上原文供核对）")
        try:
            写docx(docx路, 显示课题, 一条["源页"], 正文)
            有docx = "、docx"
        except Exception as 异常:
            有docx = "（docx 没生成：%s）" % type(异常).__name__
        索引行.append("- %s：%s（%d 页%s%s）" % (名基, 显示课题, len(一条["源页"]),
                                          "，原文过长已截断" if 截断 else "",
                                          "，⚠ 待核对归属" if 提醒 else ""))
        索引行.append("  - 文件：%s.md%s" % (名基, 有docx))
        成了 += 1
        print("✓ %s　%d 页　md %d 字" % (名基, len(一条["源页"]), len(正文)))
    索引行 += ["", "生成时间：见文件属性", ""]
    io.open(os.path.join(输出目录, "00-教案索引.md"), "w",
            encoding="utf-8", newline=chr(10)).write(chr(10).join(索引行))
    print("完成 %d 课 → %s" % (成了, 输出目录))


if __name__ == "__main__":
    main()
