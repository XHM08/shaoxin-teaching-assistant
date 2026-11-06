
import csv
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

问卷目录 = r"C:\Users\25768\Desktop\科赛\knowledge\01-背景与文献\收集的文件\调查问卷"
输出目录 = r"C:\Users\25768\Desktop\科赛\knowledge\04-数据与实验\问卷汇总"
题数 = 11
小题名 = {
    1: "你对AI的了解", 2: "用过AI的场景", 3: "班级引入AI的想法",
    4: "遇到学习难题倾向", 5: "虚拟形象建议", 6: "希望AI具备的功能",
    7: "真人授课 vs AI 授课", 8: "听过/用过的模型", 9: "AI 本身有无风险",
    10: "AI 建议是否有用", 11: "当下 AI 存在的问题",
}
开放题 = (2, 5, 6, 11)

键们 = ",".join('"题%d":"…"' % 号 for 号 in range(1, 题数 + 1))
读取提示 = chr(10).join([
    "这是一张手填的《AI进校园使用情况调查问卷》。按题号把学生填的内容读出来。",
    "只输出一个 JSON 对象，键是 题1 到 题" + str(题数) + " 外加 备注，例如：",
    "{" + 键们 + ',"备注":""}',
    "规则：勾选的写选项原文；手写的照抄，错别字保留；没填的写「未填」；实在看不清写「[不清]」。",
])


def 结果目录():
    路 = os.path.join(输出目录, "结果")
    os.makedirs(路, exist_ok=True)
    return 路


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
    if not isinstance(数据, dict):
        return None, "不是对象"
    return 数据, ""


def 读一张(源, 名):
    路 = os.path.join(结果目录(), os.path.splitext(名)[0] + ".json")
    if os.path.isfile(路):
        return "跳过", 名
    try:
        果 = 读图片.处理(源, 读取提示)
        数据, 错 = 解析(果["文本"])
    except Exception as 异常:
        数据, 错 = None, type(异常).__name__ + "：" + str(异常)[:80]
    记录 = {"文件名": 名, "ok": 数据 is not None, "错误": 错}
    if 数据 is not None:
        for 号 in range(1, 题数 + 1):
            记录["题%d" % 号] = str(数据.get("题%d" % 号, "")).strip()
        记录["备注"] = str(数据.get("备注", "")).strip()
    with io.open(路, "w", encoding="utf-8") as 文件:
        json.dump(记录, 文件, ensure_ascii=False, indent=1)
    return ("好了" if 数据 is not None else "失败"), 名


def 汇总():
    路 = os.path.join(结果目录())
    记录们 = []
    for 名 in sorted(os.listdir(路)):
        if 名.endswith(".json"):
            记录们.append(json.load(io.open(os.path.join(路, 名), encoding="utf-8")))
    好 = [记录 for 记录 in 记录们 if 记录.get("ok")]
    坏 = [记录 for 记录 in 记录们 if not 记录.get("ok")]

    os.makedirs(输出目录, exist_ok=True)
    表头 = ["文件名"] + ["题%d" % 号 for 号 in range(1, 题数 + 1)] + ["备注"]
    with io.open(os.path.join(输出目录, "明细.csv"), "w", encoding="utf-8-sig", newline="") as 文件:
        写 = csv.writer(文件)
        写.writerow(表头)
        for 记录 in sorted(好, key=lambda x: x["文件名"]):
            写.writerow([记录["文件名"]] + [记录.get("题%d" % 号, "") for 号 in range(1, 题数 + 1)]
                        + [记录.get("备注", "")])
        for 记录 in sorted(坏, key=lambda x: x["文件名"]):
            写.writerow([记录["文件名"]] + [""] * 题数 + ["读取失败：" + 记录.get("错误", "")])

    计数, 填空 = {}, {}
    for 记录 in 好:
        for 号 in range(1, 题数 + 1):
            值 = str(记录.get("题%d" % 号, "")).strip()
            if not 值 or 值 in ("未填", "[不清]", ""):
                continue
            if 号 in 开放题:
                填空.setdefault(号, []).append(值)
            else:
                计数.setdefault(号, {})
                计数[号][值] = 计数[号].get(值, 0) + 1

    行们 = ["# 问卷汇总", "", "XR: C", "",
            "- 日期：2026-11-03",
            "- 样本：%d 份成功 / %d 份失败（共 %d 张照片）" % (len(好), len(坏), len(记录们)),
            "- 原图：`" + 问卷目录 + "`", "",
            "## 封闭题计数", ""]
    for 号 in sorted(计数):
        总 = sum(计数[号].values())
        行们 += ["### 题%d %s（%d 份作答）" % (号, 小题名.get(号, ""), 总), "",
                 "| 选项 | 人数 | 占比 |", "|---|---|---|"]
        for 选项, 数 in sorted(计数[号].items(), key=lambda x: -x[1]):
            行们.append("| %s | %d | %.0f%% |" % (选项, 数, 100.0 * 数 / 总 if 总 else 0))
        行们.append("")
    行们 += ["## 开放题原文", ""]
    for 号 in sorted(填空):
        行们 += ["### 题%d %s（%d 条）" % (号, 小题名.get(号, ""), len(填空[号])), ""]
        行们 += ["- " + 条 for 条 in 填空[号]]
        行们.append("")
    if 坏:
        行们 += ["## 读取失败的", ""]
        行们 += ["- %s：%s" % (记录["文件名"], 记录.get("错误", "")) for 记录 in 坏]
        行们.append("")
    with io.open(os.path.join(输出目录, "汇总.md"), "w", encoding="utf-8") as 文件:
        文件.write(chr(10).join(行们) + chr(10))
    return 好, 坏


def 主():
    目录 = sys.argv[1] if len(sys.argv) > 1 else 问卷目录
    并行 = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    if not os.path.isdir(目录):
        raise SystemExit("照片目录不存在：" + 目录)
    照片们 = sorted(名 for 名 in os.listdir(目录) if 名.lower().endswith((".jpg", ".jpeg", ".png")))
    已有 = {os.path.splitext(名)[0] + ".json" for 名 in 照片们
          if os.path.isfile(os.path.join(结果目录(), os.path.splitext(名)[0] + ".json"))}
    待做 = [名 for 名 in 照片们 if os.path.splitext(名)[0] + ".json" not in 已有]
    print("照片 %d 张 | 已读 %d | 本次 %d 张 | 并行 %d" % (len(照片们), len(照片们) - len(待做), len(待做), 并行))

    起 = time.time()
    完成 = 0
    with ThreadPoolExecutor(max_workers=并行) as 池:
        任务 = [池.submit(读一张, os.path.join(目录, 名), 名) for 名 in 待做]
        for 任 in 任务:
            try:
                状态, 名 = 任.result()
            except Exception as 异常:
                状态, 名 = "失败", type(异常).__name__
            完成 += 1
            print("  [%d/%d] %s %s（%.0f 秒）" % (完成, len(待做), 状态, 名, time.time() - 起), flush=True)

    好, 坏 = 汇总()
    print("完成：成功 %d，失败 %d，用时 %.0f 秒" % (len(好), len(坏), time.time() - 起))
    print("明细：" + os.path.join(输出目录, "明细.csv"))
    print("汇总：" + os.path.join(输出目录, "汇总.md"))


if __name__ == "__main__":
    主()
