
import io
import json
import os
import shutil
import sys
import tempfile

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)

from 地基 import 审计, 材料, 技能包, 课件

失败 = []
条数 = 0


def 记(名, 通过, 说明=""):
    global 条数
    条数 += 1
    print(("  ✓ " if 通过 else "  ✗ ") + 名 + ("" if 通过 else "　→　" + str(说明)))
    if not 通过:
        失败.append(名)


def 会拒(函数, *参数):
    try:
        函数(*参数)
    except Exception:
        return True
    return False


def 技能包那块():
    记("① 合法代号过：demo-pack / a1 / pack-2",
       all(not 会拒(技能包.校验代号, 好) for 好 in ("demo-pack", "a1", "pack-2")))
    记("② 坏代号被拒：大写 / 连字符打头 / 连字符结尾 / 双连字符",
       all(会拒(技能包.校验代号, 坏) for 坏 in ("Demo", "-x", "x-", "a--b")))
    记("③ 代号长度：64 过、65 拒",
       not 会拒(技能包.校验代号, "a" * 64) and 会拒(技能包.校验代号, "a" * 65))
    记("④ 描述必填、1024 过、1025 拒",
       会拒(技能包.校验描述, "   ")
       and not 会拒(技能包.校验描述, "字" * 1024) and 会拒(技能包.校验描述, "字" * 1025))

    原文 = 技能包.组装技能包("demo-pack", "一句话说明", "正文第一行\n正文第二行")
    头, 正文 = 技能包.拆头尾(原文)
    记("⑤ 组装与拆头尾往返一致",
       头.get("name") == "demo-pack" and 头.get("description") == "一句话说明"
       and 正文 == "正文第一行\n正文第二行", "头=%s 正文=%r" % (头, 正文))

    头2, 正文2 = 技能包.拆头尾("没有头部的一段正文\n第二行")
    记("⑥ 没有 YAML 头时整篇当正文", 头2 == {} and 正文2.startswith("没有头部"), 头2)
    头3, 正文3 = 技能包.拆头尾("---\n只有开头分隔")
    记("⑦ 半截头部不吞正文", 头3 == {} and "只有开头分隔" in 正文3, 头3)


def 材料那块():
    print("  · 清洗文字：%r" % (材料.清洗文字("  a\n\n\n\nb  "),))
    记("⑧ 清洗文字：连续空行压成一段、首尾空白去掉",
       材料.清洗文字("  a\n\n\n\nb  ") == "a\n\nb", 材料.清洗文字("  a\n\n\n\nb  "))

    上限 = 材料.抽取字上限
    截 = 材料._封顶("字" * (上限 + 50))
    记("⑨ 超长截断且说明里带原文长度",
       len(截) < 上限 + 120 and "已截断" in 截 and str(上限 + 50) in 截, 截[-80:])
    记("⑩ 没超长就原样给", 材料._封顶("短") == "短")

    记("⑪ 列号换算：A=1 / Z=26 / AA=27 / ab=28 / 空=0",
       [材料._列号(x) for x in ("A", "Z", "AA", "ab", "")] == [1, 26, 27, 28, 0],
       [材料._列号(x) for x in ("A", "Z", "AA", "ab", "")])
    记("⑫ 页号：slide12.xml=12", 材料._页号("slide12.xml") == 12)


def 课件那块():
    记("⑬ 安全文件名：非法字符与空格换成连字符",
       课件.安全文件名("a/b:c*? d") == "a-b-c-d", 课件.安全文件名("a/b:c*? d"))
    记("⑭ 安全文件名：空值给兜底名", 课件.安全文件名("  ") == "课件", 课件.安全文件名("  "))

    记("⑮ 要点成行：字符串原样、列表按行",
       课件.要点成行(" 一行 ") == "一行"
       and 课件.要点成行(["第一条", "第二条"]) == "第一条\n第二条",
       repr(课件.要点成行(" 一行 ")))
    记("⑯ 取要点：字符串按行拆、列表去空项、None 给空表",
       课件.取要点({"points": "甲\n\n乙"}) == ["甲", "乙"]
       and 课件.取要点({"points": [" 甲 ", "", "乙"]}) == ["甲", "乙"]
       and 课件.取要点({}) == [], 课件.取要点({"points": "甲\n\n乙"}))

    数据 = {"pages": [{"title": "分数的除法"}, {"title": "试一试"}, {"title": "练一练"}]}
    课件.归一类型(数据)
    类型 = [页["kind"] for 页 in 数据["pages"]]
    记("⑰ 归一类型：首页封面、末页小结、标题带练→练习、带试一试→例题",
       类型 == ["封面", "例题", "小结"], 类型)

    数据2 = {"pages": [{"title": "头", "kind": "封面"}, {"title": "尾", "kind": "知识"}]}
    课件.归一类型(数据2)
    记("⑱ 归一类型：已经填了合法 kind 的不改",
       [页["kind"] for 页 in 数据2["pages"]] == ["封面", "知识"],
       [页["kind"] for 页 in 数据2["pages"]])


def 审计那块():
    临时 = tempfile.mkdtemp(prefix="审计-")
    原取目录, 原读取 = 审计.配置.取目录, 审计.配置.读取
    try:
        审计.配置.取目录 = lambda 名: 临时
        审计.配置.读取 = lambda: {"审计": True}
        记录 = 审计.记一笔("自检", {"提问字数": 12}, 成功=True, 秒数=0.25)
        路 = os.path.join(临时, "审计.jsonl")
        行 = [json.loads(x) for x in io.open(路, encoding="utf-8").read().splitlines() if x.strip()]
        记("⑲ 记一笔写出合法 JSON 行，字段齐",
           len(行) == 1 and set(行[0]) == {"时间", "能力", "成功", "秒数", "元信息"}
           and 行[0]["能力"] == "自检" and 行[0]["成功"] is True and 行[0]["秒数"] == 0.25,
           str(行)[:160])
        记("⑳ 元信息原样留住，备注为空时不写这个字段",
           行[0]["元信息"] == {"提问字数": 12} and "备注" not in 行[0], str(行[0]))
        记("㉑ 时间形如 2026-10-23 17:00:00",
           bool(__import__("re").fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d", 行[0]["时间"])),
           行[0]["时间"])

        审计.配置.读取 = lambda: {"审计": False}
        审计.记一笔("自检二")
        行2 = [x for x in io.open(路, encoding="utf-8").read().splitlines() if x.strip()]
        记("㉒ 审计关掉时不写盘（内存里仍有记录）",
           len(行2) == 1 and 审计.最近记录[-1]["能力"] == "自检二", len(行2))
    finally:
        审计.配置.取目录, 审计.配置.读取 = 原取目录, 原读取
        shutil.rmtree(临时, ignore_errors=True)


def 主():
    try:
        for 一块 in (技能包那块, 材料那块, 课件那块, 审计那块):
            一块()
    except Exception as 错:
        记("检查本身跑完了", False, "%s: %s" % (type(错).__name__, 错))
    print()
    print("全部 %d 项通过" % 条数 if not 失败 else "通过 %d / 共 %d" % (条数 - len(失败), 条数))
    return 0 if not 失败 else 1


if __name__ == "__main__":
    sys.exit(主())
