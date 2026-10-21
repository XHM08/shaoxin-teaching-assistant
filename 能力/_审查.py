
import re

from 地基 import 大模型, 配置, 提示词, 脱敏

级别表 = ("高", "中", "低")
默认级别 = "中"
最多问题 = 5
最短要审 = 400


_怪老师 = re.compile(r"老师[^，。；]{0,10}(要求|提问|问法|说法|诉求)[^，。；]{0,10}(不清楚|不明确|太笼统|含糊|太啰嗦|过于|不合理|应该|需要重新)")
_像邵新的锅 = ("助手", "回答", "漏", "只做", "没做", "未做", "少做", "缺", "没有做")
_条 = re.compile(r"^\s*\d+\s*[.、)]\s*(?:[\[【(（]\s*([高中低])\s*[\]】)）])?\s*(.+)$")


def 开启了吗():
    值 = 配置.读取().get("审查", True)
    if isinstance(值, dict):
        return bool(值.get("开启", True))
    return bool(值)


def 要审吗(回答, 调用记录):
    if not 开启了吗():
        return False
    return bool(调用记录) or len(str(回答)) >= 最短要审


def 解析(文本):
    原文 = str(文本 or "").strip()
    if not 原文:
        return "没跑成", [], "审查没有返回内容"

    位置 = 原文.upper().find("REJECT")
    if 位置 >= 0:
        问题们 = []
        for 行 in 原文[位置 + len("REJECT"):].splitlines():
            匹配 = _条.match(行)
            if not 匹配:
                continue
            级别 = 匹配.group(1) or 默认级别
            内容 = 匹配.group(2).strip()
            if not 内容:
                continue
            说明, _, 在哪 = 内容.partition("｜")
            问题们.append({"级别": 级别, "说明": 说明.strip(), "位置": 在哪.strip()})
            if len(问题们) >= 最多问题:
                break
        if not 问题们:
            return "没跑成", [], "说了 REJECT 但没给出可读的条目"
        return "有问题", 问题们, ""

    if "APPROVE" in 原文.upper():
        if 位置 >= 0:
            return "没跑成", [], "同时出现 APPROVE 与 REJECT，读不懂"
        return "通过", [], ""
    return "没跑成", [], "既没有 APPROVE 也没有 REJECT"


def 记录文本(调用记录):
    行 = ["- %s：%s" % (一条.get("工具", "?"), str(一条.get("结果", ""))[:120])
         for 一条 in (调用记录 or [])]
    return "\n".join(行) or "（这一轮没有调用工具）"


def 审查(回答, 老师说的, 调用记录=()):
    结果 = {"判": "跳过", "问题们": [], "说明": ""}
    if not 要审吗(回答, 调用记录):
        return 结果
    try:

        老师的话, 换1 = 脱敏.脱敏(str(老师说的)[:1500])
        助手的话, 换2 = 脱敏.脱敏(str(回答)[:4000])
        记录, 换3 = 脱敏.脱敏(记录文本(调用记录))
        提示 = 提示词.填充(提示词.读取("审查"),
                        老师这次说的=老师的话,
                        助手的回答=助手的话,
                        调用记录=记录)
        if 换1 + 换2 + 换3:
            结果["说明"] = "送审前换掉 %d 处姓名" % (换1 + 换2 + 换3)
        原文 = 大模型.问(提示, 随机度=0.0)
    except Exception as 异常:
        结果["判"] = "没跑成"
        结果["说明"] = type(异常).__name__ + "：" + str(异常)[:80]
        return 结果
    结论, 问题们, 错 = 解析(原文)
    留, 丢掉 = 过滤怪老师(问题们)
    结果["判"] = "有问题" if 留 else 结论
    结果["问题们"] = 留
    结果["说明"] = 错 or ("丢掉 %d 条针对老师的意见" % len(丢掉) if 丢掉 else "")
    return 结果


def 过滤怪老师(问题们):
    留, 丢掉 = [], []
    for 一条 in 问题们 or []:
        文本 = (一条.get("说明", "") + "｜" + 一条.get("位置", ""))
        if _怪老师.search(文本) and not any(词 in 文本 for 词 in _像邵新的锅):
            丢掉.append(一条)
            continue
        留.append(一条)
    return 留, 丢掉


def 附到回答(回答, 审查结果):
    问题们 = 审查结果.get("问题们") or []
    if not 问题们:
        return 回答
    顺序 = {级别: 号 for 号, 级别 in enumerate(级别表)}
    排好 = sorted(问题们, key=lambda 一条: 顺序.get(一条.get("级别"), 9))
    行 = ["", "", "〔审查者〕这一轮挑出 %d 处，仅供参考，改不改由你定：" % len(排好)]
    for 号, 一条 in enumerate(排好, 1):
        位置 = ("（" + 一条["位置"] + "）") if 一条.get("位置") else ""
        行.append("%d. [%s] %s%s" % (号, 一条.get("级别", 默认级别), 一条["说明"], 位置))
    return str(回答).rstrip() + "\n".join(行)
