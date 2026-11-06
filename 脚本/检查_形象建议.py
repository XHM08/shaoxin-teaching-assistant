
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
源文件 = os.path.join(根, "脚本", "形象建议汇总.py")

失败 = []
条数 = 0

形题 = "您认为 AI 具有什么样的形象才能受大家欢迎？"
给题 = "如果需要给校园 AI 设计一个虚拟形象，你的建议是？"


def 记(名, 通过, 说明=""):
    global 条数
    条数 += 1
    print(("  ✓ " if 通过 else "  ✗ ") + 名 + ("" if 通过 else "　→　" + str(说明)))
    if not 通过:
        失败.append(名)


def 载入():
    规格 = importlib.util.spec_from_file_location("形象建议_被检", 源文件)
    模块 = importlib.util.module_from_spec(规格)
    规格.loader.exec_module(模块)
    return 模块


def 铺(目录, 卷):
    路 = os.path.join(目录, "结果_题干")
    os.makedirs(路, exist_ok=True)
    for 名, 题们 in 卷.items():
        json.dump({"文件名": 名, "ok": True, "错误": "", "题们": 题们},
                  io.open(os.path.join(路, 名 + ".json"), "w", encoding="utf-8"), ensure_ascii=False)


def 跑一遍(模块, 目录, 卷, 坏=False, 半截=False):
    铺(目录, 卷)
    if 坏:
        json.dump({"文件名": "坏.jpg", "ok": False, "错误": "没有 JSON", "题们": []},
                  io.open(os.path.join(目录, "结果_题干", "坏.jpg.json"), "w", encoding="utf-8"),
                  ensure_ascii=False)
    if 半截:
        io.open(os.path.join(目录, "结果_题干", "半截.jpg.json"), "w", encoding="utf-8").write('{"ok":tr')
    模块.输出目录 = 目录
    模块.主()
    return (io.open(os.path.join(目录, "形象建议.md"), encoding="utf-8").read(),
            io.open(os.path.join(目录, "形象建议.csv"), encoding="utf-8-sig").read())


def 某题一段(文, 序):
    块们 = re.split(r"\n## ", 文)
    for 块 in 块们:
        if 块.startswith("%d. " % 序):
            return 块
    return ""


def 主():
    模块 = 载入()

    记("①「[不清]」不会被当成不表态",
        "不表态 / 不需要" not in 模块.归类("不要[不清]·好看一点"),
        "%s" % 模块.归类("不要[不清]·好看一点"))
    记("①b「无线」不会命中「无」", 模块.归类("无线") == [], "%s" % 模块.归类("无线"))
    记("①c 整句「无」算不表态", 模块.归类("无") == ["不表态 / 不需要"], "%s" % 模块.归类("无"))
    记("①d 单独「帅」归到外形·真人", "外形·真人" in 模块.归类("帅"), "%s" % 模块.归类("帅"))
    记("①e 一句话命中两类都记", set(模块.归类("可爱点,声音好听")) == {"气质·可爱", "声音"},
        "%s" % 模块.归类("可爱点,声音好听"))

    临时 = tempfile.mkdtemp(prefix="形象自检")
    try:
        卷 = {"a.jpg": [{"题号": 1, "题干": 形题, "作答": "可爱"},
                        {"题号": 2, "题干": 给题, "作答": "小狗"}],
              "b.jpg": [{"题号": 1, "题干": 形题, "作答": "云力中物"},
                        {"题号": 2, "题干": 给题, "作答": "无"}]}
        文, 表 = 跑一遍(模块, 临时, 卷, 坏=True, 半截=True)

        记("② 头部写出读出 2 张 / 读取失败 1 张 / 文件坏了 1 个",
            "读出 2 张" in 文 and "读取失败 1 张" in 文 and "结果文件坏了 1 个" in 文,
            [行 for 行 in 文.splitlines() if "底数" in 行])
        记("②b 两题各自成节，节里作答数各为 2",
            "作答 2 份" in 某题一段(文, 1) and "作答 2 份" in 某题一段(文, 2),
            (某题一段(文, 1)[:30], 某题一段(文, 2)[:30]))
        记("②c 合计是两题之和（4 份，不去重）", "作答共 4 份" in 文,
            [行 for 行 in 文.splitlines() if "合计" in 行])
        记("②d 第一题的未归类份数是 1", "| 未归类 | 1 |" in 某题一段(文, 1),
            [行 for 行 in 某题一段(文, 1).splitlines() if "未归类" in 行])
        记("②e 第二题没有未归类（「无」进了不表态）", "| 未归类 | 0 |" in 某题一段(文, 2),
            [行 for 行 in 某题一段(文, 2).splitlines() if "未归类" in 行])
        记("②f 未归类那条也进了 csv", "云力中物" in 表 and "未归类" in 表)
    finally:
        shutil.rmtree(临时, ignore_errors=True)

    临时2 = tempfile.mkdtemp(prefix="形象自检2")
    try:
        模块2 = 载入()
        模块2.归类表 = 模块2.归类表 + [("外观细节", ("云力",), ())]
        卷2 = {"a.jpg": [{"题号": 1, "题干": 形题, "作答": "云力中物"},
                         {"题号": 2, "题干": 给题, "作答": "小狗"}]}
        文2, 表2 = 跑一遍(模块2, 临时2, 卷2)
        行 = [行 for 行 in 表2.splitlines() if "云力中物" in 行]
        记("③ 反向验：词表加上「云力」后，那条不再落在未归类",
            bool(行) and "未归类" not in 行[0], 行)
    finally:
        shutil.rmtree(临时2, ignore_errors=True)

    临时3 = tempfile.mkdtemp(prefix="形象自检3")
    try:
        次们 = []
        for 次 in (1, 2):
            子 = os.path.join(临时3, str(次))
            实例 = 载入()
            卷3 = {"a.jpg": [{"题号": 1, "题干": 形题, "作答": 答} for 答 in ("可爱", "漂亮", "温和")],
                   "b.jpg": [{"题号": 1, "题干": 形题, "作答": 答} for 答 in ("有趣", "聪明", "帅")]}
            _, 表3 = 跑一遍(实例, 子, 卷3)
            次们.append(表3)
        记("④ 同一输入跑两次，归类表逐字节一致", 次们[0] == 次们[1])
        记("④b 归类表不是空表", len(次们[0].strip().splitlines()) > 1)
    finally:
        shutil.rmtree(临时3, ignore_errors=True)

    print()
    if 失败:
        print("失败 %d / 共 %d：%s" % (len(失败), 条数, "、".join(失败)))
        sys.exit(1)
    print("全部 %d 项通过" % 条数)
    sys.exit(0)


if __name__ == "__main__":
    主()
