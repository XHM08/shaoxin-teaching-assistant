
import ast
import io
import json
import os
import sys
import urllib.error

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _页面文本

from 地基 import 联网
from 能力 import 联网查证

失败 = []
计数 = {"总": 0}


def 查(名, 条件, 细节=""):
    计数["总"] += 1
    print(("✓ " if 条件 else "✗ ") + 名 + ("" if 条件 else "   ← " + 细节))
    if not 条件:
        失败.append(名)


def 抓异常(函数, *参):
    try:
        函数(*参)
    except Exception as 错:
        return 错
    return None


class 假响应(io.BytesIO):
    pass


def 装假网络(状态码=200, 内容=b"{}"):
    记录 = {"次": 0}

    def 开(请, timeout=None):
        记录["次"] += 1
        if 状态码 >= 400:
            raise urllib.error.HTTPError("u", 状态码, "err", {}, io.BytesIO(b""))
        return 假响应(内容)

    联网.urllib.request.urlopen = 开
    return 记录


def 还原(原开, 原选, 原取):
    联网.urllib.request.urlopen = 原开
    联网.大模型.选服务商 = 原选
    联网.大模型.取密钥 = 原取


原开 = 联网.urllib.request.urlopen
原选 = 联网.大模型.选服务商
原取 = 联网.大模型.取密钥

try:
    联网.大模型.选服务商 = lambda 配置表=None, 指定=None: ("deepseek", {"base_url": "https://api.deepseek.com"})
    联网.大模型.取密钥 = lambda 名字=None, 条目=None: "sk-fake"

    查("空参被挡下", isinstance(抓异常(联网查证.处理, "", ""), ValueError))
    查("条数不是数字 → 拒", isinstance(抓异常(联网查证.统一条数, "五条"), ValueError))
    查("条数超上限 → 夹到 10", 联网查证.统一条数(999) == 联网.最多条数)
    查("网址没带协议 → 拒", isinstance(抓异常(联网.抓取, "example.com"), ValueError))
    查("查询超 128 字 → 拒", isinstance(抓异常(联网.搜索, "字" * 129), ValueError))

    记 = 装假网络(200)
    抓异常(联网.搜索, "字" * 129)
    查("查询超长时**一个请求都没发**（别花钱才崩）", 记["次"] == 0, "发了 %d 次" % 记["次"])

    联网.大模型.选服务商 = lambda 配置表=None, 指定=None: ("moonshot", {"base_url": "https://api.moonshot.cn"})
    错 = 抓异常(联网.搜索, "测试")
    联网.大模型.选服务商 = lambda 配置表=None, 指定=None: ("deepseek", {"base_url": "https://api.deepseek.com"})
    查("换到非 DeepSeek 服务商 → 说清只支持官方",
      isinstance(错, RuntimeError) and "只支持 DeepSeek 官方" in str(错), str(错))

    装假网络(402)
    错 = 抓异常(联网.搜索, "测试")
    查("402 → 中文说明（不把英文栈扔给老师）",
      isinstance(错, RuntimeError) and "余额不足" in str(错), str(错))

    假结果 = {"results": [
        {"title": "T1", "url": "https://a.example/1", "date": "2026-10-17", "authority": 5, "summary": "S1"},
        {"title": "T2", "url": "https://a.example/2", "date": "", "authority": None, "snippet": "S2"},
    ]}
    整 = 联网.整理结果(假结果, 上限=2)
    查("结果字段映射对", len(整) == 2 and 整[0]["权威"] == 5 and 整[1]["摘要"] == "S2",
      json.dumps(整, ensure_ascii=False)[:160])

    原搜索 = 联网.搜索
    原抓取 = 联网.抓取
    try:
        联网.搜索 = lambda 查询, 条数=5, **其他: 假结果
        回 = 联网查证.处理("查一个东西", 条数=2)
        查("搜索链路：提示/正文/条目都有",
          bool(回["条目"]) and "搜到 2 条" in 回["提示"] and "https://a.example/1" in 回["正文"])
        查("权威度缺失时显示「未知」", 回["条目"][1]["权威"] == "未知")

        长文 = "字" * (联网查证.正文上限 + 5000)
        联网.抓取 = lambda 网址, **其他: {"title": "长页", "content": 长文}
        回2 = 联网查证.处理("", "https://a.example/long")
        查("抓取：超长正文被截断且告知",
          len(回2["正文"]) < len(长文) and "只放到" in 回2["正文"], str(len(回2["正文"])))
    finally:
        联网.搜索 = 原搜索
        联网.抓取 = 原抓取
finally:
    还原(原开, 原选, 原取)

查("能力已登记（文件里有 注册表.登记 与 代号）",
  "注册表.登记" in open(os.path.join(根, "能力", "联网查证.py"), encoding="utf-8").read())

页 = _页面文本.读页面()
查("页面上有卡片、按钮、输出区", all(k in 页 for k in ("<h2>联网查证（教师用）</h2>", "btnNetGo", "netOut")))
查("这张卡在创造模式页，不在学生问答页（学生页不该有按次计费的联网工具）",
  页.find("联网查证（教师用）") < 页.find("<h2>学生问答</h2>"))
查("结果用 textContent 渲染（网页内容不当 HTML 解析）", "出.textContent" in 页)

for 路 in ("地基/联网.py", "能力/联网查证.py"):
    树 = ast.parse(open(os.path.join(根, 路), encoding="utf-8").read())
    撞 = [n.id for n in ast.walk(树) if isinstance(n, ast.Name) and n.id in ("eval", "exec", "__import__")]
    撞 += [n.attr for n in ast.walk(树) if isinstance(n, ast.Attribute) and n.attr in ("system", "popen")]
    查("没有 eval/exec/system（%s）" % 路, 撞 == [], str(撞))

print()
print("--- 反向验：把 402 的中文说明改坏，上面那条必须变红 ---")
原说明 = dict(联网.错误说明)
try:
    联网.错误说明[402] = "payment required"
    联网.大模型.选服务商 = lambda 配置表=None, 指定=None: ("deepseek", {"base_url": "https://api.deepseek.com"})
    联网.大模型.取密钥 = lambda 名字=None, 条目=None: "sk-fake"
    装假网络(402)
    错 = 抓异常(联网.搜索, "测试")
finally:
    联网.错误说明.clear()
    联网.错误说明.update(原说明)
    还原(原开, 原选, 原取)
查("改坏之后拿到的是那句英文（证明上一条真会红）",
  "余额不足" not in str(错) and "payment required" in str(错), str(错))

print()
if 失败:
    print("通过 %d / 共 %d" % (计数["总"] - len(失败), 计数["总"]))
    for 名 in 失败:
        print("  ✗ " + 名)
else:
    print("全部 %d 项通过" % 计数["总"])
sys.exit(1 if 失败 else 0)
