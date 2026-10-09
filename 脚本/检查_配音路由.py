
import http.server
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 配置

令牌 = "自检令牌"
os.environ["SHAOXIN_TOKEN"] = 令牌

原取目录 = 配置.取目录
临时 = tempfile.mkdtemp(prefix="配音路由自检_")
课件目录 = os.path.join(临时, "课件输出")
配音目录 = os.path.join(课件目录, "自检课件_配音")
os.makedirs(配音目录)

with open(os.path.join(配音目录, "第1页.wav"), "wb") as 文件:
    文件.write(b"RIFF" + bytes(range(256)) * 8 + b"WAVE")
声音路径 = os.path.join(配音目录, "第1页.wav")
声音 = open(声音路径, "rb").read()
with open(os.path.join(配音目录, "那里有份.pptx"), "wb") as 文件:
    文件.write(b"PK\x03\x04 fake")
with open(os.path.join(临时, "秘密.txt"), "wb") as 文件:
    文件.write("这是课件目录之外的文件".encode("utf-8"))

图目录 = os.path.join(课件目录, "自检课件_页图")
os.makedirs(图目录, exist_ok=True)
页图 = b"\x89PNG\r\n\x1a\n" + bytes(range(64)) * 4
with open(os.path.join(图目录, "page1.png"), "wb") as 文件:
    文件.write(页图)

配置.取目录 = lambda 名: 课件目录 if 名 == "课件输出" else 原取目录(名)

规格 = importlib.util.spec_from_file_location(
    "本地服务模块", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "本地服务.py"))
模块 = importlib.util.module_from_spec(规格)
规格.loader.exec_module(模块)

服务 = http.server.ThreadingHTTPServer(("127.0.0.1", 0), 模块.请求处理)
端口 = 服务.server_address[1]
threading.Thread(target=服务.serve_forever, daemon=True).start()
基址 = "http://127.0.0.1:%d" % 端口
结果 = []


def 检查(名字, 通过, 说明=""):
    结果.append((名字, bool(通过), 说明))


def 取(路径, 范围=None, 带令牌=True):
    尾巴 = ("?t=" + quote(令牌)) if 带令牌 else ""
    请求 = urllib.request.Request(基址 + 路径 + 尾巴)
    if 范围:
        请求.add_header("Range", 范围)
    try:
        with urllib.request.urlopen(请求, timeout=10) as 响应:
            return 响应.status, dict(响应.headers), 响应.read()
    except urllib.error.HTTPError as 异常:
        return 异常.code, dict(异常.headers), 异常.read()


前缀 = "/" + quote("配音") + "/"
目录头 = 前缀 + quote("自检课件_配音") + "/"
地址 = 目录头 + quote("第1页.wav")

try:
    码, 头, 体 = 取(地址)
    检查("① 整份取回：200 + audio/wav + 内容逐字节一致",
        码 == 200 and 头.get("Content-Type") == "audio/wav" and 体 == 声音
        and 头.get("Content-Length") == str(len(声音)),
        "码=%s 类型=%s 长度=%s/%d" % (码, 头.get("Content-Type"), 头.get("Content-Length"), len(声音)))
    检查("② 明确告诉浏览器支持分段（<audio> 拖动进度条要用）",
        头.get("Accept-Ranges") == "bytes", "Accept-Ranges=" + str(头.get("Accept-Ranges")))

    码, 头, 体 = 取(地址, 范围="bytes=0-99")
    检查("③ Range: bytes=0-99 → 206 + 切片内容对",
        码 == 206 and 体 == 声音[:100] and 头.get("Content-Range") == "bytes 0-99/%d" % len(声音),
        "码=%s Content-Range=%s 长度=%d" % (码, 头.get("Content-Range"), len(体)))

    码, 头, 体 = 取(地址, 范围="bytes=100-")
    检查("④ Range: bytes=100- → 206 + 到末尾的内容",
        码 == 206 and 体 == 声音[100:] and 头.get("Content-Range") == "bytes 100-%d/%d" % (len(声音) - 1, len(声音)),
        "码=%s 长度=%d" % (码, len(体)))

    码, 头, 体 = 取(地址, 范围="bytes=abc-def")
    检查("⑤ 怪 Range → 退化成整份（200，内容完整、不是 206 的错位切片）",

        码 == 200 and 体 == 声音, "码=%s 长度=%d" % (码, len(体)))

    try:
        _码0, _头0, _身0 = 取(地址, 范围=None, 带令牌=True)
        _总 = int(_头0.get("Content-Length") or 0)
        _码, _头, _身 = 取(地址, 范围="bytes=-1000", 带令牌=True)
        _区间 = str(_头.get("Content-Range") or "")
        检查("Range 后缀区间：bytes=-1000 要的是**最后** 1000 字节",
           _码 == 206 and len(_身) == 1000 and _区间 == "bytes %d-%d/%d" % (_总 - 1000, _总 - 1, _总),
           "码=%s 字节=%d 区间=%s 总长=%d" % (_码, len(_身), _区间, _总))
    except Exception as _异常:
        检查("Range 后缀区间：bytes=-1000 要的是**最后** 1000 字节", False,
           type(_异常).__name__ + "：" + str(_异常)[:60])

    原判本机 = 模块.请求处理.是对端本机
    模块.请求处理.是对端本机 = lambda self: False
    服务2 = http.server.ThreadingHTTPServer(("127.0.0.1", 0), 模块.请求处理)
    基址2 = "http://127.0.0.1:%d" % 服务2.server_address[1]
    threading.Thread(target=服务2.serve_forever, daemon=True).start()

    def 取2(用令牌):
        尾巴 = {"": "", "对": "?t=" + quote(令牌), "错": "?t=wrong-token"}[用令牌]
        try:
            with urllib.request.urlopen(基址2 + 地址 + 尾巴, timeout=10) as 响应:
                return 响应.status
        except urllib.error.HTTPError as 异常:
            return 异常.code
    try:
        不带, 带对, 带错 = 取2(""), 取2("对"), 取2("错")
    finally:
        服务2.shutdown()
        模块.请求处理.是对端本机 = 原判本机
    检查("⑥ 网络来路：不带令牌 403 / 带对 200 / 带错 403",
        不带 == 403 and 带对 == 200 and 带错 == 403,
        "不带=%s 带对=%s 带错=%s（本机回环免令牌，所以下面几条不带令牌也通，那是设计）"
        % (不带, 带对, 带错))

    码, 头, 体 = 取(目录头 + quote("那里有份.pptx"))
    检查("⑦ 要一个不是 .wav 的文件 → 404", 码 == 404, "码=%s" % 码)

    码, 头, 体 = 取(前缀 + "..%2F..%2F/" + quote("秘密.txt"))
    码2, 头2, 体2 = 取(前缀 + quote("..") + "/" + quote("秘密.txt"))
    穿越内容 = b"".join([体 or b"", 体2 or b""])
    检查("⑧ 路径穿越 → 404，且读不到课件目录之外的文件",
        码 == 404 and 码2 == 404 and "课件目录之外" not in 穿越内容.decode("utf-8", "replace"),
        "码=%s/%s" % (码, 码2))

    码, 头, 体 = 取(目录头.rstrip("/"))
    码2, _, _ = 取(前缀 + "a/b/c.wav")
    检查("⑨ 地址段数不对 → 404 且给人话（不是 500）",
        码 == 404 and 码2 == 404, "码=%s/%s" % (码, 码2))

    码, 头, 体 = 取(目录头 + quote("第9页.wav"))
    检查("⑩ 文件不存在 → 404", 码 == 404, "码=%s" % 码)

    图目录头 = 前缀.replace(quote("配音"), quote("课件图")) + quote("自检课件_页图") + "/"
    码, 头, 体 = 取(图目录头 + "page1.png")
    检查("⑪ 页图整份取回：200 + image/png + 内容逐字节一致",
        码 == 200 and 头.get("Content-Type") == "image/png" and 体 == 页图,
        "码=%s 类型=%s 长度=%s" % (码, 头.get("Content-Type"), 头.get("Content-Length")))
    码, _, _ = 取(图目录头 + quote("那里有份.pptx"))
    检查("⑫ 要一个不是 .png 的文件 → 404", 码 == 404, "码=%s" % 码)
    码, _, 体 = 取(前缀.replace(quote("配音"), quote("课件图")) + "..%2F..%2F/" + quote("秘密.txt"))
    检查("⑬ 页图路径穿越 → 404，且读不到课件目录之外的文件",
        码 == 404 and "课件目录之外" not in 体.decode("utf-8", "replace"), "码=%s" % 码)
finally:
    服务.shutdown()
    配置.取目录 = 原取目录
    os.environ.pop("SHAOXIN_TOKEN", None)
    shutil.rmtree(临时, ignore_errors=True)

for 序号, (名字, 通过, 说明) in enumerate(结果, 1):
    print("  %2d. %s %s —— %s" % (序号, "通过" if 通过 else "不过", 名字, 说明))
通过数 = sum(1 for _名, 通, _说 in 结果 if 通)
print("\n%d/%d" % (通过数, len(结果)))
sys.exit(0 if 通过数 == len(结果) else 1)
