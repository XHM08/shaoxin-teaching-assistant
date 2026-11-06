
import json
import os
import threading
import time

from 地基 import 配置

教师数据锁 = threading.RLock()


def 数据目录():
    return 配置.取目录("教师数据")


def 现在():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def 读JSONL(路径, 名字):
    if not os.path.isfile(路径):
        return []
    条目们 = []
    with open(路径, "r", encoding="utf-8") as 文件:
        for 行号, 行 in enumerate(文件, 1):
            行 = 行.strip()
            if not 行:
                continue
            try:
                一条 = json.loads(行)
            except json.JSONDecodeError as 异常:
                raise ValueError(
                    名字 + " 第 " + str(行号) + " 行读不出来（多半是上次写盘被打断）：\n"
                    + 路径 + "\n软件不会覆盖它：请先人工核对这一行。"
                ) from 异常
            if not isinstance(一条, dict):
                raise ValueError(名字 + " 第 " + str(行号) + " 行不是一条记录：\n" + 路径)
            条目们.append(一条)
    return 条目们


def 追加一行(路径, 一条):
    目录 = os.path.dirname(os.path.abspath(路径))
    os.makedirs(目录, exist_ok=True)
    行 = json.dumps(一条, ensure_ascii=False) + "\n"
    with open(路径, "a", encoding="utf-8") as 文件:
        文件.write(行)
        文件.flush()
        os.fsync(文件.fileno())
