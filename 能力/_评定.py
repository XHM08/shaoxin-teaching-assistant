
import os

from 能力 import _教师数据

数据目录 = _教师数据.数据目录
现在 = _教师数据.现在
读JSONL = _教师数据.读JSONL
追加一行 = _教师数据.追加一行
评定锁 = _教师数据.教师数据锁

判定取值 = ("可接受", "需修改", "不可用")


def 待评路径():
    return os.path.join(数据目录(), "待评.jsonl")


def 评定路径():
    return os.path.join(数据目录(), "评定.jsonl")


def 校订路径():
    return os.path.join(数据目录(), "校订.jsonl")


def 已有条目号():
    号们 = []
    for 一 in 读JSONL(待评路径(), "待评.jsonl"):
        号 = 一.get("条目号")
        if isinstance(号, int):
            号们.append(号)
    return 号们


def 记待评(题目, 技能包, 讲解):
    with 评定锁:
        号们 = 已有条目号()
        号 = (max(号们) + 1) if 号们 else 1
        追加一行(待评路径(), {
            "条目号": 号,
            "题目": 题目,
            "技能包": 技能包,
            "讲解A": 讲解,
            "时间": 现在(),
        })
    return 号


def 记评定(条目号, 判定, 老师改的="", 老师原话=""):
    if 判定 not in 判定取值:
        raise ValueError("判定只能是：" + " / ".join(判定取值) + "。拿到的是：" + str(判定))
    with 评定锁:
        追加一行(评定路径(), {
            "条目号": 条目号,
            "判定": 判定,
            "讲解B": str(老师改的 or "").strip(),
            "老师原话": str(老师原话 or "").strip(),
            "时间": 现在(),
        })


def 记校订(技能包代号, 节标题, 老师原话):
    with 评定锁:
        追加一行(校订路径(), {
            "技能包": 技能包代号,
            "节": 节标题,
            "老师原话": str(老师原话 or "").strip(),
            "时间": 现在(),
        })


def 台账():
    评定表 = {}
    for 一 in 读JSONL(评定路径(), "评定.jsonl"):
        号 = 一.get("条目号")
        if isinstance(号, int):
            评定表[号] = 一
    结果 = []
    for 一 in 读JSONL(待评路径(), "待评.jsonl"):
        号 = 一.get("条目号")
        判 = 评定表.get(号) if isinstance(号, int) else None
        结果.append({
            "条目号": 号,
            "状态": "已评" if 判 else "待评",
            "判定": (判 or {}).get("判定", ""),
            "题目": 一.get("题目", ""),
            "技能包": 一.get("技能包", ""),
            "讲解A": 一.get("讲解A", ""),
            "讲解B": (判 or {}).get("讲解B", ""),
            "老师原话": (判 or {}).get("老师原话", ""),
            "时间": 一.get("时间", ""),
        })
    return 结果
