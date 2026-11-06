
import io
import os
import sys

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)

from 地基 import 大模型

过, 失败 = [], []


def 记(条件, 说明):
    (过 if 条件 else 失败).append(说明)


记(大模型.解析思考({"reasoning_content": "先看材料"}) == "先看材料", "① 认 reasoning_content")
记(大模型.解析思考({"reasoning": "再想办法"}) == "再想办法", "① 认 reasoning")
记(大模型.解析思考({"thinking": "再看一遍"}) == "再看一遍", "① 认 thinking")
记(大模型.解析思考({"content": "答案"}) == "", "① 没有思考字段时返回空串")
记(大模型.解析思考({"reasoning_content": "   "}) == "", "① 只有空白不算思考")
记(大模型.解析思考(None) == "", "① 传 None 不炸")

大模型.清空思考()
记(大模型.取思考() == "", "② 清空之后是空串")
大模型._本线程.思考.append("第一段")
大模型._本线程.思考.append("第二段")
两段 = 大模型.取思考()
记(两段.index("第一段") < 两段.index("第二段"), "② 多段按发生顺序拼接（%r）" % 两段[:24])
大模型.清空思考()
记(大模型.取思考() == "", "② 再清一次又回到空（不会把上一轮带进来）")

大模型._本线程.思考.append("上一轮的思考")
不清 = 大模型.取思考()
大模型.清空思考()
记("上一轮的思考" in 不清 and 大模型.取思考() == "",
   "② 反向验：不清空就会串（%r → 清空后空）" % 不清)

大模型.清空思考()
大模型._本线程.思考.append("第一步：先查材料")
大模型._本线程.思考.append("第二步：再比对哈希")
块们 = 大模型.思考块们()
记(len(块们) == 2 and 块们[0].startswith("第一步"), "② 思考按块取，顺序不乱（%d 块）" % len(块们))
记(chr(10) + chr(10) in 大模型.取思考(), "② 拼成一段时块之间仍有分隔（向后兼容）")
大模型.清空思考()

import 能力.创造模式 as 创造
源 = io.open(os.path.join(根, "能力", "创造模式.py"), encoding="utf-8").read()
记('"思考": 大模型.取思考()' in 源, "③ 创造模式返回里把思考带出来")
记("大模型.清空思考()" in 源, "③ 每轮开始前清空思考（否则串轮）")

网页 = io.open(os.path.join(根, "网页", "首页.js"), encoding="utf-8").read()
记("<details class=\"think\">" in 网页, "④ 前端把思考渲染成可折叠块")
记("思考 ' + (号 + 1) + '/' + 块们.length" in 网页, "④ 多块时标序号（思考 1/3 这种写法）")
记("思考: d.思考" in 网页 and "思考块: Array.isArray(d.思考块)" in 网页,
   "④ 发送后把思考与思考块都存进这条消息")
记("思考: typeof m.思考 === 'string'" in 网页, "④ 对话缓存里保留思考（刷新后还在）")
样式 = io.open(os.path.join(根, "网页", "样式.css"), encoding="utf-8").read()
记(".think > pre" in 样式, "④ 思考区有独立样式（默认收起、可滚动）")

假页 = 网页.replace("<details class=\"think\">", "<div>")
记("<details class=\"think\">" not in 假页, "④ 反向验：去掉折叠标记后判据确实为假")

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
