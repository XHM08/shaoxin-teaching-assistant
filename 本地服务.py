
import ipaddress
import json
import os
import secrets
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlparse

from 地基 import 大模型, 版本, 材料, 注册表, 技能包, 配置, 审计, 工具箱

本目录 = os.path.dirname(os.path.abspath(__file__))
网页目录 = os.path.join(本目录, "网页")
端口 = int(os.environ.get("SHAOXIN_PORT", "8765"))
请求体上限 = 1024 * 1024

主机 = os.environ.get("SHAOXIN_HOST", "127.0.0.1").strip() or "127.0.0.1"
绑定局域网 = 主机 not in ("127.0.0.1", "localhost")

访问令牌 = os.environ.get("SHAOXIN_TOKEN", "").strip()
if 绑定局域网 and not 访问令牌:
    访问令牌 = secrets.token_hex(4)

本机来源 = ("http://127.0.0.1:" + str(端口), "http://localhost:" + str(端口))

回环判断 = ipaddress.ip_address


def 来源可信(来源):
    if 来源 in 本机来源:
        return True
    if not 绑定局域网:
        return False
    try:
        解析 = urlparse(来源)
        端口号 = 解析.port
    except ValueError:
        return False
    if 解析.scheme != "http" or 端口号 != 端口:
        return False
    try:
        return ipaddress.ip_address(解析.hostname or "").is_private
    except ValueError:
        return False


def 本机地址们():
    地址们 = []
    try:
        套 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            套.connect(("10.255.255.255", 1))
            地址们.append(套.getsockname()[0])
        finally:
            套.close()
    except OSError:
        pass
    return 地址们


def 加载能力():
    结果 = 注册表.全部加载(os.path.join(本目录, "能力"))
    工具箱.接上MCP(记录=lambda 一条: print("  " + 一条, flush=True))
    return 结果


def 取选项(类别):
    if 类别 not in 注册表.可选项来源类别:
        return []
    if 类别 == "材料":
        return [条目["文件名"] for 条目 in 材料.材料清单()]
    if 类别 == "技能包":
        return [条目["技能包代号"] for 条目 in 技能包.技能包清单()]
    if 类别 == "providers":
        try:
            return sorted(大模型.读配置().get("providers", {}))
        except (OSError, RuntimeError, ValueError):
            return []
    return []


def 能力视图():
    结果 = []
    for 能力 in 注册表.能力清单():
        参数表 = []
        for 参数项 in 能力["参数"]:
            副本 = dict(参数项)
            if 副本.get("可选项来源"):
                副本["可选项"] = 取选项(副本["可选项来源"])
            参数表.append(副本)
        结果.append({"代号": 能力["代号"], "标题": 能力["标题"],
                     "说明": 能力["说明"], "参数": 参数表})
    return 结果


def 跑能力(代号, 实参):
    审计.记当前能力(代号)
    return 注册表.校验参数(代号, 实参)(**(实参 or {}))


class 请求处理(BaseHTTPRequestHandler):

    timeout = 30

    def log_message(self, 格式, *实参):
        pass

    def 发文本(self, 状态码, 文本, 类型="text/plain; charset=utf-8"):
        数据 = 文本.encode("utf-8")
        try:
            self.send_response(状态码)
            self.send_header("Content-Type", 类型)
            self.send_header("Content-Length", str(len(数据)))
            self.end_headers()
            self.wfile.write(数据)
        except OSError:
            pass

    def 发JSON(self, 状态码, 对象):
        self.发文本(状态码, json.dumps(对象, ensure_ascii=False),
                   "application/json; charset=utf-8")

    def 送文件(self, 路径, 类型):
        if not os.path.isfile(路径):
            return self.发JSON(404, {"错误": "找不到文件：" + 路径})
        with open(路径, "r", encoding="utf-8") as 文件:
            self.发文本(200, 文件.read(), 类型)

    def 送下载(self, 路径, 类型, 文件名):
        if not os.path.isfile(路径):
            return self.发JSON(404, {"错误": "找不到文件：" + 路径})
        with open(路径, "rb") as 文件:
            数据 = 文件.read()
        头部 = ("attachment; filename=\"deck.pptx\"; filename*=UTF-8''"
                + quote(文件名, safe=""))
        头部.encode("latin-1")
        try:
            self.send_response(200)
            self.send_header("Content-Type", 类型)
            self.send_header("Content-Length", str(len(数据)))
            self.send_header("Content-Disposition", 头部)
            self.end_headers()
            self.wfile.write(数据)
        except OSError:
            pass

    def 是对端本机(self):
        try:
            return 回环判断(self.client_address[0]).is_loopback
        except Exception:
            return False

    def 带对令牌(self):
        if self.是对端本机():
            return True
        if not 访问令牌:
            return False
        try:
            查询 = parse_qs(urlparse(self.path).query)
        except ValueError:
            return False
        return 查询.get("t", [""])[0] == 访问令牌

    def 可以继续吗(self, 是读还是写):
        if not self.带对令牌():
            return False
        if 是读还是写 == "读":
            return True
        if not 来源可信(self.headers.get("Origin", "")):
            return False
        类型 = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        return 类型 == "application/json"

    def 请求可信(self):
        return self.可以继续吗("写")

    def 取路径(self):
        return unquote(self.path.split("?", 1)[0])

    def do_GET(self):
        路径 = self.取路径()
        if not self.可以继续吗("读"):
            return self.发JSON(403, {"错误": "这份服务是对局域网开的，地址要带上访问令牌（?t=…）。"
                                          "令牌每次启动都不一样，看电脑上那个窗口打印的那一行。"})
        try:
            if 路径 in ("/", "/首页.html"):
                return self.送文件(os.path.join(网页目录, "首页.html"),
                                  "text/html; charset=utf-8")
            if 路径.startswith("/网页/"):
                文件名 = os.path.basename(路径)
                类型 = "text/plain; charset=utf-8"
                if 文件名.endswith(".css"):
                    类型 = "text/css; charset=utf-8"
                elif 文件名.endswith(".js"):
                    类型 = "application/javascript; charset=utf-8"
                elif 文件名.endswith(".html"):
                    类型 = "text/html; charset=utf-8"
                return self.送文件(os.path.join(网页目录, 文件名), 类型)
            if 路径.startswith("/课件/"):
                文件名 = os.path.basename(路径)
                return self.送下载(
                    os.path.join(配置.取目录("课件输出"), 文件名),
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    文件名)

            if 路径 == "/api/能力":
                return self.发JSON(200, {"版本": 版本.版本号, "条目": 能力视图()})

            self.发JSON(404, {"错误": "没有这个地址：" + 路径})
        except Exception as 异常:
            self.发JSON(500, {"错误": type(异常).__name__ + ": " + str(异常)})

    def do_POST(self):
        路径 = self.取路径()
        try:
            if 路径 != "/api/run":
                return self.发JSON(404, {"错误": "没有这个地址：" + 路径})
            if not self.请求可信():
                return self.发JSON(403, {"错误": "拒绝：请求不是来自本页面"})

            try:
                长度 = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return self.发JSON(400, {"错误": "Content-Length 不是个整数。"})
            if 长度 < 0 or 长度 > 请求体上限:
                return self.发JSON(400, {"错误": "请求体长度不合法：" + str(长度)})
            if 长度 > 请求体上限:
                return self.发JSON(413, {"错误": "请求体过大"})
            原始字节 = self.rfile.read(长度) if 长度 else b"{}"
            请求 = json.loads(原始字节.decode("utf-8") or "{}")

            结果 = 跑能力(请求.get("能力", ""), 请求.get("参数", {}))
            return self.发JSON(200, 结果)
        except (KeyError, ValueError) as 异常:
            说明 = 异常.args[0] if 异常.args else 异常
            self.发JSON(400, {"错误": str(说明)})
        except Exception as 异常:
            print("[" + type(异常).__name__ + "] " + str(异常)[:200])
            self.发JSON(500, {"错误": str(异常)})


def 主程序():
    ThreadingHTTPServer.allow_reuse_address = False

    加载能力()
    try:
        服务 = ThreadingHTTPServer((主机, 端口), 请求处理)
    except OSError as 异常:
        raise SystemExit(
            "启动失败：端口 " + str(端口) + " 绑不上。\n"
            "  多半是已经开过一个了 —— 看看任务栏有没有「邵新」的服务窗口；\n"
            "  也可能是别的程序占着这个端口。\n"
            "  原始错误：" + str(异常)
        )

    print("「邵新」辅助教育系统 已启动", flush=True)
    print("  本机打开： http://127.0.0.1:" + str(端口), flush=True)
    if 绑定局域网:
        尾巴 = ("/?t=" + 访问令牌) if 访问令牌 else "/"
        地址们 = 本机地址们()
        if 地址们:
            for 地址 in 地址们:
                print("  局域网上打开： http://" + 地址 + ":" + str(端口) + 尾巴, flush=True)
        else:
            print("  局域网上打开： http://<本机局域网的 IP>:" + str(端口) + 尾巴, flush=True)
        if not 访问令牌:
            print("  ⚠ 没设访问令牌：同一个 Wi-Fi 上任何设备都能驱动本机能力"
                  "（包括电脑服务、执行命令）", flush=True)
    print("  已加载能力：" + ", ".join(注册表.全部名字()), flush=True)
    print("  按 Ctrl+C 停止", flush=True)
    服务.serve_forever()


if __name__ == "__main__":
    主程序()
