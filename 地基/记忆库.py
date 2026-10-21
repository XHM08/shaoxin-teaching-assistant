
import json
import os
import time

from 地基 import 配置

关键记忆上限 = 200
摘要保留条数 = 40
_目录名 = "记忆"


def 目录():
    路 = os.path.join(配置.取目录("教师数据"), _目录名)
    os.makedirs(路, exist_ok=True)
    return 路


def _读行(路):
    结果 = []
    if not os.path.isfile(路):
        return 结果
    try:
        with open(路, encoding="utf-8") as 文件:
            for 行 in 文件:
                行 = 行.strip()
                if not 行:
                    continue
                try:
                    结果.append(json.loads(行))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return 结果


def _追加(路, 记录):
    os.makedirs(os.path.dirname(路), exist_ok=True)
    with open(路, "a", encoding="utf-8") as 文件:
        文件.write(json.dumps(记录, ensure_ascii=False) + "\n")


def 记一条(内容, 类别="关键", 来源=""):
    内容 = str(内容 or "").strip()
    if not 内容:
        return None
    记录 = {"时间": time.strftime("%Y-%m-%d %H:%M:%S"), "类别": str(类别 or "关键"),
            "内容": 内容[:300], "来源": str(来源 or "")[:60]}
    _追加(os.path.join(目录(), "关键记忆.jsonl"), 记录)
    修剪()
    return 记录


def 修剪(上限=None):
    上限 = 关键记忆上限 if 上限 is None else int(上限)
    路 = os.path.join(目录(), "关键记忆.jsonl")
    记录们 = _读行(路)
    if len(记录们) <= 上限:
        return 0
    留 = 记录们[-上限:]
    with open(路, "w", encoding="utf-8") as 文件:
        for 记录 in 留:
            文件.write(json.dumps(记录, ensure_ascii=False) + "\n")
    return len(记录们) - len(留)


def 取记忆(最多=20):
    记录们 = _读行(os.path.join(目录(), "关键记忆.jsonl"))
    return list(reversed(记录们))[:int(最多)]


def 记忆文本(最多=12):
    记录们 = 取记忆(最多)
    if not 记录们:
        return ""
    return "\n".join("- " + 记录["内容"] for 记录 in 记录们)


def 存摘要(会话, 覆盖到, 摘要):
    会话 = str(会话 or "默认")[:40]
    摘要 = str(摘要 or "").strip()
    if not 摘要:
        return None
    记录 = {"时间": time.strftime("%Y-%m-%d %H:%M:%S"), "会话": 会话,
            "覆盖到": int(覆盖到 or 0), "摘要": 摘要[:2000]}
    _追加(os.path.join(目录(), "摘要.jsonl"), 记录)
    _修剪摘要()
    return 记录


def _修剪摘要():
    路 = os.path.join(目录(), "摘要.jsonl")
    记录们 = _读行(路)
    if len(记录们) <= 摘要保留条数:
        return 0
    with open(路, "w", encoding="utf-8") as 文件:
        for 记录 in 记录们[-摘要保留条数:]:
            文件.write(json.dumps(记录, ensure_ascii=False) + "\n")
    return len(记录们) - 摘要保留条数


def 取摘要(会话, 最多=3):
    会话 = str(会话 or "默认")[:40]
    记录们 = [记录 for 记录 in _读行(os.path.join(目录(), "摘要.jsonl"))
             if 记录.get("会话") == 会话]
    return list(reversed(记录们))[:int(最多)]


def 摘要文本(会话, 最多=3):
    记录们 = 取摘要(会话, 最多)
    if not 记录们:
        return ""
    return "\n".join("- " + 记录["摘要"] for 记录 in 记录们)


def 清摘要(会话):
    会话 = str(会话 or "默认")[:40]
    路 = os.path.join(目录(), "摘要.jsonl")
    记录们 = _读行(路)
    留 = [记录 for 记录 in 记录们 if 记录.get("会话") != 会话]
    删了 = len(记录们) - len(留)
    if 删了:
        with open(路, "w", encoding="utf-8") as 文件:
            for 记录 in 留:
                文件.write(json.dumps(记录, ensure_ascii=False) + chr(10))
    return 删了


def 清空(范围="全部"):
    if 范围 in ("关键", "全部"):
        for 名 in ("关键记忆.jsonl",):
            路 = os.path.join(目录(), 名)
            if os.path.isfile(路):
                os.remove(路)
    if 范围 in ("摘要", "全部"):
        路 = os.path.join(目录(), "摘要.jsonl")
        if os.path.isfile(路):
            os.remove(路)
