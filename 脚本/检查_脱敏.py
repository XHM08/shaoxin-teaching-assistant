
import io
import json
import os
import shutil
import sys
import tempfile

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)

from 地基 import 配置, 脱敏, 大模型
from 能力 import _审查, _记忆

失败 = []
条数 = 0


def 记(名, 通过, 说明=""):
    global 条数
    条数 += 1
    print(("  ✓ " if 通过 else "  ✗ ") + 名 + ("" if 通过 else "　→　" + str(说明)))
    if not 通过:
        失败.append(名)


def 写对照表(目录, 内容):
    路 = os.path.join(目录, "对照表")
    os.makedirs(路, exist_ok=True)
    with io.open(os.path.join(路, "姓名对照表.json"), "w", encoding="utf-8") as 文件:
        if isinstance(内容, str):
            文件.write(内容)
        else:
            json.dump(内容, 文件, ensure_ascii=False)


def 主():
    原取目录, 原问 = 配置.取目录, 大模型.问
    临时 = tempfile.mkdtemp(prefix="脱敏-")
    try:
        配置.取目录 = lambda 名: 临时 if 名 == "学生数据" else 原取目录(名)
        if 配置.取目录("学生数据") != 临时:
            print("接管没生效：拒绝往下跑（否则会动真实档案）")
            return 1
        记("① 学生数据目录接管生效", True)


        记("② 对照表不存在：原样返回，不抛", 脱敏.脱敏("王小明答错了") == ("王小明答错了", 0))

        写对照表(临时, {"S01": {"姓名": "王小明"}, "S02": {"姓名": "李明"},
                       "S03": {"姓名": "小明"}, "S04": {"姓名": "张"},
                       "S05": {"姓名": "刘洋"}, "S06": {"姓名": "刘洋"}})
        文本, 次数 = 脱敏.脱敏("王小明、小明、刘洋、张、李明都错了")
        记("③ 姓名换编号；长名优先（王小明→S01，小明→S03）",
           "S01" in 文本 and "S03" in 文本 and "王小明" not in 文本, 文本)
        记("④ 重名归并成「某学生」", "某学生" in 文本 and "刘洋" not in 文本, 文本)
        记("⑤ 单字姓名不换（「张」保留，避免误伤正文）", "张" in 文本, 文本)
        记("⑥ 替换次数对得上", 次数 == 4, 次数)
        记("⑦ 不在表里的姓名不瞎换", 脱敏.脱敏("周同学没来")[0] == "周同学没来")


        写对照表(临时, "{ 这不是 JSON")
        记("⑧ 对照表读坏：原样返回、不抛", 脱敏.脱敏("王小明") == ("王小明", 0))
        写对照表(临时, "{}")
        记("⑨ 空对照表：原样返回", 脱敏.脱敏("王小明") == ("王小明", 0))


        配置.取目录 = lambda 名: (_ for _ in ()).throw(KeyError("目录"))
        记("⑩ 取目录抛异常时退化成不换，不抛出去", 脱敏.脱敏("王小明") == ("王小明", 0))
        配置.取目录 = lambda 名: 临时 if 名 == "学生数据" else 原取目录(名)


        写对照表(临时, {"S01": {"姓名": "王小明"}})
        捕获 = []

        def 假问(提示词原文, **参数):
            捕获.append(str(提示词原文))
            return "APPROVE"

        大模型.问 = 假问
        _审查.审查("王小明这道题错了，我让他重做。", "王小明的错题怎么讲？",
                   [{"工具": "查学生档案", "结果": "王小明 错因：通分没掌握"}])
        送审 = 捕获[-1] if 捕获 else ""
        记("⑪ 审查送审的提示词里没有姓名，只有编号",
           "王小明" not in 送审 and "S01" in 送审, 送审[:80])

        捕获.clear()
        _记忆.抽取("王小明这次考了 62 分", "好的，记下王小明的成绩。")
        抽审 = 捕获[-1] if 捕获 else ""
        记("⑫ 记忆抽取送审的提示词里也没有姓名", "王小明" not in 抽审, 抽审[:80])
    except Exception as 错:
        记("检查本身跑完了", False, "%s: %s" % (type(错).__name__, 错))
    finally:
        配置.取目录, 大模型.问 = 原取目录, 原问
        shutil.rmtree(临时, ignore_errors=True)

    print()
    print("全部 %d 项通过" % 条数 if not 失败 else "通过 %d / 共 %d" % (条数 - len(失败), 条数))
    return 0 if not 失败 else 1


if __name__ == "__main__":
    sys.exit(主())
