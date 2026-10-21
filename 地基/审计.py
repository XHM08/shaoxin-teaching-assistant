
import json
import os
import threading
import time

from 地基 import 配置

最近记录 = []
最近上限 = 200

默认上限MB = 20.0

本线程 = threading.local()


def 记当前能力(名字):
    本线程.能力 = str(名字 or "")


def 当前能力():
    return getattr(本线程, "能力", "") or "（未标明）"


def 取上限MB():
    设置 = 配置.读取().get("审计", True)
    if isinstance(设置, dict):
        try:
            return float(设置.get("上限MB", 默认上限MB))
        except (TypeError, ValueError):
            return 默认上限MB
    return 默认上限MB


def 该轮转了吗(路径):
    try:
        return os.path.getsize(路径) >= 取上限MB() * 1024 * 1024
    except OSError:
        return False


def 轮转(路径, 日志目录):
    备份目录 = os.path.join(日志目录, "_备份")
    os.makedirs(备份目录, exist_ok=True)
    基名 = "审计." + time.strftime("%Y%m%d-%H%M%S")
    目标 = os.path.join(备份目录, 基名 + ".jsonl")
    序号 = 1
    while os.path.exists(目标):
        目标 = os.path.join(备份目录, "%s-%d.jsonl" % (基名, 序号))
        序号 += 1
    os.replace(路径, 目标)
    return 目标


def 记一笔(能力, 元信息=None, 成功=True, 秒数=0.0, 备注=""):

    记录 = {
        "时间": time.strftime("%Y-%m-%d %H:%M:%S"),
        "能力": 能力,
        "成功": bool(成功),
        "秒数": round(float(秒数), 3),
        "元信息": 元信息 or {},
    }
    if 备注:
        记录["备注"] = 备注

    最近记录.append(记录)
    if len(最近记录) > 最近上限:
        del 最近记录[0]

    if not 配置.读取().get("审计", True):
        return 记录

    try:
        日志目录 = 配置.取目录("日志")
        os.makedirs(日志目录, exist_ok=True)
        路径 = os.path.join(日志目录, "审计.jsonl")
        if 该轮转了吗(路径):
            轮转(路径, 日志目录)
        with open(路径, "a", encoding="utf-8") as 文件:
            文件.write(json.dumps(记录, ensure_ascii=False) + "\n")
    except OSError as 异常:

        记录["备注"] = "审计写入失败：" + str(异常)
    return 记录


def 最近几条(条数=50):
    return 最近记录[-条数:]


def 读日志尾巴(条数=100):
    路径 = os.path.join(配置.取目录("日志"), "审计.jsonl")
    if not os.path.isfile(路径):
        return []
    行表 = []
    with open(路径, "r", encoding="utf-8") as 文件:
        for 行 in 文件:
            行 = 行.strip()
            if 行:
                行表.append(行)
    结果 = []
    for 行 in 行表[-条数:]:
        try:
            结果.append(json.loads(行))
        except json.JSONDecodeError:
            continue
    return 结果
