
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)
源文件 = os.path.join(根, "脚本", "开放题关键词.py")

失败 = []
条数 = 0


def 记(名, 通过, 说明=""):
    global 条数
    条数 += 1
    print(("  ✓ " if 通过 else "  ✗ ") + 名 + ("" if 通过 else "　→　" + str(说明)))
    if not 通过:
        失败.append(名)


def 载入():
    规格 = importlib.util.spec_from_file_location("开放题关键词_被检", 源文件)
    模块 = importlib.util.module_from_spec(规格)
    规格.loader.exec_module(模块)
    return 模块


def 主():
    模块 = 载入()

    词们, _ = 模块.算([("学习", 10), ("刷题", 1)])
    份 = dict(词们)
    记("① 同一句被 10 人写，「学习」的份数是 10 而不是 1",
        份.get("学习") == 10, "算出来 %s" % 份.get("学习"))

    词2 = [词 for 词, _ in 模块.算([("写作业", 2)])[0]]
    记("② 只在「写作业」里出现的「作业」被盖住，不单列",
        ("写作业" in 词2) and ("作业" not in 词2), "拿到 %s" % 词2)
    词2b = [词 for 词, _ in 模块.算([("写作业", 2), ("作业", 5)])[0]]
    记("②b 短词份数更高时不盖（真按份数比，不是见到包含就删）",
        ("作业" in 词2b) and ("写作业" in 词2b), "拿到 %s" % 词2b)

    词们3, _ = 模块.算([("使用的问题 123 很好", 3)])
    词3 = [词 for 词, _ in 词们3]
    记("③ 停用词「问题」「使用」与纯数字不进结果",
        not any(词 in ("问题", "使用", "123") for 词 in 词3), "拿到 %s" % 词3[:8])
    记("③b 纯字母片段不进结果", not any(词.isascii() for 词 in 词3), "拿到 %s" % 词3[:8])

    词们4, 门4 = 模块.算([("甲" * 2, 1), ("乙乙", 40)])
    记("④ 门槛按总份数的 5% 算（41 份 → 门槛 2）", 门4 == 2, "门槛 %s" % 门4)
    记("④b 只有 1 份提到的词被门槛挡掉", all(份 >= 门4 for _, 份 in 词们4),
        "拿到 %s" % 词们4)

    临时 = tempfile.mkdtemp(prefix="关键词自检")
    五题 = ["你对 AI 有什么建议吗？", "你对 AI 有什么想法吗？", "你对 AI 有什么期待吗？",
            "你对 AI 有什么意见吗？", "你对 AI 有什么看法吗？"]
    三卷 = {
        "a.jpg": ["多讲例题", "讲慢一点", "多练几道", "少布置作业", "多讲例题"],
        "b.jpg": ["多讲例题", "多练几道", "讲慢一点", "多练几道", "多讲例题"],
        "c.jpg": ["多讲例题", "讲慢一点", "多讲例题", "少布置作业", "多讲例题"],
    }
    try:
        结果 = []
        for 次 in (1, 2):
            子 = os.path.join(临时, str(次))
            os.makedirs(os.path.join(子, "结果_题干"), exist_ok=True)
            for 名, 答们 in 三卷.items():
                题们 = [{"题号": 号, "题干": 干, "作答": 答}
                        for 号, (干, 答) in enumerate(zip(五题, 答们), 1)]
                json.dump({"文件名": 名, "ok": True, "错误": "", "题们": 题们},
                          io.open(os.path.join(子, "结果_题干", 名 + ".json"), "w", encoding="utf-8"),
                          ensure_ascii=False)
            模块.输出目录 = 子
            模块.主()
            结果.append(io.open(os.path.join(子, "开放题关键词.csv"), encoding="utf-8-sig").read())
        记("⑤ 同一输入跑两次，关键词表逐字节一致", 结果[0] == 结果[1])
        记("⑤b 关键词表不是空表", len(结果[0].strip().splitlines()) > 1,
            "只有表头，说明每题都被当成「写法太少」跳过了")
    finally:
        shutil.rmtree(临时, ignore_errors=True)

    模块2 = 载入()
    模块2.门槛 = lambda 总份: 1
    词们5, 门5 = 模块2.算([("甲甲", 1), ("乙乙", 40)])
    记("⑥ 反向验：门槛改成 1 后，只有 1 份的词会出现（④b 会变红）",
        门5 == 1 and any(份 == 1 for _, 份 in 词们5), "拿到 %s" % 词们5)

    print()
    if 失败:
        print("失败 %d / 共 %d：%s" % (len(失败), 条数, "、".join(失败)))
        sys.exit(1)
    print("全部 %d 项通过" % 条数)
    sys.exit(0)


if __name__ == "__main__":
    主()
