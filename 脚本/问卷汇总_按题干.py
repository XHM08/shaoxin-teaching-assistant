
import csv
import difflib
import io
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)

from 能力 import 读图片

问卷目录 = os.environ.get("QUESTIONNAIRE_DIR", "")
输出目录 = os.environ.get("QUESTIONNAIRE_OUT", "")

字母们 = "ABCDEFGHIJ"
选项标记 = re.compile(r"(?:^|[\s　\n])([" + 字母们 + r"])[\.．、:：]")

封闭空答 = ("", "未填", "空", "没有填", "没填", "无", "没有", "[不清]", "[不清晰]",
            "不清", "不清楚", "身份：未填", "身份:未填", "/", "-", "—", "?", "？")
开放空答 = ("", "未填", "[不清]", "[不清晰]")
多选词 = ("多选", "双选", "可多选")

姓名式 = re.compile(r"姓名[：:]\s*([^；;\n]*)")
空白式 = re.compile(r"[\s　]+")
句末标点 = re.compile(r"[。．\.、;；,，]+$")


def 归一(值):
    t = 空白式.sub("", str(值 or ""))
    t = 句末标点.sub("", t)
    return t.replace("／", "/").replace("－", "-")


def 去掉姓名(值):
    return 姓名式.sub("姓名：〔略〕", str(值 or ""))


def 是封闭(题干):
    return len(set(选项标记.findall(str(题干 or "")))) >= 2


def 是多选(题干):
    return any(词 in str(题干 or "") for 词 in 多选词)


def 收紧选项(值):
    return re.split(r"[；;]", str(值 or ""))[0].strip()


def 选项表(原始题干):
    文 = str(原始题干 or "")
    位置们 = list(选项标记.finditer(文))
    表 = {}
    for 第, 匹 in enumerate(位置们):
        字母 = 匹.group(1)
        if 字母 in 表:
            continue
        起 = 匹.end()
        止 = 位置们[第 + 1].start() if 第 + 1 < len(位置们) else len(文)
        文字 = 归一(文[起:止].split(chr(10))[0].split("姓名")[0])[:24]
        表[字母] = 文字 or 字母
    return 表


def 认字母(值, 原始题干):
    原 = str(值 or "")
    if not 是封闭(原始题干):
        return 归一(去掉姓名(原))
    t = 归一(收紧选项(去掉姓名(原)))
    if not t:
        return ""
    if re.fullmatch(r"[" + 字母们 + r"](?:[" + 字母们 + r"\s,，]*[" + 字母们 + r"])?", t):
        序 = [字母 for 字母 in 字母们 if 字母 in t]
        return " ".join(序)
    有效 = set(选项表(原始题干))
    标记们 = sorted(set(选项标记.findall(" " + t.replace("　", " "))))
    标记们 = [字母 for 字母 in 字母们 if 字母 in 标记们 and 字母 in 有效]
    if 标记们:
        return " ".join(标记们)
    只字母 = sorted({字 for 字 in t if 字 in 有效})
    if 只字母:
        return " ".join(只字母)
    return "其他：" + t[:20]


def 是空(值, 原始题干):
    if 是封闭(原始题干):
        return 归一(re.split(r"姓名", 收紧选项(值))[0]) in [归一(一) for 一 in 封闭空答]
    return 归一(值) in [归一(一) for 一 in 开放空答]


def 结果目录():
    if not 输出目录:
        raise SystemExit("没设输出目录：先 export QUESTIONNAIRE_OUT=<输出目录>")
    路 = os.path.join(输出目录, "结果_题干")
    os.makedirs(路, exist_ok=True)
    return 路


提示 = chr(10).join([
    "这是一张手填的《AI进校园使用情况调查问卷》。按卷面从上到下的顺序读，每道题给出：",
    "题号（卷面上印的阿拉伯数字）、题干原文（完整抄下来，含选项文字）、学生的作答。",
    "只输出一个 JSON 对象，形如：",
    '{"题们":[{"题号":1,"题干":"您的身份是\\nA. 学生\\nB. 老师\\nC. 家长","作答":"A. 学生"}]}',
    "规则：卷面上有几道题就出几项，题干不要省略、不要改写；勾选的写选项原文；",
    "手写的照抄，错别字保留；没填的写「未填」；实在看不清写「[不清]」；卷面上没有的题不要编。",
])


def 解析(文本):
    原文 = str(文本 or "").strip()
    围栏 = re.search(r"```(?:json)?\s*(.*?)```", 原文, re.S)
    if 围栏:
        原文 = 围栏.group(1)
    起, 止 = 原文.find("{"), 原文.rfind("}")
    if 起 < 0 or 止 <= 起:
        return None, "没有 JSON"
    try:
        数据 = json.loads(原文[起:止 + 1])
    except json.JSONDecodeError as 错:
        return None, "JSON 坏了：" + str(错)[:40]
    题们 = 数据.get("题们") if isinstance(数据, dict) else None
    if not isinstance(题们, list) or not 题们:
        return None, "没有题们"
    干净 = []
    for 一 in 题们:
        if not isinstance(一, dict):
            continue
        号 = 一.get("题号")
        干 = str(一.get("题干", "")).strip()
        答 = str(一.get("作答", "")).strip()
        if 干 or 答:
            干净.append({"题号": 号 if isinstance(号, int) else None, "题干": 干, "作答": 答})
    if not 干净:
        return None, "题们都空"
    return 干净, ""


def 读一张(源, 名):
    路 = os.path.join(结果目录(), os.path.splitext(名)[0] + ".json")
    if os.path.isfile(路):
        return "跳过", 名
    try:
        果 = 读图片.处理(源, 提示)
        题们, 错 = 解析(果["文本"])
    except Exception as 异常:
        题们, 错 = None, type(异常).__name__ + "：" + str(异常)[:80]
    记录 = {"文件名": 名, "ok": 题们 is not None, "错误": 错, "题们": 题们 or []}
    with io.open(路, "w", encoding="utf-8") as 文件:
        json.dump(记录, 文件, ensure_ascii=False, indent=1)
    return ("好了" if 题们 is not None else "失败"), 名


def 读结果们(路):
    好, 坏, 读不成 = [], [], []
    for 名 in sorted(os.listdir(路)):
        if not 名.endswith(".json"):
            continue
        try:
            记录 = json.load(io.open(os.path.join(路, 名), encoding="utf-8"))
        except Exception as 异常:
            读不成.append("%s：%s" % (名, type(异常).__name__))
            continue
        if not isinstance(记录, dict) or "题们" not in 记录:
            读不成.append("%s：没有题们" % 名)
            continue
        (好 if 记录.get("ok") else 坏).append(记录)
    return 好, 坏, 读不成


def 主键(原始题干):
    return 归一(str(原始题干 or "").replace(chr(10), " ").split("姓名")[0])[:18] or "（没题干）"


def 聚合():
    好, 坏, 读不成 = 读结果们(结果目录())

    每题 = {}
    行们, 顺序, 不进统计, 归类异 = [], [], [], []
    for 记 in sorted(好, key=lambda x: x["文件名"]):
        try:
            本张 = {}
            for 一 in 记["题们"]:
                键 = 主键(一["题干"])
                袋 = 每题.setdefault(键, {"原文": 一["题干"], "计数": {}, "人次": {},
                                          "空": 0, "出现": 0, "封闭": 是封闭(一["题干"]),
                                          "多选": 是多选(一["题干"])})
                if 键 in 本张:
                    continue
                本张[键] = 一["作答"]
        except Exception as 异常:
            归类异.append("%s：%s" % (记.get("文件名", "?"), type(异常).__name__))
            continue
        if len(本张) < 5:
            不进统计.append("%s：只读出 %d 题" % (记["文件名"], len(本张)))
            continue
        for 键 in 本张:
            if 键 not in 顺序:
                顺序.append(键)
        行们.append((记["文件名"], 本张))
        for 键, 答 in 本张.items():
            袋 = 每题[键]
            袋["出现"] += 1
            if 是空(答, 袋["原文"]):
                袋["空"] += 1
                continue
            if 袋["封闭"]:
                值 = 认字母(答, 袋["原文"])
                袋["计数"][值] = 袋["计数"].get(值, 0) + 1
                if 袋["多选"]:
                    for 字母 in 值.split():
                        袋["人次"][字母] = 袋["人次"].get(字母, 0) + 1
            else:
                值 = 归一(去掉姓名(答))
                袋["计数"][值] = 袋["计数"].get(值, 0) + 1

    顺序.sort(key=lambda 键: -每题[键]["出现"])

    代表, 映射 = [], {}
    for 键 in 顺序:
        干 = 归一(每题[键]["原文"]).split("姓名")[0]
        归到 = 键
        for 基准干, 基准键 in 代表:
            if difflib.SequenceMatcher(None, 干, 基准干).ratio() >= 0.90:
                归到 = 基准键
                break
        else:
            代表.append((干, 键))
        映射[键] = 归到
    if any(映射.get(到) != 到 for 到 in 映射.values()):
        raise SystemExit("题干合并出错：代表键自己又被合并走了")
    合并后 = {}
    for 键, 到 in 映射.items():
        if 到 == 键:
            合并后[键] = 每题[键]
            continue
        袋 = 合并后[到]
        for 值, 数 in 每题[键]["计数"].items():
            袋["计数"][值] = 袋["计数"].get(值, 0) + 数
        for 字母, 数 in 每题[键]["人次"].items():
            袋["人次"][字母] = 袋["人次"].get(字母, 0) + 数
        袋["空"] += 每题[键]["空"]
        袋["出现"] += 每题[键]["出现"]
    每题 = 合并后
    顺序 = [键 for 键 in 顺序 if 键 in 每题]
    撞车 = []
    重映射 = []
    for 名, 本张 in 行们:
        新张 = {}
        for 键, 值 in 本张.items():
            到 = 映射.get(键)
            if 到 not in 每题:
                continue
            if 到 in 新张 and 新张[到] != 值:
                撞车.append("%s：合并后同题出现两个不同作答" % 名)
                continue
            新张[到] = 值
        重映射.append((名, 新张))
    行们 = 重映射
    return 每题, 行们, 顺序, 不进统计, 归类异, 撞车, 好, 坏, 读不成


def 列名们(每题, 顺序):
    粗 = [主键(每题[键]["原文"]) for 键 in 顺序]
    计数 = {}
    for 名 in 粗:
        计数[名] = 计数.get(名, 0) + 1
    见过 = {}
    出 = []
    for 名 in 粗:
        if 计数[名] == 1:
            出.append(名)
            continue
        见过[名] = 见过.get(名, 0) + 1
        出.append("%s（%d）" % (名, 见过[名]))
    if len(set(出)) != len(出):
        raise SystemExit("列名还是撞车了：" + "、".join(出))
    return 出


def 汇总():
    每题, 行们, 顺序, 不进统计, 归类异, 撞车, 好, 坏, 读不成 = 聚合()
    if not 输出目录:
        raise SystemExit("没设输出目录：先 export QUESTIONNAIRE_OUT=<输出目录>")
    os.makedirs(输出目录, exist_ok=True)

    def 题名(键):
        干 = 每题[键]["原文"].replace(chr(10), " ")
        干 = re.split(r"\s+[A-J]\s*[\.．、:：]", 干)[0].strip().split("姓名")[0].strip()
        return 干 or "（没题干）"

    表头 = ["文件名"] + 列名们(每题, 顺序) + ["备注"]
    with io.open(os.path.join(输出目录, "明细_按题干.csv"), "w",
                 encoding="utf-8-sig", newline="") as 文件:
        写 = csv.writer(文件)
        写.writerow(表头)
        for 名, 本张 in 行们:
            写.writerow([名] + [去掉姓名(本张.get(键, "")) for 键 in 顺序]
                        + ["读出 %d 题" % len(本张)])
        for 记 in 坏:
            写.writerow([记["文件名"]] + [""] * len(顺序) + ["读取失败：" + 记.get("错误", "")])
        for 条 in 读不成 + 归类异:
            写.writerow([条.split("：")[0]] + [""] * len(顺序) + ["结果文件坏了：" + 条])

    长表 = []
    文 = ["# 问卷汇总（按题干分组）", "", "XR: C", "",
          "- 日期：2026-11-03",
          "- 抽到照片 %d 张：读出 %d / 读取失败 %d / 结果文件坏了 %d"
          % (len(好) + len(坏) + len(读不成), len(好), len(坏), len(读不成)),
          "- 进统计 %d 张；另有 %d 张读得不全或归类出错，不进统计" % (len(行们), len(不进统计) + len(归类异)),
          "- 原图：`" + (问卷目录 or "（没设 QUESTIONNAIRE_DIR）") + "`",
          "- 分组：按题干原文分组，不认卷面题号。",
          "- 未填：不进分子也不进分母，每节写明「另有 N 份未填」。",
          "- 多选：按「人次」统计，一个人勾了几个就各记一次；占比的分母是作答人数。",
          "- 姓名：一律写成「姓名：〔略〕」。", "", "## 各题统计", ""]

    for 序, 键 in enumerate(顺序, 1):
        袋 = 每题[键]
        总 = sum(袋["计数"].values())
        题 = 题名(键)
        文 += ["### %d. %s" % (序, 题[:80]), ""]
        if not 总:
            文 += ["（%d 份都没填）" % 袋["空"], ""]
            长表.append([序, 题, "（全空）", 0, "", 袋["空"]])
            continue
        if 袋["封闭"] and 袋["多选"]:
            文 += ["作答 %d 份；另有 %d 份未填，不计入。" % (总, 袋["空"]), ""]
            表 = 选项表(袋["原文"])
            文 += ["分母是已作答份数（未填不算）。一人可勾多项，各行占比加起来会超过 100%。", "",
                   "| 选项 | 内容 | 人次 | 占作答份数 |", "|---|---|---|---|"]
            for 字母, 数 in sorted(袋["人次"].items(), key=lambda 项: -项[1]):
                行 = "%s | %s | %d | %.0f%%" % (字母, 表.get(字母, ""), 数,
                                              100.0 * 数 / 总 if 总 else 0)
                文.append("| " + 行 + " |")
                长表.append([序, 题, "多选 " + 字母, 数,
                             "%.0f%%" % (100.0 * 数 / 总 if 总 else 0), 袋["空"]])
            文.append("")
        elif 袋["封闭"]:
            文 += ["作答 %d 份；另有 %d 份未填，不计入。" % (总, 袋["空"]), ""]
            表 = 选项表(袋["原文"])
            文 += ["| 选项 | 内容 | 人数 | 占比 |", "|---|---|---|---|"]
            for 字母, 数 in sorted(袋["计数"].items(), key=lambda 项: -项[1]):
                文.append("| %s | %s | %d | %.0f%% |" % (字母, 表.get(字母, ""), 数, 100.0 * 数 / 总))
                长表.append([序, 题, "单选 " + 字母 + " " + 表.get(字母, ""), 数,
                             "%.0f%%" % (100.0 * 数 / 总), 袋["空"]])
            文.append("")
        else:
            文 += ["作答 %d 份；另有 %d 份未填，不计入。" % (总, 袋["空"]), ""]
            for 值 in sorted(袋["计数"], key=lambda x: -袋["计数"][x]):
                文.append("- %s（%d 人）" % (值, 袋["计数"][值]))
                长表.append([序, 题, "开放 " + 值, 袋["计数"][值], "", 袋["空"]])
            文.append("")

    def 列清单(标题, 条们, 上限=40):
        if not 条们:
            return []
        出 = [标题, ""] + ["- " + 条 for 条 in 条们[:上限]]
        if len(条们) > 上限:
            出.append("- （还有 %d 条没列出来，看 `结果_题干/` 里的原始 JSON）" % (len(条们) - 上限))
        出.append("")
        return 出

    文 += 列清单("## 读得不全、不进统计的（%d 张）" % len(不进统计), 不进统计)
    文 += 列清单("## 归类出错、不进统计的（%d 张）" % len(归类异), 归类异)
    文 += 列清单("## 合并后同一张卷面同题出现两个不同作答、只留先读到的那条（%d 处）" % len(撞车), 撞车)
    文 += 列清单("## 读取失败或结果文件坏了的（%d 条）" % (len(坏) + len(读不成)),
                 [记["文件名"] + "：" + 记.get("错误", "") for 记 in 坏] + 读不成)

    with io.open(os.path.join(输出目录, "汇总_按题干.md"), "w", encoding="utf-8") as 文件:
        文件.write(chr(10).join(文) + chr(10))

    with io.open(os.path.join(输出目录, "统计表.csv"), "w",
                 encoding="utf-8-sig", newline="") as 文件:
        写 = csv.writer(文件)
        写.writerow(["题序", "题目", "选项或原文", "人数", "占比", "未填"])
        写.writerows(长表)

    表文 = ["# 问卷统计表", "", "XR: C", "",
            "共 %d 题；未填不计入，另列一栏。多选题按人次统计。" % len(顺序), "",
            "| 题 | 选项 / 原文 | 人数 | 占比 |", "|---|---|---|---|"]
    上题 = None
    for 序, 题, 项, 数, 比, 空 in 长表:
        if 项 == "（全空）":
            项 = "（全空，未填 %d）" % 空
        表文.append("| %s | %s | %s | %s |" % (题 if 题 != 上题 else "（同上）", 项, 数, 比))
        上题 = 题
    io.open(os.path.join(输出目录, "统计表.md"), "w", encoding="utf-8").write(
        chr(10).join(表文) + chr(10))

    return len(好), len(坏), len(读不成), len(不进统计) + len(归类异), len(顺序)


def 主():
    并行 = 4
    if len(sys.argv) > 1:
        try:
            并行 = int(sys.argv[1])
        except ValueError:
            raise SystemExit("并行数要写整数，例如：python 脚本/问卷汇总_按题干.py 4")
        if 并行 < 1 or 并行 > 16:
            raise SystemExit("并行数要在 1 到 16 之间，现在是 " + str(并行))
    if not 问卷目录 or not os.path.isdir(问卷目录):
        raise SystemExit("照片目录不存在：" + (问卷目录 or "（没设 QUESTIONNAIRE_DIR）"))
    if not 输出目录:
        raise SystemExit("没设输出目录：先 export QUESTIONNAIRE_OUT=<输出目录>")
    os.makedirs(结果目录(), exist_ok=True)

    照片们 = sorted(名 for 名 in os.listdir(问卷目录) if 名.lower().endswith((".jpg", ".jpeg", ".png")))
    已有 = {os.path.splitext(名)[0] + ".json" for 名 in 照片们
            if os.path.isfile(os.path.join(结果目录(), os.path.splitext(名)[0] + ".json"))}
    待做 = [名 for 名 in 照片们 if os.path.splitext(名)[0] + ".json" not in 已有]
    print("照片 %d 张 | 已读 %d | 本次 %d 张 | 并行 %d"
          % (len(照片们), len(照片们) - len(待做), len(待做), 并行))

    起 = time.time()
    完成 = 0
    with ThreadPoolExecutor(max_workers=并行) as 池:
        任务 = [池.submit(读一张, os.path.join(问卷目录, 名), 名) for 名 in 待做]
        for 任 in 任务:
            try:
                状态, 名 = 任.result()
            except Exception as 异常:
                状态, 名 = "失败", type(异常).__name__
            完成 += 1
            print("  [%d/%d] %s %s（%.0f 秒）" % (完成, len(待做), 状态, 名, time.time() - 起), flush=True)

    好, 坏, 读不成, 不进, 题数 = 汇总()
    print("完成：读出 %d，失败 %d，结果坏 %d，不进统计 %d，共 %d 道不同题干，用时 %.0f 秒"
          % (好, 坏, 读不成, 不进, 题数, time.time() - 起))
    print("统计表：" + os.path.join(输出目录, "统计表.csv"))
    print("汇总：" + os.path.join(输出目录, "汇总_按题干.md"))


if __name__ == "__main__":
    主()
