
import io
import os

from 地基 import 注册表, 配置, 技能包, 文件属性
from 能力.写文件 import _定路 as 定文件路


def 处理(名称="", md路径="", 代号="", 描述="", 覆盖="否"):
    全, _根名 = 定文件路(md路径)
    if not os.path.isfile(全):
        raise ValueError("这份 md 不在：%s" % md路径)
    代号 = str(代号 or "").strip() or str(名称 or "").strip()
    if not 代号:
        raise ValueError("要给一个代号（小写字母、数字、连字符，例如 xiaozeyun-yuwen）")
    技能包.校验代号(代号)

    原文 = io.open(全, encoding="utf-8").read()
    if not 原文.strip():
        raise ValueError("这份 md 是空的：%s" % md路径)

    if 原文.lstrip().startswith("---"):
        成品 = 原文
        头部 = 原文.split("---")[1] if 原文.count("---") >= 2 else ""
        if "name:" not in 头部:
            raise ValueError("md 有 front matter 但缺 name 字段，补上或去掉 front matter 再登记")
    else:
        要描述 = str(描述 or "").strip()
        if not 要描述:
            raise ValueError("这份 md 没有 front matter，就得给一句描述（它会写进 description）")
        成品 = 技能包.组装技能包(代号, 要描述, 原文)

    已有 = os.path.isdir(技能包.技能包目录(代号))
    if 已有 and str(覆盖 or "否").strip() != "是":
        raise ValueError("技能包「%s」已经存在；要覆盖就把「覆盖」填「是」（旧 SKILL.md 会备份进 _历史/）" % 代号)

    成品 = chr(10).join(一行 for 一行 in 成品.split(chr(10))
                        if not 一行.strip().upper().startswith("XR:"))
    路 = 技能包.保存技能包(配置.取目录("技能包"), 代号, 成品)
    try:
        标记 = 文件属性.写XR(路, "C")
    except ValueError as 异常:
        raise ValueError("技能包写好了，但 XR 属性没写进去：%s" % 异常)
    if "XR:" in 成品:
        raise ValueError("XR 还在正文里，应该只在文件属性里：" + 路)

    清单 = [一.get("技能包代号") for 一 in 技能包.技能包清单()]
    if 代号 not in 清单:
        raise ValueError("写进去了但「查技能包」列不出来：%s（清单有 %d 个）" % (代号, len(清单)))

    return {"正文": "技能包「%s」已%s，清单里现在有 %d 个。路径：%s（XR 在文件属性里：%s）"
                    % (代号, "覆盖" if 已有 else "新建", len(清单), 路, 标记),
            "代号": 代号, "路径": 路, "覆盖": 已有, "清单条数": len(清单), "XR": 标记}


注册表.登记(
    代号="登记技能包",
    标题="登记技能包",
    说明="把一份 md 写成正式技能包（带 name/description 头），写完立刻核对「查技能包」列得出来。",
    参数=[
        {"代号": "名称", "标签": "显示用名称（留空则用代号）", "类型": "text", "必填": False,
         "示例": "肖泽云-语文"},
        {"代号": "md路径", "标签": "要登记的 md 路径", "类型": "text", "必填": True,
         "示例": "材料/_批量识图/肖泽云-语文-全97张.md"},
        {"代号": "代号", "标签": "代号（小写字母/数字/连字符）", "类型": "text", "必填": True,
         "示例": "xiaozeyun-yuwen"},
        {"代号": "描述", "标签": "什么时候该用这份技能包（md 无 front matter 时必填）",
         "类型": "text", "必填": False, "示例": "肖泽云老师讲高中语文：先疏通字词再抓关键词"},
        {"代号": "覆盖", "标签": "已存在时是否覆盖（是/否）", "类型": "text", "必填": False,
         "示例": "否"},
    ],
    处理函数=处理,
)
