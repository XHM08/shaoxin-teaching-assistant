
import importlib
import os

已登记能力 = {}

参数可用字段 = ("代号", "标签", "类型", "必填", "可选项", "可选项来源", "示例")

可选项来源类别 = frozenset({"材料", "技能包", "课件", "providers"})


def 登记(代号, 标题, 说明, 参数, 处理函数):
    if 代号 in 已登记能力:
        raise ValueError("能力名重复：" + 代号 + "（两个文件用了同一个名字）")
    if not callable(处理函数):
        raise ValueError("能力 " + 代号 + " 的处理函数不是函数")

    for 参数项 in 参数:
        if "代号" not in 参数项 or "标签" not in 参数项:
            raise ValueError("能力 " + 代号 + " 的参数必须有「代号」和「标签」：" + str(参数项))
        多余字段 = [键 for 键 in 参数项 if 键 not in 参数可用字段]
        if 多余字段:
            raise ValueError(
                "能力 " + 代号 + " 的参数写了不认识的字段：" + ", ".join(多余字段)
                + "。允许的有：" + ", ".join(参数可用字段)
            )
        来源 = 参数项.get("可选项来源")
        if 来源 and 来源 not in 可选项来源类别:
            raise ValueError(
                "能力 " + 代号 + " 的参数「" + str(参数项.get("代号")) + "」把「可选项来源」写错了："
                + str(来源) + "。认得的只有："
                + "、".join(sorted(可选项来源类别))
                + "。写错不会报错，只会让界面上那个下拉框空着。"
            )

    已登记能力[代号] = {
        "标题": 标题,
        "说明": 说明,
        "参数": 参数,
        "处理函数": 处理函数,
    }


def 全部加载(能力目录):
    if not os.path.isdir(能力目录):
        return []

    importlib.import_module("能力")
    已加载 = []
    for 文件名 in sorted(os.listdir(能力目录)):
        if not 文件名.endswith(".py") or 文件名.startswith("_"):
            continue
        模块名 = "能力." + 文件名[:-3]
        importlib.import_module(模块名)
        已加载.append(模块名)
    return 已加载


def 全部名字():
    return sorted(已登记能力)


def 取能力(代号):
    if 代号 not in 已登记能力:
        raise KeyError("没有这个能力：" + 代号 + "。可用的有：" + ", ".join(全部名字()))
    return 已登记能力[代号]


def 校验参数(代号, 实参):
    条目 = 取能力(代号)
    认识的 = {参数项["代号"] for 参数项 in 条目["参数"]}
    不认识的 = [键 for 键 in 实参 if 键 not in 认识的]
    if 不认识的:
        raise ValueError("能力 " + 代号 + " 不认识这些参数：" + ", ".join(不认识的)
                         + "。它认识的参数是：" + (", ".join(sorted(认识的)) or "（无）"))
    缺的 = [参数项["代号"] for 参数项 in 条目["参数"]
            if 参数项.get("必填") and not str(实参.get(参数项["代号"], "")).strip()]
    if 缺的:
        raise ValueError("能力 " + 代号 + " 缺必填参数：" + ", ".join(缺的))
    return 条目["处理函数"]


def 能力清单():
    结果 = []
    for 代号 in 全部名字():
        条目 = 已登记能力[代号]
        结果.append({
            "代号": 代号,
            "标题": 条目["标题"],
            "说明": 条目["说明"],
            "参数": 条目["参数"],
        })
    return 结果
