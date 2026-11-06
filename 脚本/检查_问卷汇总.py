
import csv
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)
源文件 = os.path.join(根, "脚本", "问卷汇总_按题干.py")

失败 = []
条数 = 0


def 记(名, 通过, 说明=""):
    global 条数
    条数 += 1
    print(("  ✓ " if 通过 else "  ✗ ") + 名 + ("" if 通过 else "　→　" + str(说明)))
    if not 通过:
        失败.append(名)


def 载入(目录, 路=源文件):
    规格 = importlib.util.spec_from_file_location("问卷汇总_被检", 路)
    模块 = importlib.util.module_from_spec(规格)
    规格.loader.exec_module(模块)
    模块.问卷目录 = 目录
    模块.输出目录 = 目录
    return 模块


封题 = "您担心在校使用 AI 会带来哪些问题？（多选）\nA. 抄袭\nB. 出错\nC. 泄露"
单题 = "如果我校引入 AI，您会使用它？\nA. 经常用\nB. 偶尔\nC. 不用"
开题 = "对于 AI 进校园这件事，你还有别的想法或建议吗？"
身题 = "您的身份是\nA. 学生\nB. 老师\nC. 家长"
规题 = "你觉得学校是否需要制定校园 AI 使用规则？\nA. 非常需要\nB. 可以有"
功题 = "您认为校园里的 AI 工具应该要有哪些功能？"
什题 = "您认为 AI 具有什么样的形象才能受大家欢迎？"
十题 = ("以下大模型中，你听过/使用过的有哪些？（多选）\n"
        "A. ChatGPT\nB. Claude\nC. DeepSeek\nD. 豆包\nE. GLM\nF. Kimi\nG. 混元\nH. 千问")


def 题(号, 干, 答):
    return {"题号": 号, "题干": 干, "作答": 答}


卷子 = {
    "a.jpg": [题(1, 封题, "A B"), 题(2, 单题, "B. 偶尔"), 题(3, 开题, "无"),
              题(4, 身题, "A. 学生；姓名：张三；班级：514"), 题(5, 规题, "B. 可以有"),
              题(6, 功题, "答疑"), 题(7, 什题, "可爱"), 题(8, 十题, "C G H")],
    "b.jpg": [题(1, 封题, "未填"), 题(2, 单题, "未填。"), 题(3, 开题, "未填"),
              题(4, 身题, "身份：未填"), 题(5, 规题, "无"), 题(6, 功题, "改作业"),
              题(7, 什题, "未填"), 题(8, 十题, "未填")],
    "c.jpg": [题(1, 封题, "A B"), 题(2, 单题, "A"), 题(3, 开题, "多用"),
              题(4, 身题, "B. 老师"), 题(5, 规题, "A. 非常需要"), 题(6, 功题, "出卷子"),
              题(7, 什题, "好看"), 题(8, 十题, "A C")],
    "d.jpg": [题(1, 封题, "A"), 题(2, 单题, "C"), 题(3, 开题, "多用"),
              题(4, 身题, "C. 家长"), 题(5, 规题, "B"), 题(6, 功题, "答疑"),
              题(7, 什题, "可爱"), 题(8, 十题, "B")],
}


def 铺(目录, 卷):
    路 = os.path.join(目录, "结果_题干")
    os.makedirs(路, exist_ok=True)
    for 名, 题们 in 卷.items():
        json.dump({"文件名": 名, "ok": True, "错误": "", "题们": 题们},
                  io.open(os.path.join(路, 名 + ".json"), "w", encoding="utf-8"), ensure_ascii=False)


def 找袋(每题, 顺序, 关键词):
    for 键 in 顺序:
        if 关键词 in 每题[键]["原文"]:
            return 每题[键]
    return None


def 读统计表(目录):
    with io.open(os.path.join(目录, "统计表.csv"), encoding="utf-8-sig") as 文件:
        return list(csv.DictReader(文件))


def 行们百分比(长表, 题目关键词, 选项开头):
    for 行 in 长表:
        if 题目关键词 in 行["题目"] and 行["选项或原文"].startswith(选项开头):
            return 行
    return None


def 主():
    临时 = tempfile.mkdtemp(prefix="问卷自检")
    try:
        模块 = 载入(临时)
        铺(临时, 卷子)
        _, 坏, 读不成, 不进, _ = 模块.汇总()
        记("样本全部读出、没有被判成不全", not 坏 and not 读不成 and not 不进,
            "坏 %s 读不成 %s 不进 %s" % (坏, 读不成, 不进))

        每题, 行们, 顺序, _, _, _, _, _, _ = 模块.聚合()
        多袋 = 找袋(每题, 顺序, "担心")
        单袋 = 找袋(每题, 顺序, "会使用它")
        开袋 = 找袋(每题, 顺序, "想法或建议")
        十袋 = 找袋(每题, 顺序, "大模型")
        缺 = [名 for 名, 袋 in (("担心", 多袋), ("会使用", 单袋), ("建议", 开袋), ("大模型", 十袋))
              if not 袋]
        记("四道关键题都归到组里", not 缺, "缺 %s" % 缺)

        汇总 = io.open(os.path.join(临时, "汇总_按题干.md"), encoding="utf-8").read()
        明细 = io.open(os.path.join(临时, "明细_按题干.csv"), encoding="utf-8-sig").read()
        长表 = 读统计表(临时)

        if 缺:
            记("①～④ 依赖上面几道题，跳过", False, "题没归上，后面测不了")
        else:
            记("① 多选：未填 1 份不算进作答（作答 3、空 1）",
                sum(多袋["计数"].values()) == 3 and 多袋["空"] == 1,
                "计数 %s 空 %s" % (多袋["计数"], 多袋["空"]))
            记("①b 单选：带句号的「未填。」也算空（作答 3、空 1）",
                单袋["空"] == 1 and sum(单袋["计数"].values()) == 3,
                "计数 %s 空 %s" % (单袋["计数"], 单袋["空"]))
            记("①c 开放题里的「无」算真回答", 开袋["计数"].get("无") == 1,
                "计数 %s" % 开袋["计数"])
            记("③b 十选项题认得 G、H",
                十袋["人次"].get("H") == 1 and 十袋["计数"].get("C G H") == 1,
                "人次 %s 计数 %s" % (十袋["人次"], 十袋["计数"]))

            行A = 行们百分比(长表, "担心", "多选 A")
            记("④ 统计表里「担心」A 选项占比 = 100%（3/3，分母是已作答份数）",
                行A is not None and 行A["占比"] == "100%",
                "读到的行 %s" % 行A)
            超 = [行 for 行 in 长表 if 行["占比"].endswith("%") and float(行["占比"][:-1]) > 100.0]
            记("④b 统计表里没有任何一行占比超过 100%", not 超, "；".join(str(行) for 行 in 超[:2]))

        越界 = []
        for 键 in 顺序:
            袋 = 每题[键]
            if not 袋["封闭"]:
                continue
            有效 = set(模块.选项表(袋["原文"]))
            for 值 in list(袋["计数"]) + list(袋["人次"]):
                for 字 in str(值).split():
                    if len(字) == 1 and 字.isalpha() and 字 not in 有效:
                        越界.append("%s→%s" % (模块.主键(袋["原文"]), 字))
        记("③ 统计出的字母都在题干选项里", not 越界, "；".join(越界[:4]))

        统计原文 = io.open(os.path.join(临时, "统计表.csv"), encoding="utf-8-sig").read()
        记("② 真名不出现在四个产出文件里",
            "张三" not in 明细 and "张三" not in 汇总 and "张三" not in 统计原文)
        记("②b 姓名位置写成〔略〕", "〔略〕" in 明细)

        未填行 = [行 for 行 in 长表 if "未填" in 行["选项或原文"]]
        记("⑤ 统计表里没有把「未填」当成选项行", not 未填行, "；".join(str(行) for 行 in 未填行[:2]))
        要写的节 = len([键 for 键 in 顺序 if sum(每题[键]["计数"].values()) > 0])
        记("⑤b 每道有作答的题都写明「另有 N 份未填」（没未填也写 0）",
            汇总.count("份未填，不计入") == 要写的节 and "另有 0 份未填" in 汇总,
            "写了 %d 处，应写 %d 处" % (汇总.count("份未填，不计入"), 要写的节))

        记("⑥ 统计表表头是题序/题目/选项或原文/人数/占比/未填",
            list(长表[0].keys()) == ["题序", "题目", "选项或原文", "人数", "占比", "未填"] if 长表 else False,
            list(长表[0].keys()) if 长表 else "空表")
        记("⑥b 每题至少一行", len({行["题序"] for 行 in 长表}) == len(顺序),
            "表里 %d 题，聚合出 %d 题" % (len({行["题序"] for 行 in 长表}), len(顺序)))

        临时2 = tempfile.mkdtemp(prefix="问卷自检2")
        try:
            模块2 = 载入(临时2)
            铺(临时2, {"x.jpg": [题(1, 封题, "A B"), 题(2, 封题, "C"), 题(3, 单题, "A"),
                                  题(4, 开题, "好"), 题(5, 身题, "A. 学生"), 题(6, 规题, "B"),
                                  题(7, 功题, "答疑"), 题(8, 什题, "可爱")]})
            _, 行们2, _, _, _, _, _, _, _ = 模块2.聚合()
            本张 = 行们2[0][1] if 行们2 else {}
            同题键 = [键 for 键 in 本张 if 模块2.主键(封题) == 键]
            记("⑦ 同张卷面同一题出现两次，只留先读到的那条",
                len(同题键) == 1 and 本张[同题键[0]] == "A B",
                "留下的值 %s" % [本张[键] for 键 in 同题键])
        finally:
            shutil.rmtree(临时2, ignore_errors=True)

        临时3 = tempfile.mkdtemp(prefix="问卷自检3")
        try:
            模块3 = 载入(临时3)
            模块3.开放空答 = 模块3.开放空答 + ("无",)
            铺(临时3, 卷子)
            每题3, _, 顺序3, _, _, _, _, _, _ = 模块3.聚合()
            记("⑧ 反向验：开放空答加上「无」后，①c 会变红",
                找袋(每题3, 顺序3, "想法或建议")["计数"].get("无") is None)
        finally:
            shutil.rmtree(临时3, ignore_errors=True)

        临时4 = tempfile.mkdtemp(prefix="问卷自检4")
        try:
            模块4 = 载入(临时4)
            模块4.字母们 = "ABCDEF"
            模块4.选项标记 = re.compile(r"(?:^|[\s　\n])([A-F])[\.．、:：]")
            铺(临时4, 卷子)
            每题4, _, 顺序4, _, _, _, _, _, _ = 模块4.聚合()
            记("⑨ 反向验：字母上限退回 A-F 后，③b 会变红",
                找袋(每题4, 顺序4, "大模型")["人次"].get("H") is None)
        finally:
            shutil.rmtree(临时4, ignore_errors=True)

        临时5 = tempfile.mkdtemp(prefix="问卷自检5")
        改过 = os.path.join(临时5, "改过的汇总.py")
        try:
            原 = io.open(源文件, encoding="utf-8").read()
            坏 = 原.replace('100.0 * 数 / 总 if 总 else 0', '100.0 * 数 / 袋["出现"] if 袋["出现"] else 0')
            io.open(改过, "w", encoding="utf-8").write(坏)
            模块5 = 载入(临时5, 改过)
            铺(临时5, 卷子)
            模块5.汇总()
            行A5 = 行们百分比(读统计表(临时5), "担心", "多选 A")
            记("⑩ 反向验：分母换成含未填的「出现」后，④ 会读成 75%",
                行A5 is not None and 行A5["占比"] == "75%",
                "读到的行 %s" % 行A5)
        finally:
            shutil.rmtree(临时5, ignore_errors=True)
    finally:
        shutil.rmtree(临时, ignore_errors=True)

    print()
    if 失败:
        print("失败 %d / 共 %d：%s" % (len(失败), 条数, "、".join(失败)))
        sys.exit(1)
    print("全部 %d 项通过" % 条数)
    sys.exit(0)


if __name__ == "__main__":
    主()
