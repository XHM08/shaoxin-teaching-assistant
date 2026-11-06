
import json
import uuid
import os
import socket
import urllib.error
import urllib.request
from urllib.parse import urlencode

默认地址 = "http://127.0.0.1:9880"
默认超时 = 300
最长文本 = 2000
能用的参考音后缀 = (".wav",)


def 取地址():
    try:
        from 地基 import 配置
        值 = (配置.读取().get("语音") or {}).get("地址")
        if 值 and str(值).strip():
            return str(值).strip()
    except Exception:
        pass
    return 默认地址


def 服务在吗(地址=None, 超时=1.5):
    地址 = 地址 or 取地址()
    主机端口 = 地址.split("//")[-1].split("/")[0]
    主机, _, 端口 = 主机端口.partition(":")
    主机 = 主机 or "127.0.0.1"
    try:
        连接 = socket.create_connection((主机, int(端口 or 80)), 超时)
    except Exception:
        return False
    try:
        连接.settimeout(超时)
        连接.sendall(b"GET / HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
        return bool(连接.recv(1))
    except Exception:
        return False
    finally:
        连接.close()


def 没启动怎么说(地址=None):
    地址 = 地址 or 取地址()
    return ("语音服务没在跑（" + 地址 + "）。先启动它再试：\n"
          "  1. 双击 语音/启动语音服务.bat（或cd到 GPT-SoVITS 目录跑 .venv\\Scripts\\python.exe api_v2.py）\n"
          "  2. 等它打印出监听端口，再回来点「讲稿配音」\n"
          "它和邵新是两个进程，互不影响，不配音时不用开它。")


def 程序目录文件():
    from 地基 import 配置
    return os.path.join(配置.根目录, "语音", "程序目录.txt")


def 读程序目录():
    路径 = 程序目录文件()
    if not os.path.isfile(路径):
        raise ValueError(
            "找不到 " + 路径 + "\n"
            "  这个文件里只写一行：GPT-SoVITS 那个文件夹的完整路径。\n"
            "  见 语音/说明.md 的「搬家」一节。")
    with open(路径, "r", encoding="utf-8") as 文件:
        for 行 in 文件:
            行 = 行.strip()
            if 行 and not 行.startswith("#"):
                return 行
    raise ValueError("语音/程序目录.txt 是空的：第一行要写 GPT-SoVITS 文件夹的完整路径")


def 读端口():
    地址 = 取地址()
    尾巴 = 地址.split("//")[-1].split("/")[0]
    端口 = 尾巴.partition(":")[2]
    try:
        return int(端口)
    except ValueError:
        return 9880


def 取参考音():
    目录 = None
    try:
        from 地基 import 配置
        目录 = 配置.取目录("参考音")
    except Exception:
        目录 = ""
    if not 目录 or not os.path.isdir(目录):
        raise ValueError(
            "还没有参考音。请把本人同意使用的一段 3–10 秒录音放成\n"
            "  " + os.path.join(目录 or "语音/参考音", "参考音.wav") + "\n"
            "再在同目录放一个同名的 参考音.txt，第一行写上那段录音说的是什么字。\n"
            "（合规：只能用本人同意过的本人声音；学生与他人的声音一律不许放进来）")

    音频们 = [名 for 名 in sorted(os.listdir(目录))
             if os.path.splitext(名)[1].lower() in 能用的参考音后缀]
    提醒 = "\n（合规：只能用本人同意过的本人声音；学生与他人的声音一律不许放进来）"
    if not 音频们:
        raise ValueError("参考音目录里一个 .wav 都没有：" + 目录 + 提醒)
    音频 = os.path.join(目录, 音频们[0])
    文字路径 = os.path.splitext(音频)[0] + ".txt"
    if not os.path.isfile(文字路径):
        raise ValueError("参考音缺一份\"它念的是什么字\"：请建 " + os.path.basename(文字路径)
                         + "，第一行写那段录音的内容（3–10 秒大约 10–30 个字）" + 提醒)
    with open(文字路径, "r", encoding="utf-8") as 文件:
        for 行 in 文件:
            行 = 行.strip()
            if 行 and not 行.startswith("#"):
                return 音频, 行
    raise ValueError("参考音的文字文件是空的：" + os.path.basename(文字路径) + 提醒)


def 合成(文本, 参考音, 参考音文本, 语言="zh", 语速=1.0, 地址=None, 超时=默认超时):
    地址 = 地址 or 取地址()
    文本 = str(文本 or "").strip()
    if not 文本:
        raise ValueError("要合成的文字是空的")
    if len(文本) > 最长文本:
        raise ValueError("一次最多合成 %d 个字（这次 %d 个）。讲稿请按页分开合成。"
                         % (最长文本, len(文本)))
    if not os.path.isfile(str(参考音)):
        raise ValueError("找不到参考音文件：" + os.path.basename(str(参考音)))
    if not 服务在吗(地址):
        raise RuntimeError(没启动怎么说(地址))

    请求体 = {
        "text": 文本,
        "text_lang": 语言,
        "ref_audio_path": str(参考音),
        "prompt_text": str(参考音文本 or ""),
        "prompt_lang": 语言,
        "text_split_method": "cut5",
        "batch_size": 1,
        "media_type": "wav",
        "streaming_mode": False,
        "speed_factor": float(语速),
    }
    请求 = urllib.request.Request(
        地址.rstrip("/") + "/tts",
        data=json.dumps(请求体, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(请求, timeout=超时) as 响应:
            数据 = 响应.read()
    except urllib.error.HTTPError as 异常:
        详情 = 异常.read().decode("utf-8", "replace")[:200]
        raise RuntimeError("语音服务返回 " + str(异常.code) + "：" + 详情) from 异常
    except urllib.error.URLError as 异常:
        raise RuntimeError(没启动怎么说(地址) + "\n（底层错误：" + str(异常.reason) + "）") from 异常
    if len(数据) < 44 or 数据[:4] != b"RIFF":
        raise RuntimeError("语音服务没回音频（前 120 字节：" + repr(数据[:120]) + "）")
    return 数据


def 合成到文件(文本, 输出路径, 参考音, 参考音文本, **其余):
    字节 = 合成(文本, 参考音, 参考音文本, **其余)
    临时 = str(输出路径) + ".合成中" + "." + uuid.uuid4().hex[:8]
    with open(临时, "wb") as 文件:
        文件.write(字节)
    os.replace(临时, 输出路径)
    return 输出路径


def 设权重(参考音模型=None, 生成模型=None, 地址=None, 超时=60):
    地址 = 地址 or 取地址()
    结果 = []
    for 路径, 路由 in ((参考音模型, "set_sovits_weights"), (生成模型, "set_gpt_weights")):
        if not 路径:
            continue
        if not 服务在吗(地址):
            raise RuntimeError(没启动怎么说(地址))
        网址 = 地址.rstrip("/") + "/" + 路由 + "?" + urlencode({"weights_path": str(路径)})
        try:
            with urllib.request.urlopen(网址, timeout=超时) as 响应:
                结果.append(响应.read().decode("utf-8", "replace")[:120])
        except Exception as 异常:
            raise RuntimeError(路由 + " 失败：" + str(异常)[:160]) from 异常
    return 结果
