
import json

from 地基 import 大模型, 提示词, 记忆库, 脱敏

默认最多抽取 = 3


def 设置():
    值 = 配置读取().get("记忆", True)
    return 值 if isinstance(值, dict) else {"开启": bool(值)}


def 配置读取():
    from 地基 import 配置
    return 配置.读取()


def 开启了吗():
    return bool(设置().get("开启", True))


def 抽取开着吗():
    if not 开启了吗():
        return False
    return bool(设置().get("抽取", True))


def 压缩开着吗():
    if not 开启了吗():
        return False
    return bool(设置().get("压缩", True))


def 解析记忆(文本, 最多=None):
    上限 = 默认最多抽取 if 最多 is None else int(最多)
    结果 = []
    for 行 in str(文本 or "").splitlines():
        行 = 行.strip()
        if not 行.startswith("{"):
            continue
        try:
            记录 = json.loads(行)
        except json.JSONDecodeError:
            continue
        if not isinstance(记录, dict):
            continue
        内容 = str(记录.get("内容", "")).strip()
        if not 内容:
            continue
        类别 = str(记录.get("类别", "关键")).strip() or "关键"
        结果.append({"类别": 类别, "内容": 内容[:60]})
        if len(结果) >= 上限:
            break
    return 结果


def 抽取(老师说的, 回答, 来源="创造模式", 最多=None):
    结果 = {"记了": [], "说明": ""}
    if not 抽取开着吗():
        结果["说明"] = "记忆抽取已关闭"
        return 结果
    try:
        老师说, _ = 脱敏.脱敏(str(老师说的)[:1200])
        助手说, _ = 脱敏.脱敏(str(回答)[:2000])
        提示 = 提示词.填充(提示词.读取("抽取记忆"),
                        老师这次说的=老师说,
                        助手的回答=助手说)
        原文 = 大模型.问(提示, 随机度=0.0)
    except Exception as 异常:
        结果["说明"] = type(异常).__name__ + "：" + str(异常)[:60]
        return 结果

    已有 = {记录["内容"] for 记录 in 记忆库.取记忆(50)}
    for 一条 in 解析记忆(原文, 最多):
        if 一条["内容"] in 已有:
            continue
        记录 = 记忆库.记一条(一条["内容"], 一条["类别"], 来源)
        if 记录:
            结果["记了"].append(记录)
            已有.add(一条["内容"])
    return 结果


def 压缩(历史, 会话="默认", 压到=8000):
    if not 压缩开着吗():
        return 历史, False, "记忆压缩已关闭"
    文本 = str(历史 or "")
    if len(文本) <= 压到:
        return 历史, False, ""
    try:
        要压 = 文本[:-压到][:6000]
        要压, _ = 脱敏.脱敏(要压)
        提示 = 提示词.填充(提示词.读取("压缩对话"), 对话=要压)
        摘要 = str(大模型.问(提示, 随机度=0.0)).strip()
    except Exception as 异常:
        return 历史, False, type(异常).__name__ + "：" + str(异常)[:60]
    if len(摘要) < 10:
        return 历史, False, "压缩返回的内容太短，没用"
    记忆库.存摘要(会话, len(文本) - 压到, 摘要)
    尾巴 = 文本[-压到:]
    切点 = 尾巴.find("\n")
    if 切点 >= 0:
        尾巴 = 尾巴[切点 + 1:]
    新 = "（更早的对话已压缩成摘要，原文不再随请求发送）\n【这一段的小结】" + 摘要 + "\n" + 尾巴
    return 新, True, ""


慢压阈值 = 6


def 慢压(会话="默认", 阈值=None):
    结果 = {"合并": 0, "说明": ""}
    阈值 = 慢压阈值 if 阈值 is None else int(阈值)
    if not 压缩开着吗():
        结果["说明"] = "记忆压缩已关闭"
        return 结果
    记录们 = 记忆库.取摘要(会话, 99)
    if len(记录们) < 阈值:
        return 结果
    旧文 = chr(10).join("- " + 记录["摘要"] for 记录 in reversed(记录们))
    try:
        旧文, _ = 脱敏.脱敏(旧文[:4000])
        提示 = 提示词.填充(提示词.读取("合并摘要"), 摘要们=旧文)
        合并 = str(大模型.问(提示, 随机度=0.0)).strip()
    except Exception as 异常:
        结果["说明"] = type(异常).__name__ + "：" + str(异常)[:60]
        return 结果
    if len(合并) < 10:
        结果["说明"] = "合并结果太短，没用"
        return 结果
    覆盖 = sum(int(记录.get("覆盖到") or 0) for 记录 in 记录们)
    删了 = 记忆库.清摘要(会话)
    记忆库.存摘要(会话, 覆盖, 合并)
    结果["合并"] = 删了
    return 结果


def 注入文本(会话="默认"):
    记忆, _ = 脱敏.脱敏(记忆库.记忆文本(12))

    摘要, _ = 脱敏.脱敏(记忆库.摘要文本(会话, 2))
    if not 记忆 and not 摘要:
        return ""
    行 = []
    if 记忆:
        行.append("【长期记忆】")
        行.append(记忆)
    if 摘要:
        行.append("【更早对话的小结】")
        行.append(摘要)
    return "\n".join(行)
