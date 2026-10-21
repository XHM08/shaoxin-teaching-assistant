
import os
import re
import sys

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)

from 地基 import 注册表

失败 = []
条数 = 0


def 记(名, 通过, 说明=""):
    global 条数
    条数 += 1
    print(("  ✓ " if 通过 else "  ✗ ") + 名 + ("" if 通过 else "　→　" + str(说明)))
    if not 通过:
        失败.append(名)


def 页面组名():
    文本 = open(os.path.join(根, "网页", "首页.html"), encoding="utf-8").read()
    return re.findall(r"<summary>([^<\s]+)\s*<span class=\"g-hint\"", 文本)


def 问题列表(代号们, 映射, 默认组, 组名们, 页面名们):
    问题 = []
    孤儿 = sorted(set(映射) - set(代号们))
    if 孤儿:
        问题.append("组表里有不存在的代号：" + "、".join(孤儿))
    漏 = [代号 for 代号 in 代号们 if 映射.get(代号, 默认组) == 默认组]
    if 漏:
        问题.append("没分组的：" + "、".join(漏))
    for 组 in 组名们:
        if not [代号 for 代号 in 代号们 if 映射.get(代号) == 组]:
            问题.append("空组：" + 组)
    if list(组名们) != list(页面名们):
        问题.append("组名与页面不一致：注册表 %s / 页面 %s" % (list(组名们), list(页面名们)))
    return 问题


def 主():
    注册表.全部加载(os.path.join(根, "能力"))
    代号们 = 注册表.全部名字()
    页面名们 = 页面组名()

    记("① 能力加载得到，且与分组清单总数一致（>40 个才算加载全）",
       len(代号们) > 40 and len(代号们) == sum(len(x["能力们"]) for x in 注册表.分组清单()), len(代号们))
    记("② 页面上读得到四个组的文案", len(页面名们) == 4, 页面名们)

    问题 = 问题列表(代号们, 注册表.代号到分组, 注册表.默认分组, 注册表.组名顺序, 页面名们)
    记("③ 分组完整：没有孤儿代号、没有漏分组、四组都非空、组名与页面一致",
       not 问题, "；".join(问题))

    清单 = 注册表.分组清单()
    记("④ 分组清单条目数与能力总数一致、顺序固定",
       sum(len(x["能力们"]) for x in 清单) == len(代号们)
       and [x["分组"] for x in 清单] == list(注册表.组名顺序), [x["分组"] for x in 清单])


    import 本地服务
    视图 = 本地服务.能力视图()
    记("⑤ 接口视图里每个能力都带 分组 字段，且不是「其他」",
       len(视图) == len(代号们) and all(x.get("分组") and x["分组"] != 注册表.默认分组 for x in 视图),
       [x["代号"] for x in 视图 if not x.get("分组") or x["分组"] == 注册表.默认分组][:5])


    坏1 = dict(注册表.代号到分组)
    坏1["根本没有这个能力"] = "上课"
    记("⑥ 反向验：组表塞进一个不存在的代号要报红",
       bool(问题列表(代号们, 坏1, 注册表.默认分组, 注册表.组名顺序, 页面名们)))

    坏2 = dict(注册表.代号到分组)
    坏2.pop("创造模式", None)
    记("⑦ 反向验：拿掉一个能力的分组要报红",
       bool(问题列表(代号们, 坏2, 注册表.默认分组, 注册表.组名顺序, 页面名们)))

    记("⑧ 反向验：页面组名改一个字要报红",
       bool(问题列表(代号们, 注册表.代号到分组, 注册表.默认分组, 注册表.组名顺序,
                    ["上课", "学生", "材料与技能包", "环境与工具"])))

    print()
    print("全部 %d 项通过" % 条数 if not 失败 else "通过 %d / 共 %d" % (条数 - len(失败), 条数))
    return 0 if not 失败 else 1


if __name__ == "__main__":
    sys.exit(主())
