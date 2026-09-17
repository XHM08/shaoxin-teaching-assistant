
import json
import sys
import time

协议版本 = "2025-06-18"

工具们 = [
    {"name": "回声", "description": "把给你的话原样说回来",
     "inputSchema": {"type": "object",
                     "properties": {"话": {"type": "string", "description": "要说的话"}},
                     "required": ["话"]}},
    {"name": "报错", "description": "总是自报执行出错",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "写日志", "description": "往 stderr 写两万行日志",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "卡住", "description": "睡 5 秒再回话（验客户端超时；睡满后它能继续干活）",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "查取消", "description": "报告有没有收到过取消通知",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "退出", "description": "收到就自己退出，用来验「服务器半路没了」这条路",
     "inputSchema": {"type": "object", "properties": {}}},
]

收到的取消 = []


def 回(号, 结果):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": 号, "result": 结果},
                                ensure_ascii=False) + "\n")
    sys.stdout.flush()


def 回错误(号, 码, 说明):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": 号,
                                 "error": {"code": 码, "message": 说明}},
                                ensure_ascii=False) + "\n")
    sys.stdout.flush()


for 行 in sys.stdin:
    行 = 行.strip()
    if not 行:
        continue
    try:
        消息 = json.loads(行)
    except ValueError:
        continue
    if not isinstance(消息, dict):
        continue

    方法 = 消息.get("method")
    号 = 消息.get("id")

    if 方法 == "initialize":
        回(号, {"protocolVersion": 协议版本,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "自检服务器", "version": "1.0"}})
    elif 方法 == "notifications/initialized":
        pass
    elif 方法 == "notifications/cancelled":
        收到的取消.append((消息.get("params") or {}).get("requestId"))
    elif 方法 == "tools/list":
        回(号, {"tools": 工具们})
    elif 方法 == "tools/call":
        参数 = 消息.get("params") or {}
        名字 = 参数.get("name")
        实参 = 参数.get("arguments") or {}
        if 名字 == "回声":
            回(号, {"content": [{"type": "text",
                                "text": "你说的是：" + str(实参.get("话", ""))}]})
        elif 名字 == "报错":
            回(号, {"content": [{"type": "text", "text": "这个工具故意失败"}],
                    "isError": True})
        elif 名字 == "写日志":
            for i in range(20000):
                sys.stderr.write("这是第 %d 行日志，用来把管道缓冲区写满\n" % i)
            sys.stderr.flush()
            回(号, {"content": [{"type": "text", "text": "写了两万行日志"}]})
        elif 名字 == "卡住":
            time.sleep(5)
        elif 名字 == "查取消":
            回(号, {"content": [{"type": "text",
                                "text": "收到过的取消：" + str(收到的取消)}]})
        elif 名字 == "退出":
            sys.exit(0)
        else:
            回错误(号, -32602, "没有这个工具：" + str(名字))
