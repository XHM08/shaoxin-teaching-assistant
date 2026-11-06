
import csv
import importlib.util
import io
import os
import re
import sys

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)
输出目录 = os.environ.get("QUESTIONNAIRE_OUT", "")

最短 = 2
最长 = 6
每张最多 = 15
最少写法数 = 3

停用 = set("""
一些 一个 这个 那个 自己 还有 因为 所以 但是 如果 时候 东西 事情 方面 比较 非常 特别
很多 有点 感觉 觉得 没有 不是 就是 还是 或者 以及 等等 之类 其他 其它 现在 之后 以后
之前 一般 主要 使用 进行 需要 应该 希望 用来 用于 可以 什么 问题
""".split())
分词清洗 = re.compile(r"[^\u4e00-\u9fa5A-Za-z0-9]+")


def 门槛(总份):
    return max(2, int(round(总份 * 0.05)))


def 载入():
    规格 = importlib.util.spec_from_file_location(
        "问卷汇总_被读", os.path.join(根, "脚本", "问卷汇总_按题干.py"))
    模块 = importlib.util.module_from_spec(规格)
    规格.loader.exec_module(模块)
    模块.输出目录 = 输出目录
    return 模块


def 片断们(句):
    净 = 分词清洗.sub("|", 句)
    出 = set()
    for 段 in 净.split("|"):
        for 长 in range(最短, 最长 + 1):
            for 起 in range(0, len(段) - 长 + 1):
                片 = 段[起:起 + 长]
                if 片 in 停用 or 片.isdigit():
                    continue
                if not re.search(r"[\u4e00-\u9fa5]", 片):
                    continue
                出.add(片)
    return 出


def 算(答案们):
    总份 = sum(人数 for _, 人数 in 答案们)
    片到份 = {}
    for 句, 人数 in 答案们:
        for 片 in 片断们(句):
            片到份[片] = 片到份.get(片, 0) + 人数
    倒排 = {}
    留 = {}
    for 片 in sorted(片到份, key=lambda 词: (-len(词), 词)):
        份 = 片到份[片]
        候选 = set()
        for 字 in set(片):
            候选.update(倒排.get(字, ()))
        被盖 = any(片 in 长 and 片到份[长] >= 份 for 长 in 候选)
        if 被盖:
            continue
        留[片] = 份
        for 字 in set(片):
            倒排.setdefault(字, []).append(片)
    门 = 门槛(总份)
    词们 = [(片, 份) for 片, 份 in sorted(留.items(), key=lambda 对: (-对[1], -len(对[0]), 对[0]))
            if 份 >= 门]
    return 词们, 门


def 主():
    if not 输出目录:
        raise SystemExit("没设输出目录：先 export QUESTIONNAIRE_OUT=<问卷汇总目录>")
    模块 = 载入()
    每题, 行们, 顺序, _, _, _, _, _, _ = 模块.聚合()

    段们, 长表, 跳过 = [], [], []
    for 序, 键 in enumerate(顺序, 1):
        袋 = 每题[键]
        if 袋["封闭"]:
            continue
        题 = re.sub(r"\s+", " ", 袋["原文"]).strip()[:40]
        总份 = sum(袋["计数"].values())
        if len(袋["计数"]) < 最少写法数:
            跳过.append("第 %d 题「%s」：%d 份作答只有 %d 种写法，不做词频"
                        % (序, 题, 总份, len(袋["计数"])))
            continue
        词们, 门 = 算(list(袋["计数"].items()))
        段们 += ["### %d. %s" % (序, 题), "",
                 "作答 %d 份，写法 %d 种；列出至少 %d 份回答里出现过的词（按份数从多到少）："
                 % (总份, len(袋["计数"]), 门), "",
                 "| 词 | 提到它的份数 | 占作答 |", "|---|---|---|"]
        for 词, 份 in 词们[:每张最多]:
            段们.append("| %s | %d | %.0f%% |" % (词, 份, 100.0 * 份 / 总份 if 总份 else 0))
        if len(词们) > 每张最多:
            段们.append("")
            段们.append("（另有 %d 个词过门槛但没列在这儿，全量在 `开放题关键词.csv`）"
                        % (len(词们) - 每张最多))
        段们.append("")
        for 词, 份 in 词们:
            长表.append([序, 题, 词, 份, 总份])

    文 = ["# 开放题关键词", "", "XR: C", "",
          "- 日期：2026-11-03",
          "- 口径：一份回答里出现就算 1 份；同一条里出现多次不重复计；一条被多人写成同一个词时按人数计。",
          "- 去重：短词被更长的词整块包含、且份数不高于长词时，只报长词。",
          "- 丢掉：停用词（含「问题」「使用」这类泛词）、纯数字、不含汉字的片段（AI、APP 这类）。",
          "- 门槛：每题按自己的作答份数算，5% 且不少于 2 份。",
          "- 排序：按份数从多到少；份数相同的，长词在前。",
          "- `开放题关键词.csv` 是过门槛的全量，本文件每题最多列 %d 个。" % 每张最多, ""]
    if 跳过:
        文 += ["## 没做词频的题", ""] + ["- " + 条 for 条 in 跳过] + [""]
    文 += 段们
    with io.open(os.path.join(输出目录, "开放题关键词.md"), "w", encoding="utf-8") as 文件:
        文件.write(chr(10).join(文) + chr(10))
    with io.open(os.path.join(输出目录, "开放题关键词.csv"), "w",
                 encoding="utf-8-sig", newline="") as 文件:
        写 = csv.writer(文件)
        写.writerow(["题序", "题目", "关键词", "提到它的份数", "该题作答份数"])
        写.writerows(长表)
    print("开放题 %d 道做了词频，%d 道跳过，关键词 %d 条"
          % (len({行[0] for 行 in 长表}), len(跳过), len(长表)))
    print("关键词表：" + os.path.join(输出目录, "开放题关键词.md"))


if __name__ == "__main__":
    主()
