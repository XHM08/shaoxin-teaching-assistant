
import os
import re

from 地基 import 落盘, 配置

代号长度上限 = 64
描述长度上限 = 1024

合法代号 = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def 校验代号(代号):
    if len(代号) > 代号长度上限:
        raise ValueError("技能名超过 " + str(代号长度上限) + " 个字符：" + 代号)
    if not 合法代号.match(代号):
        raise ValueError(
            "技能名只允许小写字母、数字、连字符，不能以连字符开头或结尾，"
            "也不能连着两个连字符。现在拿到的是：" + 代号
        )


def 校验描述(描述):
    if not 描述.strip():
        raise ValueError("description 不能为空")
    if len(描述) > 描述长度上限:
        raise ValueError("description 超过 " + str(描述长度上限) + " 个字符")


def 组装技能包(代号, 描述, 正文, 其它字段=None):
    校验代号(代号)
    校验描述(描述)

    行表 = ["---", "name: " + 代号, "description: " + 描述]
    if 其它字段:
        for 键 in 其它字段:
            行表.append(键 + ": " + str(其它字段[键]))
    行表.append("---")
    行表.append("")
    行表.append(正文.strip())
    行表.append("")
    return "\n".join(行表)


def 拆头尾(原文):
    原文 = 原文.strip()
    if not 原文.startswith("---"):
        return {}, 原文

    片段 = 原文.split("---", 2)
    if len(片段) < 3:
        return {}, 原文

    头部 = {}
    for 行 in 片段[1].strip().split("\n"):
        if ":" in 行:
            键, 值 = 行.split(":", 1)
            头部[键.strip()] = 值.strip()
    return 头部, 片段[2].strip()


def 保存技能包(输出目录, 代号, 原文):
    校验代号(代号)
    目录 = os.path.join(输出目录, 代号)
    os.makedirs(目录, exist_ok=True)
    路径 = os.path.join(目录, "SKILL.md")
    落盘.带时间备份(路径)
    落盘.原子写文本(路径, 原文)
    return 路径


def 读取技能包(技能包目录):
    路径 = os.path.join(技能包目录, "SKILL.md")
    with open(路径, "r", encoding="utf-8") as 文件:
        return 拆头尾(文件.read())


def 技能包目录(代号):
    return os.path.join(配置.取目录("技能包"), 代号)


def 读技能包全文(代号):
    目录 = 技能包目录(代号)
    if not os.path.isdir(目录):
        raise ValueError("没有这个技能包：" + 代号)
    头部, 正文 = 读取技能包(目录)
    return 组装技能包(头部.get("name", 代号), 头部.get("description", ""), 正文)


def 技能包清单():
    目录 = 配置.取目录("技能包")
    if not os.path.isdir(目录):
        return []
    条目表 = []
    for 代号 in sorted(os.listdir(目录)):
        if not os.path.isdir(os.path.join(目录, 代号)):
            continue
        try:
            头部, _ = 读取技能包(os.path.join(目录, 代号))
            描述 = 头部.get("description", "")
        except (OSError, ValueError):
            描述 = ""
        条目表.append({"技能包代号": 代号, "描述": 描述})
    return 条目表
