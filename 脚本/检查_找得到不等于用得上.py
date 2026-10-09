
import http.server
import os
import re
import socket
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 材料, 语音

结果 = []
跳过 = []
根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

判据样式 = re.compile(r"print\s*\(\s*sys\.version_info\[0\]\s*\)")
where样式 = re.compile(r"where(\.exe)?\s+[\"']?python", re.I)


def 检查(名字, 通过, 说明=""):
    结果.append((名字, bool(通过), 说明))


def 跳过一项(名字, 说明=""):
    跳过.append((名字, 说明))
    print("  跳过  " + 名字 + ("　→　" + 说明 if 说明 else ""))


def 命令行(文本):
    行表 = []
    for 行 in str(文本).splitlines():
        干净的 = 行.strip()
        if not 干净的 or 干净的.lower().startswith("rem"):
            continue
        行表.append(干净的)
    return 行表


def 批处理判据():
    for 名 in ("启动.bat", "课堂悬浮窗.bat", os.path.join("语音", "启动语音服务.bat")):
        路径 = os.path.join(根, 名)
        if not os.path.isfile(路径):
            检查("① %s 在" % 名, False, 路径)
            continue
        原 = open(路径, "rb").read()
        文本 = 原.decode("utf-8", "replace")
        执行行 = 命令行(文本)
        违规 = [行 for 行 in 执行行 if where样式.search(行)]
        检查("① %s 不拿 `where python` 当判据（它命中应用商店的桩）" % 名, not 违规,
            "共 %d 行会执行，没出现 where python" % len(执行行)
            if not 违规 else "执行行里还有：%s" % 违规[:1])
        判据行 = [行 for 行 in 执行行 if 判据样式.search(行)]
        检查("① %s 的判据是**看输出**（桩返回 0 也挡得住）" % 名, bool(判据行),
            str(判据行[0])[:76] if 判据行 else "执行行里没找到 print(sys.version_info[0])")
        检查("① %s 是 UTF-8 无 BOM + CRLF（改它时别把编码改掉）" % 名,
            (not 原.startswith(b"\xef\xbb\xbf")) and 原.count(b"\r\n") > 0
            and 原.count(b"\n") == 原.count(b"\r\n"),
            "BOM=%s CRLF=%d 独行LF=%d" % (原.startswith(b"\xef\xbb\xbf"),
                                      原.count(b"\r\n"), 原.count(b"\n") - 原.count(b"\r\n")))


def OCR判据():
    try:
        原因 = 材料.OCR不可用的原因()
        检查("② 没探测过时问「OCR 为什么不可用」→ 返回空串、不抛错", isinstance(原因, str), repr(原因))
    except Exception as 异常:
        检查("② 没探测过时问「OCR 为什么不可用」→ 返回空串、不抛错", False,
            type(异常).__name__ + "：" + str(异常)[:60])

    if os.name != "nt" or not os.path.isfile(材料.OCR脚本路径) or 材料.找powershell() is None:
        跳过一项("② 探针那一组（这台机器上 OCR 脚本或 powershell 不可达）", "这一条没验")
        return

    原可用, 原因0, 时刻0 = 材料._OCR可用, 材料._OCR原因, 材料._OCR探针时刻
    原跑 = 材料._跑OCR
    调用 = []

    class 假失败:
        returncode = 2
        stderr = "no OCR engine available"
        stdout = ""

    材料._OCR可用, 材料._OCR原因, 材料._OCR探针时刻 = None, "", 0.0
    材料._跑OCR = lambda *a, **k: (调用.append(1), 假失败())[1]
    try:
        好 = 材料.OCR可用()
        一次 = len(调用)
        可读, 说明 = 材料.能读("一张图.png")
        材料.OCR可用()
        检查("② 探针失败 → 判成不可用，且把原因说出来（不当成可用）",
            (not 好) and ("no OCR engine available" in 材料.OCR不可用的原因()),
            材料.OCR不可用的原因()[:50])
        检查("② 不可用时给的话要带原因、也要带出路（先转成文字）",
            (not 可读) and ("转成文字" in 说明) and ("no OCR engine available" in 说明), 说明[:70])
        检查("② 失败结果要缓存（问第二遍不该再真跑一次探针）", 一次 == 1 and len(调用) == 1,
            "第一次之后共 %d 次，问第二遍之后共 %d 次" % (一次, len(调用)))
        材料._OCR探针时刻 = 0.0
        材料.OCR可用()
        检查("② 缓存过期后会重新探一次（装了语言包不必重启程序）", len(调用) == 2,
            "共 %d 次" % len(调用))
    finally:
        材料._跑OCR = 原跑
        材料._OCR可用, 材料._OCR原因, 材料._OCR探针时刻 = 原可用, 原因0, 时刻0


def 语音判据():
    检查("③ 空端口 → 语音服务判成「不在」", 语音.服务在吗("http://127.0.0.1:1", 超时=1) is False)

    服务 = socket.socket()
    服务.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    服务.bind(("127.0.0.1", 0))
    服务.listen(5)
    端口 = 服务.getsockname()[1]

    def 哑服务():
        try:
            连, _ = 服务.accept()
            time.sleep(0.8)
            连.close()
        except OSError:
            pass

    threading.Thread(target=哑服务, daemon=True).start()
    try:
        检查("③ 非 HTTP 的程序占着端口 → 也判成「不在」（不是只看 TCP 连得上）",
            语音.服务在吗("http://127.0.0.1:%d" % 端口, 超时=1) is False)
    finally:
        服务.close()

    class 最小HTTP(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_error(404)

        def log_message(self, *args):
            pass

    真 = http.server.ThreadingHTTPServer(("127.0.0.1", 0), 最小HTTP)
    threading.Thread(target=真.serve_forever, daemon=True).start()
    try:
        检查("③ 真有个 HTTP 服务在、而且它对这个路由回 404 → 仍然判成「在」",
            语音.服务在吗("http://127.0.0.1:%d" % 真.server_address[1], 超时=3) is True)
    finally:
        真.shutdown()


def main():
    批处理判据()
    OCR判据()
    语音判据()
    print()
    坏 = 0
    for 名字, 过, 说明 in 结果:
        print(("  通过  " if 过 else "  失败  ") + 名字 + ("　→　" + 说明 if 说明 else ""))
        坏 += 0 if 过 else 1
    if 跳过:
        print("另外跳过 %d 项（没验，不算通过）" % len(跳过))
    print("全部 %d 项通过" % len(结果) if not 坏 else "%d 项失败" % 坏)
    return 0 if not 坏 else 1


if __name__ == "__main__":
    sys.exit(main())
