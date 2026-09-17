
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 配置, 技能包, 注册表

if "--确认" not in sys.argv:
    print("  这个自检会真的写盘（教师数据/ 与 技能包/）。")
    print("  它跑之前先备份、跑完无条件还原；确认要跑就加上 --确认。")
    sys.exit(2)

注册表.全部加载(os.path.join(配置.根目录, "能力"))

import 能力._评定 as 评定
import 能力.讲解评定 as P
import 能力.技能包校订 as X

结果 = []


def 检查(名字, 通过, 说明=""):
    结果.append((名字, bool(通过), 说明))


def 试(动作):
    try:
        return True, 动作()
    except Exception as 异常:
        return False, 异常


教师数据 = 配置.取目录("教师数据")
技能包根 = 配置.取目录("技能包")
备份根 = tempfile.mkdtemp(prefix="评定自检备份_")
试包 = "ztest-" + str(os.getpid())

原来就有 = os.path.isdir(教师数据)
if 原来就有:
    shutil.copytree(教师数据, os.path.join(备份根, "教师数据"))
    shutil.rmtree(教师数据, ignore_errors=True)

真问 = P.大模型.问
P.大模型.问 = lambda *a, **k: "（自检桩）先拿整数试一试，再问他 4 里面有几个 1/2。"

try:
    甲 = P.处理出讲解("demo-real", "4 ÷ 1/2 = ?")
    检查("① 空池里第一条的号是 1", 甲["条目号"] == 1, "实际：" + str(甲["条目号"]))

    乙 = P.处理出讲解("demo-real", "3/4 ÷ 1/2 = ?")
    检查("② 第二条的号接着涨", 乙["条目号"] == 2, "实际：" + str(乙["条目号"]))

    台 = P.处理台账("全部")
    检查("③ 台账里两条都在，且都是「待评」",
        len(台["条目"]) == 2 and all(一["状态"] == "待评" for 一 in 台["条目"]),
        "拿到 " + str(len(台["条目"])) + " 条")

    好, 东西 = 试(lambda: P.处理记评定(1, "挺不错的"))
    检查("④ 自造的判定被拒（实验五要靠这三种做统计）",
        (not 好) and isinstance(东西, ValueError) and "可接受" in str(东西),
        "拿到：" + (type(东西).__name__ + "：" + str(东西)[:36] if not 好 else "没拦住"))

    好1, 东西1 = 试(lambda: P.处理记评定(99, "可接受"))
    好2, 东西2 = 试(lambda: P.处理记评定("x", "可接受"))
    检查("⑤ 不存在的号、不是数字的号，都被拒",
        (not 好1) and isinstance(东西1, ValueError)
        and (not 好2) and isinstance(东西2, ValueError),
        str(东西1)[:30] + " ｜ " + str(东西2)[:30])

    P.处理记评定(1, "需修改", "改成先问他 4 里面有几个 1/2", "不能直接说乘以 2")
    已评 = P.处理台账("已评")["条目"]
    待评 = P.处理台账("待评")["条目"]
    检查("⑥ 记完判定：已评 1 条、待评 1 条，改后版本也存下了",
        len(已评) == 1 and len(待评) == 1 and 已评[0]["判定"] == "需修改"
        and "有几个 1/2" in 已评[0]["讲解B"],
        "已评 %d 条、待评 %d 条" % (len(已评), len(待评)))

    允许 = {"条目号", "状态", "判定", "题目", "技能包", "讲解A", "讲解B", "老师原话", "时间"}
    多出来的 = set()
    for 一 in P.处理台账("全部")["条目"]:
        多出来的 |= set(一) - 允许
    检查("⑦ 台账里没有多余字段（题目由项目组自备，不该夹带学生信息）",
        not 多出来的, "多出来：" + "、".join(sorted(多出来的)))

    坏路径 = 评定.待评路径() + ".坏"
    with open(坏路径, "w", encoding="utf-8") as 文件:
        文件.write('{"条目号": 1, "题目": "半截')
    好3, 东西3 = 试(lambda: 评定.读JSONL(坏路径, "待评.jsonl"))
    检查("⑧ 半截 JSON 读不出来时**报错**，不是返回空",
        (not 好3) and isinstance(东西3, ValueError) and "不会覆盖" in str(东西3),
        str(东西3)[:44] if not 好3 else "居然返回了 " + str(东西3))
    if os.path.isfile(坏路径):
        os.remove(坏路径)

    影子 = os.path.join(os.path.dirname(评定.待评路径()), "_自检坏池.jsonl")
    with open(影子, "w", encoding="utf-8") as 文件:
        文件.write('{"条目号": 1}\n{"条目号":')
    好4, 东西4 = 试(lambda: 评定.读JSONL(影子, "待评.jsonl"))
    os.remove(影子)
    检查("⑨ 池子有坏行时不许当成空池（当成空池 → 下一个号又是 1 → 重号）",
        (not 好4) and isinstance(东西4, ValueError),
        str(东西4)[:40] if not 好4 else "居然返回了 " + str(东西4))

    原文 = ("---\nname: " + 试包 + "\ndescription: 自检用\nnote: 这个键必须活下来\n---\n\n"
          "## 核心自述\n原话一\n\n## 教师名言\n原话二\n\n"
          "### 三级标题不该被当成新的一段\n乱入\n")
    技能包.保存技能包(技能包根, 试包, 原文)
    看 = X.处理看节(试包)
    检查("⑩ 拆节：2 段，且「### 三级标题」没被算成新的一段",
        len(看["条目"]) == 2 and [一["标题"] for 一 in 看["条目"]] == ["核心自述", "教师名言"],
        "拿到：" + str([一["标题"] for 一 in 看["条目"]]))

    X.处理存节(试包, "核心自述", "改过的这一段", "他说的原话")
    with open(os.path.join(技能包.技能包目录(试包), "SKILL.md"), "r", encoding="utf-8") as 文件:
        改后 = 文件.read()
    历史 = os.path.join(技能包.技能包目录(试包), "_历史")
    备份们 = sorted(os.listdir(历史)) if os.path.isdir(历史) else []
    旧 = ""
    if 备份们:
        with open(os.path.join(历史, 备份们[0]), "r", encoding="utf-8") as 文件:
            旧 = 文件.read()

    检查("⑪ 改一段之后：改的进去了，别段与 frontmatter 其它键一字未动",
        "改过的这一段" in 改后 and "原话二" in 改后
        and "note: 这个键必须活下来" in 改后
        and "### 三级标题不该被当成新的一段" in 改后,
        "该在的都在" if "原话二" in 改后 and "note: 这个键必须活下来" in 改后
        else "有内容被弄丢了")
    检查("⑫ 覆盖前留了备份，且备份就是改前那一版",
        bool(备份们) and 旧 == 原文, "备份：" + str(备份们))

    好5, 东西5 = 试(lambda: X.处理存节(试包, "根本没有这一段", "x"))
    好6, 东西6 = 试(lambda: X.处理存节(试包, "核心自述", "   "))
    检查("⑬ 段名对不上、内容为空的，都拒（不做模糊匹配，也不按序号猜）",
        (not 好5) and isinstance(东西5, ValueError)
        and (not 好6) and isinstance(东西6, ValueError),
        str(东西5)[:44])
except Exception as 异常:
    检查("自检半路出错", False, type(异常).__name__ + "：" + str(异常))
finally:
    P.大模型.问 = 真问
    shutil.rmtree(技能包.技能包目录(试包), ignore_errors=True)
    shutil.rmtree(教师数据, ignore_errors=True)
    if 原来就有:
        shutil.copytree(os.path.join(备份根, "教师数据"), 教师数据)
    shutil.rmtree(备份根, ignore_errors=True)

坏的 = 0
print()
for 名字, 通过, 说明 in 结果:
    print(("  通过  " if 通过 else "  失败  ") + 名字 + ("　→　" + 说明 if 说明 else ""))
    坏的 += 0 if 通过 else 1
print("全部 %d 项通过" % len(结果) if not 坏的 else "%d 项失败" % 坏的)
sys.exit(0 if not 坏的 else 1)
