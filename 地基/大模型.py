
import base64
import json
import os
import re
import urllib.error
import urllib.request

from 地基 import 审计, 配置

默认超时 = 120

图片类型 = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
          ".gif": "image/gif", ".webp": "image/webp"}
单张图上限 = 8 * 1024 * 1024
一批图上限 = 24 * 1024 * 1024
图片边长上限 = 8192
缩放后边长 = 1600
一次最多几张图 = 8


def 服务商支持图(条目):
    return isinstance(条目, dict) and 条目.get("支持图片") is True


def 图片能发吗(路径):
    真身 = os.path.realpath(str(路径 or ""))
    if not os.path.isfile(真身):
        return False
    根表 = []
    for 名 in ("材料", "参考资料"):
        try:
            根表.append(os.path.realpath(配置.取目录(名)))
        except Exception:
            continue
    return any(真身.startswith(根 + os.sep) for 根 in 根表)


def 边超限(路径):
    try:
        from PIL import Image
        with Image.open(路径) as 图:
            return max(图.size) > 图片边长上限
    except Exception:
        return False


def 收拾一张图(路径):
    if not 图片能发吗(路径):
        raise ValueError("这张图不能发：不在 材料/ 或 参考资料/ 里，或者文件已不在、不是文件："
                         + os.path.basename(str(路径)))
    类型 = 图片类型.get(os.path.splitext(str(路径))[1].lower())
    if 类型 is None:
        raise ValueError("这张图的格式不能发给模型（只收 JPEG / PNG / GIF / WebP）："
                         + os.path.basename(str(路径)))
    try:
        with open(路径, "rb") as 文件:
            字节 = 文件.read()
    except OSError:
        raise ValueError("这张图读不出来（被删掉、改了名，或没有读权限）："
                         + os.path.basename(str(路径))) from None
    if len(字节) <= 单张图上限 and not 边超限(路径):
        return 字节, 类型
    try:
        from PIL import Image
    except ImportError:
        raise ValueError("这张图太大（超过 %.0f MB 或边长超过 %d px），要缩小才能发；"
                         "这台电脑上没装 Pillow，请先手工缩小：%s"
                         % (单张图上限 / 1048576, 图片边长上限,
                            os.path.basename(str(路径)))) from None
    import io
    缓冲 = io.BytesIO()
    with Image.open(路径) as 图:
        图 = 图.convert("RGB")
        比例 = min(1.0, float(缩放后边长) / max(图.size))
        if 比例 < 1.0:
            图 = 图.resize((max(1, int(图.size[0] * 比例)), max(1, int(图.size[1] * 比例))))
        图.save(缓冲, format="JPEG", quality=85)
    字节 = 缓冲.getvalue()
    if len(字节) > 单张图上限:
        raise ValueError("这张图缩完还有 %.1f MB，超过单张 %.0f MB 的上限：%s"
                         % (len(字节) / 1048576, 单张图上限 / 1048576,
                            os.path.basename(str(路径))))
    return 字节, "image/jpeg"


def 拼内容(提示词, 图=None):
    if 图 is None or 图 == []:
        return 提示词
    if isinstance(图, (str, bytes)) or not isinstance(图, (list, tuple)):
        raise ValueError("图要传一串路径（列表），不能传单个字符串。")
    图表 = list(图)
    if len(图表) > 一次最多几张图:
        raise ValueError("一次最多发 " + str(一次最多几张图)
                         + " 张图（这次 " + str(len(图表)) + " 张）")
    块表 = [{"type": "text", "text": 提示词}]
    累计 = 0
    明细 = []
    for 一张 in 图表:
        标签 = None
        if isinstance(一张, (list, tuple)) and len(一张) == 2:
            标签, 一张 = str(一张[0]), 一张[1]
        字节, 类型 = 收拾一张图(一张)
        名字 = os.path.basename(str(一张))
        明细.append("%s %.1f MB" % (名字, len(字节) / 1048576))
        累计 = 累计 + len(字节)
        if 累计 > 一批图上限:
            raise ValueError("这批图加起来超过一次能发的 %.0f MB，请少选几张或先压缩。"
                             "已计入：%s"
                             % (一批图上限 / 1048576, "、".join(明细)))
        if 标签:
            块表.append({"type": "text", "text": 标签})
        块表.append({"type": "image_url",
                   "image_url": {"url": "data:" + 类型 + ";base64,"
                                            + base64.b64encode(字节).decode("ascii")}})
    return 块表


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
    环境变量名 = str(条目.get("key_env") or "").strip()
    if not 环境变量名:
        raise RuntimeError("服务商 " + repr(名字) + " 没写 key_env")

    密钥 = os.environ.get(环境变量名)
    if 密钥 and 密钥.strip():
        return 密钥.strip()

    if not re.fullmatch(r"[A-Za-z0-9_]{1,64}", 环境变量名):
        raise RuntimeError("服务商 " + repr(名字) + " 的 key_env 不像环境变量名："
                         + repr(环境变量名) + "（只允许字母、数字、下划线，最多 64 位）")

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
       超时=默认超时, 配置文件路径=None, 图=None):
    if 假模式:
        return 假回复

    配置表 = 读配置(配置文件路径)
    名字, 条目 = 选服务商(配置表, 服务商)
    校验服务商(名字, 条目)

    if 图 and not 服务商支持图(条目):
        raise ValueError(
            "服务商「" + str(名字) + "」（模型 " + str(条目.get("model")) + "）没标「支持图片」，"
            "不能带图发。要发图请先在 服务商.json 里给这家加上 \"支持图片\": true —— "
            "只给真正能看图的模型加。")

    密钥 = 取密钥(名字, 条目)
    网址 = 条目["base_url"].rstrip("/") + "/chat/completions"
    内容 = 拼内容(提示词, 图)
    图片张数 = (sum(1 for 块 in 内容
                if isinstance(块, dict) and 块.get("type") == "image_url")
              if isinstance(内容, list) else 0)
    请求体 = {
        "model": 条目["model"],
        "temperature": 随机度,
        "messages": [{"role": "user", "content": 内容}],
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
            "图片张数": 图片张数,
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
