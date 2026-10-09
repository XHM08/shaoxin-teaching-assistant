
import atexit
import json
import os
import re

from 地基 import MCP

已登记工具 = {}
最多步数 = 5

工具说明模板 = """
=====================
你可以调用下面这些本地工具来获取需要的信息：

{工具清单}

需要工具时，**只输出一行 JSON**（键名就用 工具 / 参数），格式如下：
{"工具": "工具名", "参数": {"参数名": "值"}}

拿到工具结果后，再给出最终回答；不需要工具就直接回答。
=====================
"""

工具名格式 = re.compile(r'"(?:工具|tool)"\s*:\s*"([^"]{1,60})"', re.I)
参数起头格式 = re.compile(r'"(?:参数|args)"\s*:\s*\{', re.I)


def 登记工具(工具名, 说明, 参数, 处理函数):
    if 工具名 in 已登记工具:
        raise ValueError("工具名重复：" + 工具名)
    if not callable(处理函数):
        raise ValueError("工具 " + 工具名 + " 的处理函数不是函数")
    for 参数项 in 参数:
        if "代号" not in 参数项 or "标签" not in 参数项:
            raise ValueError("工具 " + 工具名 + " 的参数必须有「代号」和「标签」：" + str(参数项))
    已登记工具[工具名] = {"说明": 说明, "参数": 参数, "处理函数": 处理函数}


def 全部名字():
    return sorted(已登记工具)


def 工具清单文字():
    if not 已登记工具:
        return "（当前没有登记任何工具）"
    行表 = []
    for 工具名 in sorted(已登记工具):
        工具 = 已登记工具[工具名]
        参数字段 = "、".join(参数项["代号"] for 参数项 in 工具["参数"]) or "无参数"
        行表.append("- " + 工具名 + "（" + 参数字段 + "）：" + 工具["说明"])
    return "\n".join(行表)


def _补齐参数(工具名, 实参):
    参数表 = 已登记工具[工具名]["参数"]
    认识的 = {一项["代号"] for 一项 in 参数表}
    if not 实参 or set(实参) <= 认识的:
        return dict(实参 or {})
    结果 = {}
    for 键, 值 in 实参.items():
        if 键 in 认识的:
            结果[键] = 值
    没占的 = [一项["代号"] for 一项 in 参数表 if 一项["代号"] not in 结果]
    序号 = 0
    for 键, 值 in 实参.items():
        if 键 in 认识的:
            continue
        if 序号 < len(没占的):
            结果[没占的[序号]] = 值
            序号 += 1
    return 结果


def 调用(工具名, 实参=None):
    if 工具名 not in 已登记工具:
        return {"成功": False, "错误": "没有登记这个工具：" + 工具名}
    try:
        真参数 = _补齐参数(工具名, 实参)
        return {"成功": True, "结果": 已登记工具[工具名]["处理函数"](**真参数)}
    except Exception as 异常:
        return {"成功": False, "错误": type(异常).__name__ + ": " + str(异常)}


def _取配对对象(文本, 起点):
    深度 = 0
    for 位置 in range(起点, len(文本)):
        字符 = 文本[位置]
        if 字符 == "{":
            深度 += 1
        elif 字符 == "}":
            深度 -= 1
            if 深度 == 0:
                return 文本[起点:位置 + 1]
    return ""


def 找出调用(文本):
    文本 = 文本 or ""
    找到的 = []
    for 名字命中 in 工具名格式.finditer(文本):
        参数命中 = 参数起头格式.search(文本, 名字命中.end())
        if not 参数命中:
            参数命中 = 参数起头格式.search(文本)
        if not 参数命中:
            continue
        片段 = _取配对对象(文本, 参数命中.end() - 1)
        if not 片段:
            continue
        try:
            实参 = json.loads(片段)
        except json.JSONDecodeError:
            continue
        if not isinstance(实参, dict):
            continue
        找到的.append({"工具": 名字命中.group(1), "参数": 实参})
    return 找到的


def 工具说明文字(清单文字=None):
    return 工具说明模板.replace("{工具清单}", 清单文字 or 工具清单文字())


每轮调用上限 = 4


def 带工具跑(提示词, 问模型, 步数上限=最多步数, 调用记录=None):
    if 工具说明文字() not in 提示词:
        提示词 = 提示词 + "\n\n" + 工具说明文字()
    对话 = 提示词

    for 第几步 in range(步数上限):
        回答 = 问模型(对话)
        本轮调用 = 找出调用(回答)
        if not 本轮调用:
            if 调用记录 is not None and 回答.count("{") and (
                    "工具" in 回答 or '"tool"' in 回答.lower()):
                调用记录.append({"第几步": 第几步 + 1, "工具": "（没能解析出调用）", "成功": False})
            return 回答

        if len(本轮调用) > 每轮调用上限:
            for 多余 in 本轮调用[每轮调用上限:]:
                if 调用记录 is not None:
                    调用记录.append({"第几步": 第几步 + 1, "工具": 多余["工具"],
                                "成功": False, "说明": "一轮里超过 %d 个，没执行" % 每轮调用上限})
            本轮调用 = 本轮调用[:每轮调用上限]
        for 一条 in 本轮调用:
            结果 = 调用(一条["工具"], 一条["参数"])
            if 调用记录 is not None:
                调用记录.append({"第几步": 第几步 + 1, "工具": 一条["工具"], "成功": 结果["成功"]})
            对话 += ("\n\n" + 回答 + "\n\n[工具 " + 一条["工具"] + " 的结果]\n"
                     + json.dumps(结果, ensure_ascii=False))

    对话 += "\n\n不要再调用工具了，请直接给出最终回答。"
    return 问模型(对话)



_MCP服务器们 = []
_接过MCP吗 = False


def 转参数表(格式):
    格式 = 格式 if isinstance(格式, dict) else {}
    属性 = 格式.get("properties")
    属性 = 属性 if isinstance(属性, dict) else {}
    必填 = set(格式.get("required") or [])
    表 = []
    for 代号, 定义 in 属性.items():
        定义 = 定义 if isinstance(定义, dict) else {}
        标签 = str(定义.get("description") or 定义.get("title") or 代号)
        可选 = 定义.get("enum")
        if isinstance(可选, list) and 可选:
            标签 += "（可选：" + " / ".join(str(一个) for 一个 in 可选) + "）"
        if 代号 in 必填:
            标签 += "（必填）"
        表.append({"代号": str(代号), "标签": 标签})
    return 表


def _做外部工具处理函数(服, 原名, 显示名):
    def 处理(**实参):
        from 地基 import 审计
        try:
            文本, 服务器说出错 = 服.调工具(原名, 实参)
        except MCP.出错 as 异常:
            审计.记一笔("外部工具", {"服务器": 服.名字, "工具": 原名,
                                   "错误": str(异常)[:200]}, 成功=False)
            return {"成功": False, "结果": "外部工具「%s」没成功：%s" % (显示名, 异常)}
        审计.记一笔("外部工具", {"服务器": 服.名字, "工具": 原名,
                               "参数名": sorted(实参)}, 成功=not 服务器说出错)
        if 服务器说出错:
            return {"成功": False, "结果": "外部工具「%s」没成功：%s" % (显示名, 文本)}
        return {"成功": True, "结果": 文本}
    return 处理


def 接上MCP(记录=None, 配置路径=None):
    global _接过MCP吗
    if _接过MCP吗:
        return list(_MCP服务器们)

    说 = 记录 or (lambda _忽略: None)
    根目录 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        配置表 = MCP.读配置(配置路径 or os.path.join(根目录, "MCP服务器.json"))
    except MCP.出错 as 异常:
        说("MCP 配置读不了，这次不挂外部工具：" + str(异常))
        return []

    _接过MCP吗 = True

    if not 配置表.get("启用"):
        return []

    for 服 in MCP.起全部(配置表, 记录=说):
        try:
            工具们 = 服.列工具()
        except MCP.出错 as 异常:
            说("MCP 服务器「%s」列不出工具，跳过：%s" % (服.名字, 异常))
            try:
                服.关闭()
            except Exception:
                pass
            continue
        for 工具 in 工具们:
            名字 = 服.名字 + "·" + 工具["名字"]
            if len(名字) > 60:
                名字 = 名字[:57] + "…"
            if 名字 in 已登记工具:
                说("工具名撞车，跳过：" + 名字)
                continue
            登记工具(名字, 工具["说明"] or ("来自 MCP 服务器「%s」" % 服.名字),
                  转参数表(工具["参数格式"]),
                  _做外部工具处理函数(服, 工具["名字"], 名字))
            说("挂上外部工具：" + 名字)
        _MCP服务器们.append(服)
    if _MCP服务器们:
        atexit.register(关MCP)
    return list(_MCP服务器们)


def 关MCP():
    while _MCP服务器们:
        服 = _MCP服务器们.pop()
        try:
            服.关闭()
        except Exception:
            pass
