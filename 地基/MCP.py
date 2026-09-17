
import json
import os
import queue
import subprocess
import threading
import time

from 地基 import 版本

协议版本 = "2025-06-18"
默认超时 = 60.0
启动给多少秒 = 0.8


class 出错(Exception):
    pass


class 服务器:

    def __init__(self, 名字, 命令, 参数们=None, 环境=None, 超时=默认超时):
        self.名字 = str(名字)
        self.命令 = str(命令)
        self.参数们 = [str(一个) for 一个 in (参数们 or [])]
        self.额外环境 = 环境 or {}
        self.超时 = float(超时)
        self.进程 = None
        self.服务器信息 = {}
        self.能力 = {}
        self.协商版本 = ""
        self.日志 = []
        self._收件箱 = queue.Queue()
        self._号 = 0
        self._锁 = threading.Lock()


    def 启动(self):
        if self.进程 is not None:
            return self
        环境 = dict(os.environ)
        环境.update({str(键): str(值) for 键, 值 in self.额外环境.items()})
        try:
            self.进程 = subprocess.Popen(
                [self.命令] + self.参数们,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=环境, text=True, encoding="utf-8", errors="replace", bufsize=1)
        except OSError as 异常:
            raise 出错("起不了 MCP 服务器「%s」：%s" % (self.名字, 异常)) from 异常

        threading.Thread(target=self._读stdout, daemon=True).start()
        threading.Thread(target=self._读stderr, daemon=True).start()

        回 = None
        try:
            回 = self._请求("initialize", {
                "protocolVersion": 协议版本,
                "capabilities": {},
                "clientInfo": {"name": "邵新辅助教育系统", "version": 版本.版本号},
            })
        except Exception:
            self.关闭()
            raise
        结果 = 回.get("result") or {}
        self.协商版本 = str(结果.get("protocolVersion") or "")
        self.服务器信息 = 结果.get("serverInfo") or {}
        self.能力 = 结果.get("capabilities") or {}
        self._通知("notifications/initialized", {})
        return self

    def 有工具吗(self):
        return "tools" in self.能力


    def 列工具(self):
        if not self.有工具吗():
            return []
        回 = self._请求("tools/list", {})
        工具们 = (回.get("result") or {}).get("tools") or []
        结果 = []
        for 一 in 工具们:
            if not isinstance(一, dict) or not 一.get("name"):
                continue
            结果.append({
                "名字": str(一["name"]),
                "说明": str(一.get("description") or 一.get("title") or ""),
                "参数格式": 一.get("inputSchema") or {},
            })
        return 结果

    def 调工具(self, 名字, 参数=None):
        回 = self._请求("tools/call", {"name": str(名字), "arguments": 参数 or {}})
        结果 = 回.get("result") or {}
        片段们 = 结果.get("content") or []
        文本 = []
        for 片段 in 片段们:
            if isinstance(片段, dict) and 片段.get("type") == "text":
                文本.append(str(片段.get("text") or ""))
            elif isinstance(片段, dict) and 片段.get("type"):
                文本.append("（服务器返回了一段 %s，这里只看文本）" % 片段.get("type"))
        正文 = "\n".join(文本).strip()
        if 结果.get("isError"):
            return "（服务器说这次工具执行出错）" + (正文 or "没给原因"), True
        return (正文 or "（服务器没返回文本）"), False


    def 关闭(self):
        进程, self.进程 = self.进程, None
        if 进程 is None:
            return
        try:
            if 进程.stdin:
                进程.stdin.close()
        except OSError:
            pass
        try:
            进程.wait(timeout=启动给多少秒)
            return
        except subprocess.TimeoutExpired:
            pass
        try:
            进程.terminate()
            进程.wait(timeout=3)
        except Exception:
            try:
                进程.kill()
            except Exception:
                pass


    def _读stdout(self):
        try:
            for 行 in self.进程.stdout:
                self._收件箱.put(行)
        except Exception:
            pass
        self._收件箱.put(None)

    def _读stderr(self):
        try:
            for 行 in self.进程.stderr:
                self.日志.append(行.rstrip())
                del self.日志[:-20]
        except Exception:
            pass

    def _写(self, 消息):
        if self.进程 is None or self.进程.stdin is None:
            raise 出错("MCP 服务器「%s」已经关了" % self.名字)
        行 = json.dumps(消息, ensure_ascii=False) + "\n"
        try:
            self.进程.stdin.write(行)
            self.进程.stdin.flush()
        except (OSError, ValueError) as 异常:
            raise 出错("往 MCP 服务器「%s」写不进去（它可能已经退出了）：%s"
                       % (self.名字, 异常)) from 异常

    def _通知(self, 方法, 参数):
        self._写({"jsonrpc": "2.0", "method": 方法, "params": 参数})

    def _请求(self, 方法, 参数):
        with self._锁:
            self._号 += 1
            号 = self._号
            self._写({"jsonrpc": "2.0", "id": 号, "method": 方法, "params": 参数})
            截止 = time.monotonic() + self.超时
            while True:
                剩 = 截止 - time.monotonic()
                if 剩 <= 0:
                    self._尽力取消(号)
                    raise 出错("MCP 服务器「%s」的 %s 超时（%.0f 秒没回）。它最近的日志：%s"
                               % (self.名字, 方法, self.超时, self._日志尾巴()))
                try:
                    行 = self._收件箱.get(timeout=剩)
                except queue.Empty:
                    continue
                if 行 is None:
                    raise 出错("MCP 服务器「%s」退出了（%s 还没回）。它最近的日志：%s"
                               % (self.名字, 方法, self._日志尾巴()))
                行 = 行.strip()
                if not 行:
                    continue
                try:
                    消息 = json.loads(行)
                except ValueError:
                    continue
                if not isinstance(消息, dict) or 消息.get("id") != 号:
                    continue
                if 消息.get("error"):
                    错 = 消息["error"] or {}
                    raise 出错("MCP 服务器「%s」拒绝了 %s：%s"
                               % (self.名字, 方法, 错.get("message") or 错))
                return 消息

    def _尽力取消(self, 号):
        try:
            self._通知("notifications/cancelled",
                     {"requestId": 号, "reason": "客户端超时"})
        except Exception:
            pass

    def _日志尾巴(self):
        return " ｜ ".join(self.日志[-3:]) or "（没有）"


def 读配置(路径):
    if not os.path.isfile(路径):
        return {"启用": False, "服务器们": []}
    try:
        with open(路径, "r", encoding="utf-8") as 文件:
            表 = json.load(文件)
    except (OSError, ValueError) as 异常:
        raise 出错("读不了 %s：%s" % (路径, 异常)) from 异常
    if not isinstance(表, dict):
        raise 出错("MCP服务器.json 应该是一个对象")
    服务器们 = 表.get("服务器们")
    return {"启用": bool(表.get("启用")),
            "服务器们": 服务器们 if isinstance(服务器们, list) else []}


def 起全部(配置表, 记录=None):
    结果 = []
    if not 配置表.get("启用"):
        return 结果
    for 一 in 配置表.get("服务器们") or []:
        if not isinstance(一, dict) or not 一.get("命令"):
            continue
        名字 = str(一.get("名字") or 一.get("命令"))
        try:
            服 = 服务器(名字, 一["命令"], 一.get("参数"), 一.get("环境"),
                       float(一.get("超时") or 默认超时)).启动()
            结果.append(服)
            if 记录:
                记录("已连上 MCP 服务器「%s」，它提供 %d 个工具"
                     % (名字, len(服.列工具())))
        except 出错 as 异常:
            if 记录:
                记录("MCP 服务器「%s」没起来，跳过：%s" % (名字, 异常))
        except Exception as 异常:
            if 记录:
                记录("MCP 服务器「%s」没起来，跳过：%s: %s"
                     % (名字, type(异常).__name__, 异常))
    return 结果
