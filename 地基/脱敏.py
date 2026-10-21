
import json
import os

from 地基 import 配置

_对照目录 = "对照表"
_对照文件 = "姓名对照表.json"
占位 = "某学生"


def _对照表路径():
    try:
        根 = 配置.取目录("学生数据")
    except Exception:
        return ""
    return os.path.join(根, _对照目录, _对照文件)


def 读对照表():
    路 = _对照表路径()
    if not 路 or not os.path.isfile(路):
        return {}
    try:
        with open(路, encoding="utf-8") as 文件:
            内容 = json.load(文件)
    except (OSError, json.JSONDecodeError):
        return {}
    return 内容 if isinstance(内容, dict) else {}


def 姓名映射():
    表 = {}
    重名 = set()
    for 编号, 记录 in 读对照表().items():
        if not isinstance(记录, dict):
            continue
        姓名 = str(记录.get("姓名", "")).strip()
        if len(姓名) < 2:
            continue
        编号 = str(编号)
        if 姓名 not in 表:
            表[姓名] = 编号
        elif 表[姓名] != 编号:
            重名.add(姓名)
            表[姓名] = 占位
    return 表


def 脱敏(文本):
    原文 = "" if 文本 is None else str(文本)
    if not 原文:
        return 原文, 0
    映射 = 姓名映射()
    if not 映射:
        return 原文, 0
    次数 = 0

    for 姓名 in sorted(映射, key=len, reverse=True):
        次数 += 原文.count(姓名)
        原文 = 原文.replace(姓名, 映射[姓名])
    return 原文, 次数
