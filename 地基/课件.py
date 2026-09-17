
import json
import re


def 取出JSON(原文):
    起点 = 原文.find("{")
    终点 = 原文.rfind("}")
    if 起点 < 0 or 终点 <= 起点:
        raise ValueError("模型没有返回课件 JSON。原始内容前 300 字：" + str(原文 or "")[:300])
    片段 = 原文[起点:终点 + 1]
    try:
        数据 = json.loads(片段)
    except json.JSONDecodeError as 异常:
        raise ValueError("课件 JSON 解析失败：" + str(异常) + "。原始内容前 300 字：" + 片段[:300])
    if not isinstance(数据, dict) or not isinstance(数据.get("pages"), list) or not 数据["pages"]:
        raise ValueError('课件 JSON 结构不对，需要 {"title": ..., "pages": [...]}')
    return 数据


def 安全文件名(原文):
    结果 = re.sub(r'[\\/:*?"<>|\s]+', "-", str(原文 or "").strip())
    return 结果.strip("-") or "课件"


def 页面清单(数据):
    return [页 for 页 in 数据.get("pages", []) if isinstance(页, dict)]


def 取要点(一页):
    要点 = (一页 or {}).get("points")
    if isinstance(要点, str):
        return [每一行.strip() for 每一行 in 要点.splitlines() if 每一行.strip()]
    if isinstance(要点, (list, tuple)):
        return [str(一条).strip() for 一条 in 要点 if str(一条).strip()]
    return []


能识别的类型 = ("封面", "知识", "例题", "练习", "小结")
例题味 = ("试一试", "试一", "算一算", "例题", "推导")
练习味 = ("练",)


def 归一类型(数据):
    页面们 = 页面清单(数据)
    总数 = len(页面们)
    for 序号, 页 in enumerate(页面们):
        if str(页.get("kind") or "").strip() in 能识别的类型:
            continue
        标题 = str(页.get("title") or "")
        if 序号 == 0:
            页["kind"] = "封面"
        elif 序号 == 总数 - 1:
            页["kind"] = "小结"
        elif any(词 in 标题 for 词 in 练习味):
            页["kind"] = "练习"
        elif any(词 in 标题 for 词 in 例题味):
            页["kind"] = "例题"
        else:
            页["kind"] = "知识"
    return 数据


def 转文字(数据):
    归一类型(数据)
    行表 = [str(数据.get("title", "课件"))]
    for 序号, 页 in enumerate(页面清单(数据), 1):
        类型 = str(页.get("kind") or "").strip()
        行表.append("")
        行表.append("第 " + str(序号) + " 页"
                  + ("（" + 类型 + "）" if 类型 else "")
                  + "｜" + str(页.get("title", "")))
        if 页.get("关键句"):
            行表.append("★ " + str(页["关键句"]))
        for 要点 in 取要点(页):
            行表.append("- " + 要点)
        if 页.get("script"):
            行表.append("讲稿：" + str(页["script"]))
    return "\n".join(行表)
