
import json
import os
import urllib.error
import urllib.request

from 地基 import 审计, 配置

默认超时 = 120


def 取整数(值):
    if isinstance(值, bool):
        return None
    if isinstance(值, (int, float)):
        return 值
    if isinstance(值, str) and 值.strip().lstrip("-").isdigit():
        return int(值.strip())
    return None


def 取子表(表, 键):
    值 = 表.get(键) if isinstance(表, dict) else None
    return 值 if isinstance(值, dict) else {}

假回复 = """---
name: demo-teacher
description: 演示用技能包，由假模式产生，用于验证流水线，不是真实教师。
---

## 核心自述
（演示）这里本来会是一位教师的自述。

## 高频错因
（演示）这里本来会是错因清单。

## 课堂教学风格
（演示）这里本来会是课堂风格描述。
"""


def 读配置(配置文件路径=None):
    路径 = 配置文件路径 or 配置.服务商配置路径()
    if not os.path.exists(路径):
        示例 = os.path.join(配置.根目录, "服务商.示例.json")
        if not os.path.exists(示例):
            raise RuntimeError(
                "没找到服务商配置：" + 路径
                + "\n把 服务商.示例.json 复制成 服务商.json，再按里面说明填。"
            )
        路径 = 示例
    with open(路径, "r", encoding="utf-8") as 文件:
        return json.load(文件)


def 选服务商(配置表, 指定=None):
    名字 = 指定 or 配置表.get("default")
    if not 名字:
        raise RuntimeError("配置里没有 default，调用时也没指定服务商")

    服务商表 = 配置表.get("providers", {})
    if 名字 not in 服务商表:
        raise RuntimeError(
            "配置里没有服务商 " + repr(名字)
            + "。现有的有：" + ", ".join(sorted(服务商表))
        )
    return 名字, 服务商表[名字]


必填字段 = ["base_url", "model", "key_env"]


def 校验服务商(名字, 条目):
    缺的 = [字段 for 字段 in 必填字段 if not str(条目.get(字段, "")).strip()]
    if 缺的:
        raise RuntimeError(
            "服务商 " + repr(名字) + " 的配置不完整，还缺：" + "、".join(缺的)
            + "。中转站 / 自建服务就是在这里填它给你的 base_url 和 key 环境变量名。"
        )


def 查环境变量名(环境变量名):
    if 环境变量名 in ("", ".", "..") or any(字符 in 环境变量名 for 字符 in ("/", "\\", ":")):
        raise ValueError("密钥环境变量名不合法：" + repr(环境变量名))


def 读密钥文件(环境变量名):
    if not 环境变量名 or any(字符 in 环境变量名 for 字符 in ("/", "\\", ":")):
        return ""
    路径 = os.path.join(配置.取目录("密钥"), 环境变量名 + ".txt")
    if not os.path.isfile(路径):
        return ""
    with open(路径, "r", encoding="utf-8") as 文件:
        for 行 in 文件:
            行 = 行.strip()
            if 行 and not 行.startswith("#"):
                return 行
    return ""


def 取密钥(名字, 条目):
    环境变量名 = 条目.get("key_env")
    if not 环境变量名:
        raise RuntimeError("服务商 " + repr(名字) + " 没写 key_env")

    密钥 = os.environ.get(环境变量名)
    if 密钥 and 密钥.strip():
        return 密钥.strip()

    密钥 = 读密钥文件(环境变量名)
    if 密钥:
        return 密钥

    raise RuntimeError(
        "没找到 " + 环境变量名 + " 的 Key。两种放法任选一种：\n"
        "  ① 设环境变量 " + 环境变量名 + "\n"
        "  ② 存成文件 密钥/" + 环境变量名 + ".txt（第一行就是 Key）\n"
        "也可以先用假模式把流程跑通。"
    )


def 问(提示词, 服务商=None, 随机度=0.3, 假模式=False,
       超时=默认超时, 配置文件路径=None):
    if 假模式:
        return 假回复

    配置表 = 读配置(配置文件路径)
    名字, 条目 = 选服务商(配置表, 服务商)
    校验服务商(名字, 条目)
    密钥 = 取密钥(名字, 条目)

    网址 = 条目["base_url"].rstrip("/") + "/chat/completions"
    请求体 = {
        "model": 条目["model"],
        "temperature": 随机度,
        "messages": [{"role": "user", "content": 提示词}],
    }
    请求 = urllib.request.Request(
        网址,
        data=json.dumps(请求体).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + 密钥,
        },
    )

    try:
        with urllib.request.urlopen(请求, timeout=超时) as 响应:
            数据 = json.loads(响应.read().decode("utf-8"))
    except urllib.error.HTTPError as 异常:
        详情 = 异常.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(
            "服务商 " + 名字 + " 返回 " + str(异常.code) + "：" + 详情
        ) from 异常
    except urllib.error.URLError as 异常:
        raise RuntimeError(
            "连不上 " + 名字 + "（网络或代理问题）：" + str(异常.reason)
        ) from 异常

    try:
        用量 = 取子表(数据, "usage")
        输入 = 取整数(用量.get("prompt_tokens"))
        命中 = 取整数(用量.get("prompt_cache_hit_tokens"))
        if 命中 is None:
            命中 = 取整数(取子表(用量, "prompt_tokens_details").get("cached_tokens"))
        未命中 = 取整数(用量.get("prompt_cache_miss_tokens"))
        if 未命中 is None and 命中 is not None and 输入 is not None:
            未命中 = max(0, 输入 - 命中)
        审计.记一笔("模型调用", {
            "服务商": 名字,
            "来源": 审计.当前能力(),
            "输入token": 输入,
            "输出token": 取整数(用量.get("completion_tokens")),
            "推理token": 取整数(取子表(用量, "completion_tokens_details").get("reasoning_tokens")),
            "缓存命中token": 命中,
            "缓存未命中token": 未命中,
        }, 成功=True)
    except Exception:
        pass

    try:
        return 数据["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as 异常:
        raise RuntimeError(
            "返回的结构看不懂，原始内容：" + json.dumps(数据, ensure_ascii=False)[:500]
        ) from 异常
