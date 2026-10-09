
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 配置, 大模型, 注册表

注册表.全部加载(os.path.join(配置.根目录, "能力"))

from 能力 import _档案, 学生问答

要写盘 = "--确认" in sys.argv

试编号 = "_自检生"
试姓名 = "测试名字甲"
试目录 = _档案.学生目录(试编号)
路径表 = {"名册": _档案.名册路径(), "对照表": _档案.对照表路径()}
目录表 = {"对照表目录": _档案.对照表目录(), "数据目录": _档案.数据目录()}

结果 = []


def 检查(名字, 通过):
    结果.append((名字, bool(通过)))


def 读文本(路径):
    if not os.path.isfile(路径):
        return None
    with open(路径, "r", encoding="utf-8") as 文件:
        return 文件.read()


def 条数(文本):
    try:
        return len(json.loads(文本 or "{}"))
    except ValueError:
        return None


真闸门 = _档案.同意书已签
备份 = {键: 读文本(路径) for 键, 路径 in 路径表.items()}
目录原本在 = {键: os.path.isdir(路径) for 键, 路径 in 目录表.items()}
收尾出问题 = []

if 要写盘 and (_档案.已注册(试编号) or os.path.isdir(试目录)):
    print("  上次跑残留了 " + 试编号 + "（名册或文件夹里还有），先手动清掉再跑。")
    print("  要清的两处：" + 路径表["对照表"] + " 里的这一条，以及 " + 试目录)
    sys.exit(1)


def 只读部分():
    _档案.同意书已签 = lambda: False
    for 名字, 动作 in (("① 没签同意书时「注册」被拒", lambda: _档案.注册(试编号, 姓名=试姓名)),
                       ("② 没签同意书时「记录」被拒", lambda: _档案.记一条(试编号, {"类别": "问答"}))):
        try:
            动作()
            检查(名字, False)
        except ValueError:
            检查(名字, True)
    _档案.同意书已签 = 真闸门

    检查("③ 对照表目录没被列成学生", _档案.对照表目录名 not in _档案.全部学生())
    try:
        _档案.校验编号(_档案.对照表目录名)
        检查("④ 拿「对照表」当编号会被拒", False)
    except ValueError:
        检查("④ 拿「对照表」当编号会被拒", True)

    拦住了 = True
    for 坏 in ("../../etc", "S 01", "a/b", ""):
        try:
            _档案.校验编号(坏)
            拦住了 = False
        except ValueError:
            pass
    检查("⑤ 非法编号（路径穿越 / 空格 / 空）全被拒", 拦住了)


def 写盘部分():
    _档案.同意书已签 = lambda: True
    _档案.注册(试编号, 姓名=试姓名, 学号="2026001", 年级="八年级", 班级="3 班",
              备注="自检用", 家长同意书="已签回")
    检查("⑥ 注册后建出了该生的文件夹", os.path.isdir(试目录))
    检查("⑦ 名册里有这个编号", _档案.已注册(试编号))

    信息 = _档案.学生信息(试编号)
    检查("⑧ 对照表里存下了姓名/学号/年级/班级",
        信息.get("姓名") == 试姓名 and 信息.get("学号") == "2026001"
        and 信息.get("年级") == "八年级" and 信息.get("班级") == "3 班")

    检查("⑨ 名册只存编号与时间（姓名不在名册里）", 试姓名 not in (读文本(路径表["名册"]) or ""))
    _档案.记一条(试编号, {"类别": "问答", "技能包": "demo-real", "问题": "为什么"})
    检查("⑩ 记录文件的路径仍是编号键（姓名可进内容，不当主键）",
        试编号 in _档案.记录路径(试编号) and 试姓名 not in _档案.记录路径(试编号))

    try:
        _档案.记一条(试编号, {"类别": "问答", "问题": "我学号2026001"})
        检查("补充：学号可以写进记录（落盘闸已拆）", True)
    except ValueError as 异常:
        检查("补充：学号可以写进记录（落盘闸已拆）", False)
        print("     补充 抛了 ValueError：" + str(异常).splitlines()[0][:100])

    记录 = _档案.读记录(试编号)
    检查("⑪ 记一条后读得回来", len(记录) >= 1 and 记录[0]["问题"] == "为什么")
    清单允许的键 = {"类别", "技能包", "问题", "时间"}
    检查("⑫ 记录只含采集清单允许的字段", bool(记录) and set(记录[0]) <= 清单允许的键)

    一览 = {一条["编号"]: 一条 for 一条 in _档案.档案一览()}
    检查("⑬ 档案一览里能看到他、条数对、并带出姓名",
        一览.get(试编号, {}).get("记录条数", 0) >= 1 and 一览.get(试编号, {}).get("姓名") == 试姓名)

    捕获 = {}

    def 替身(提示词):
        捕获["提示词"] = 提示词
        return "（自检替身，没有真调模型）"

    真问 = 大模型.问
    大模型.问 = 替身
    try:
        try:
            学生问答.处理(试编号, "demo-real", "分数的除法为什么要倒过来乘？")
            提示词 = 捕获.get("提示词", "")
            检查("⑭ 正常提问照常走到模型（姓名不再被剔）", bool(提示词))
        except Exception as 异常:
            检查("⑭ 正常提问能走到模型（没被别的错拦住）", False)
            print("     ⑭ 抛了 " + type(异常).__name__ + "：" + str(异常).splitlines()[0][:100])

        捕获.clear()
        try:
            学生问答.处理(试编号, "demo-real", "我是" + 试姓名 + "，我有个问题")
            检查("⑮ 学生把姓名写进问题不再被拒（闸门已拆）",
                bool(捕获.get("提示词")))
        except Exception as 异常:
            检查("⑮ 学生把姓名写进问题不再被拒（闸门已拆）", False)
            print("     ⑮ 抛了 " + type(异常).__name__ + "：" + str(异常).splitlines()[0][:100])
    finally:
        大模型.问 = 真问

    try:
        _档案.记一条(试编号, {"类别": "问答", "问题": "我是" + 试姓名})
        检查("㉑ 姓名可以写进记录（落盘闸已拆）", True)
    except ValueError as 异常:
        检查("㉑ 姓名可以写进记录（落盘闸已拆）", False)
        print("     ㉑ 抛了 ValueError：" + str(异常).splitlines()[0][:100])

    try:
        _档案.记资料(试编号, 姓名="")
        检查("㉒ 用空姓名覆盖会被拒", False)
    except ValueError:
        检查("㉒ 用空姓名覆盖会被拒", True)
    检查("㉓ 拒了之后原有姓名还在", _档案.学生信息(试编号).get("姓名") == 试姓名)

    原名 = _档案.记资料(试编号, 姓名="测试名字乙", 学号="2026002", 年级="九年级")
    检查("㉔ 改资料返回原姓名、新值也写进去了",
        原名 == 试姓名 and _档案.学生信息(试编号).get("姓名") == "测试名字乙"
         and _档案.学生信息(试编号).get("学号") == "2026002"
         and _档案.学生信息(试编号).get("年级") == "九年级")

    试2 = tempfile.mkdtemp(prefix="自检原子写_")
    try:
        试路径 = os.path.join(试2, "x.json")
        _档案.原子写(试路径, '{"A": 1}')
        检查("㉕ 原子写写出来的文件读得回来",
            _档案.读JSON(试路径, None, "x.json", dict) == {"A": 1})
        检查("㉖ 原子写没留下 .tmp 残留", not os.path.isfile(试路径 + ".tmp"))
        for 序号, (内容, 说明) in enumerate((('{"A": 1', "半截 JSON"),
                                          ("[1, 2]", "形状不对（列表当表读）"))):
            with open(试路径, "w", encoding="utf-8") as 文件:
                文件.write(内容)
            try:
                _档案.读JSON(试路径, {}, "x.json", dict)
                检查("㉗㉘"[序号] + " " + 说明 + " 必须报错而不是返回空表", False)
            except ValueError:
                检查("㉗㉘"[序号] + " " + 说明 + " 必须报错而不是返回空表", True)
    finally:
        shutil.rmtree(试2, ignore_errors=True)


try:
    只读部分()
    if 要写盘:
        try:
            写盘部分()
        except Exception as 异常:
            检查("写盘部分半路出错：" + type(异常).__name__ + "：" + str(异常).splitlines()[0][:110],
                False)
finally:
    _档案.同意书已签 = 真闸门

    if 要写盘:
        for 键, 路径 in 路径表.items():
            try:
                原 = 备份[键]
                if 原 is None:
                    if os.path.isfile(路径):
                        os.remove(路径)
                else:
                    os.makedirs(os.path.dirname(路径), exist_ok=True)
                    with open(路径, "w", encoding="utf-8") as 文件:
                        文件.write(原)
            except OSError as 异常:
                收尾出问题.append("还原 " + 键 + "：" + str(异常))
        try:
            shutil.rmtree(试目录)
        except FileNotFoundError:
            pass
        except OSError as 异常:
            收尾出问题.append("删自检生文件夹：" + str(异常))
        for 键, 路径 in 目录表.items():
            try:
                if (not 目录原本在[键]) and os.path.isdir(路径) and not os.listdir(路径):
                    os.rmdir(路径)
            except OSError as 异常:
                收尾出问题.append("清空目录 " + 键 + "：" + str(异常))

for 一条 in 收尾出问题:
    检查("收尾：" + 一条, False)

if 要写盘:
    现在名册 = 读文本(路径表["名册"])
    现在对照表 = 读文本(路径表["对照表"])
    检查("⑯ 收尾后名册原样",
        (现在名册 == 备份["名册"]) if 备份["名册"] is not None else (现在名册 is None))
    检查("⑰ 收尾后对照表原样 —— 自检没删到既有条目",
        (现在对照表 == 备份["对照表"]) if 备份["对照表"] is not None else (现在对照表 is None))
    检查("⑱ 自检生的文件夹已删掉", not os.path.isdir(试目录))

    之前 = 条数(备份["对照表"]) if 备份["对照表"] is not None else 0
    之后 = 条数(现在对照表) if 现在对照表 is not None else 0
    检查("⑲ 对照表条数与跑之前一致（两边都数得出来才算过）",
        之前 is not None and 之后 is not None and 之前 == 之后)
    print("   （对照表：跑之前 %s 条，跑完 %s 条%s）"
          % (之前, 之后, "" if 之前 == 之后 else "  ← 条数变了！"))

    检查("⑳ 目录状态回到跑之前",
        all(os.path.isdir(路径) == 目录原本在[键] for 键, 路径 in 目录表.items()))
else:
    print("   （没加 --确认，只跑了只读部分；要跑全部请加 --确认）")

坏的 = 0
for 名字, 通过 in 结果:
    print(("  通过  " if 通过 else "  失败  ") + 名字)
    坏的 += 0 if 通过 else 1
print("全部 %d 项通过" % len(结果) if not 坏的 else "%d 项失败" % 坏的)
sys.exit(0 if not 坏的 else 1)
