
import io
import json
import os
import sys

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)

from 地基 import 大模型
from 能力.创造模式 import _回答过滤

过, 失败 = [], []


def 记(条件, 说明):
    (过 if 条件 else 失败).append(说明)


def 假响应(行们):
    class 响应:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def __iter__(self):
            for 行 in 行们:
                yield (行 + chr(10)).encode("utf-8")
    return 响应()


片段 = []


def 收到(类型, 文本):
    片段.append((类型, 文本))


真urlopen = 大模型.urllib.request.urlopen
大模型.urllib.request.urlopen = lambda 请求, timeout=None: 假响应([
    'data: {"choices":[{"delta":{"reasoning_content":"先想"}}]}',
    'data: {"choices":[{"delta":{"reasoning_content":"一想"}}]}',
    'data: {"choices":[{"delta":{"content":"答"}}]}',
    'data: {"choices":[{"delta":{"content":"案"}}]}',
    "data: [DONE]",
])
try:
    大模型.清空思考()
    全文 = 大模型.流式问("随便问", 收到=收到, 服务商="deepseek")
finally:
    大模型.urllib.request.urlopen = 真urlopen

记(全文 == "答案", "① 回答增量拼起来等于全文（%r）" % 全文)
思考段 = "".join(文 for 类, 文 in 片段 if 类 == "思考")
回答段 = "".join(文 for 类, 文 in 片段 if 类 == "回答")
记(思考段 == "先想一想", "① 思考增量拼起来完整（%r）" % 思考段)
记(回答段 == "答案", "① 回答与思考没有串到一边（%r）" % 回答段)
记(大模型.思考块们() and 大模型.思考块们()[0] == "先想一想", "① 流式收到的思考也进了思考块")

片段.clear()
大模型.urllib.request.urlopen = lambda 请求, timeout=None: 假响应([
    'data: {"choices":[{"delta":{"content":"有效"}}]}',
    "data: [DONE]",
    'data: {"choices":[{"delta":{"content":"不该出现"}}]}',
])
try:
    全文2 = 大模型.流式问("随便问", 收到=收到, 服务商="deepseek")
finally:
    大模型.urllib.request.urlopen = 真urlopen
记(全文2 == "有效", "② [DONE] 之后的内容不再收（%r）" % 全文2)

下游 = []
过滤 = _回答过滤(lambda 类, 文: 下游.append((类, 文)))
for 片 in ('{"工具"', ': "造文件"', ', "参数"', ': {}}'):
    过滤("回答", 片)
记(not [文 for 类, 文 in 下游 if 类 == "回答"],
   "③ 工具调用那段 JSON 被挡住（下游拿到 %d 段回答）" % len([1 for 类, _ in 下游 if 类 == "回答"]))
过滤("思考", "我要先造个文件")
记(any(类 == "思考" for 类, _ in 下游), "③ 思考照常显示，不被工具过滤牵连")

下游2 = []
过滤2 = _回答过滤(lambda 类, 文: 下游2.append((类, 文)))
for 片 in ("这是", "一段", "正常回答"):
    过滤2("回答", 片)
拼 = "".join(文 for 类, 文 in 下游2 if 类 == "回答")
记(拼 == "这是一段正常回答", "③ 正常回答照常流出去，且一个字不少（%r）" % 拼)

下游3 = []
原样 = lambda 类, 文: 下游3.append((类, 文))
for 片 in ('{"工具"', ': "造文件"'):
    原样("回答", 片)
记(any("工具" in 文 for 类, 文 in 下游3), "④ 反向验：不过滤时工具 JSON 确实漏出去（证明过滤在起作用）")

print()
for 一 in 过:
    print("  ✓ " + 一)
for 一 in 失败:
    print("  ✗ " + 一)
print()
if 失败:
    print("有 %d 项没过" % len(失败))
    sys.exit(1)
print("全部 %d 项通过" % len(过))
