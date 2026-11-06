
import io
import json
import os
import time

from 地基 import 配置

最多条数 = 300


def _路():
    目录 = 配置.取目录("教师数据")
    os.makedirs(目录, exist_ok=True)
    return os.path.join(目录, "审查记录.jsonl")


def 记一条(判定, 问题们, 老师说的="", 回答字数=0, 用了几件工具=0):
    一条 = {
        "时间": time.strftime("%Y-%m-%d %H:%M:%S"),
        "判定": str(判定 or "没跑成"),
        "问题们": 问题们 or [],
        "老师说的": (老师说的 or "")[:200],
        "回答字数": int(回答字数 or 0),
        "工具次数": int(用了几件工具 or 0),
    }
    try:
        with io.open(_路(), "a", encoding="utf-8") as 文件:
            文件.write(json.dumps(一条, ensure_ascii=False) + chr(10))
        if os.path.getsize(_路()) > 最多条数 * 800:
            修剪()
    except OSError:
        return 一条
    return 一条


def 取最近(最多=50):
    行们 = []
    路 = _路()
    if not os.path.isfile(路):
        return []
    with io.open(路, encoding="utf-8") as 文件:
        for 行 in 文件:
            行 = 行.strip()
            if not 行:
                continue
            try:
                行们.append(json.loads(行))
            except json.JSONDecodeError:
                continue
    return list(reversed(行们))[:最多]


def 统计():
    记录们 = 取最近(最多条数)
    有问题的 = [一 for 一 in 记录们 if 一.get("判定") == "有问题"]
    没跑成 = [一 for 一 in 记录们 if 一.get("判定") == "没跑成"]
    通过的 = [一 for 一 in 记录们 if 一.get("判定") == "通过"]
    跳过的 = [一 for 一 in 记录们 if 一.get("判定") == "跳过"]
    问题条数 = sum(len(一.get("问题们") or []) for 一 in 记录们)
    return {"总轮数": len(记录们), "有问题轮数": len(有问题的),
            "通过轮数": len(通过的), "跳过轮数": len(跳过的),
            "没跑成轮数": len(没跑成), "问题条数": 问题条数}


def 修剪(上限=None):
    上限 = 上限 or 最多条数
    路 = _路()
    if not os.path.isfile(路):
        return 0
    行们 = [行 for 行 in io.open(路, encoding="utf-8").read().split(chr(10)) if 行.strip()]
    if len(行们) <= 上限:
        return 0
    丢 = len(行们) - 上限
    保 = 行们[-上限:]
    with io.open(路, "w", encoding="utf-8", newline=chr(10)) as 文件:
        文件.write(chr(10).join(保) + chr(10))
    return 丢


def 清空():
    路 = _路()
    if os.path.isfile(路):
        条数 = len([行 for 行 in io.open(路, encoding="utf-8").read().split(chr(10)) if 行.strip()])
        os.remove(路)
        return 条数
    return 0
