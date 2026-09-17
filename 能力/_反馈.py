
import os
import time

from 能力 import _教师数据

反馈类型 = ("不好用", "算错了", "太慢了", "想要新功能")

处理结果 = ("已修", "不做", "重复", "先记着")



def 反馈路径():
    return os.path.join(_教师数据.数据目录(), "反馈.jsonl")


def 处理路径():
    return os.path.join(_教师数据.数据目录(), "反馈处理.jsonl")


def 已有反馈号():
    号们 = []
    for 一 in _教师数据.读JSONL(反馈路径(), "反馈.jsonl"):
        号 = 一.get("反馈编号")
        if isinstance(号, int):
            号们.append(号)
    return 号们


def 记反馈(类型, 内容, 影响面=""):
    if 类型 not in 反馈类型:
        raise ValueError("反馈类型只能是：" + " / ".join(反馈类型)
                         + "。拿到的是：" + str(类型))
    正文 = str(内容 or "").strip()
    if not 正文:
        raise ValueError("反馈内容不能为空。")
    with _教师数据.教师数据锁:
        号们 = 已有反馈号()
        号 = (max(号们) + 1) if 号们 else 1
        _教师数据.追加一行(反馈路径(), {
            "反馈编号": 号,
            "类型": 类型,
            "内容": 正文,
            "影响面": str(影响面 or "").strip(),
            "时间": _教师数据.现在(),
        })
    return 号


def 记处理(反馈编号, 结果, 提交号="", 说明=""):
    if 结果 not in 处理结果:
        raise ValueError("处理结果只能是：" + " / ".join(处理结果)
                         + "。拿到的是：" + str(结果))
    原文 = str(反馈编号).strip()
    if not 原文.isdigit():
        raise ValueError("反馈编号要写数字（就是清单里那个号）。拿到的是："
                         + (原文 or "（空）"))
    号 = int(原文)
    已有 = 已有反馈号()
    if 号 not in 已有:
        raise ValueError("没有编号 " + str(号) + " 这条反馈。现在有："
                         + ("、".join(str(一) for 一 in sorted(已有)) or "（一条都没有）"))
    with _教师数据.教师数据锁:
        _教师数据.追加一行(处理路径(), {
            "反馈编号": 号,
            "结果": 结果,
            "提交号": str(提交号 or "").strip(),
            "说明": str(说明 or "").strip(),
            "时间": _教师数据.现在(),
        })


def 取一条(反馈编号):
    for 一 in _教师数据.读JSONL(反馈路径(), "反馈.jsonl"):
        if 一.get("反馈编号") == 反馈编号:
            return 一
    return None


def 小时差(早, 晚):
    try:
        甲 = time.strptime(str(早), "%Y-%m-%d %H:%M:%S")
        乙 = time.strptime(str(晚), "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None
    return round((time.mktime(乙) - time.mktime(甲)) / 3600.0, 1)


def 清单():
    处理表 = {}
    for 一 in _教师数据.读JSONL(处理路径(), "反馈处理.jsonl"):
        号 = 一.get("反馈编号")
        if isinstance(号, int):
            处理表[号] = 一
    结果 = []
    for 一 in _教师数据.读JSONL(反馈路径(), "反馈.jsonl"):
        号 = 一.get("反馈编号")
        处 = 处理表.get(号) if isinstance(号, int) else None
        结果.append({
            "反馈编号": 号,
            "状态": "已处理" if 处 else "未处理",
            "类型": 一.get("类型", ""),
            "内容": 一.get("内容", ""),
            "影响面": 一.get("影响面", ""),
            "结果": (处 or {}).get("结果", ""),
            "提交号": (处 or {}).get("提交号", ""),
            "处理说明": (处 or {}).get("说明", ""),
            "时间": 一.get("时间", ""),
            "处理时间": (处 or {}).get("时间", ""),
            "处理用时小时": 小时差(一.get("时间", ""), (处 or {}).get("时间", ""))
                            if 处 else None,
        })
    return 结果
