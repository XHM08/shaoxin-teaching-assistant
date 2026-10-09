
import http.server
import importlib.util
import io
import json
import os
import queue
import sys
import threading
import urllib.error
import urllib.request
from urllib.parse import parse_qsl, quote, urlencode

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 课堂留言

结果 = []
令牌 = "自检令牌"
原令牌环境 = os.environ.get("SHAOXIN_TOKEN")
os.environ["SHAOXIN_TOKEN"] = 令牌


def 检查(名字, 通过, 说明=""):
    结果.append((名字, bool(通过), 说明))


def 取(基址, 路径, 方法="GET", 体=None, 带令牌=True, 来源="默认"):
    路径部分, _, 查询 = 路径.partition("?")
    对 = dict(parse_qsl(查询)) if 查询 else {}
    if 带令牌:
        对["t"] = 令牌
    网址 = 基址 + quote(路径部分) + (("?" + urlencode(对)) if 对 else "")
    头, 数据 = {}, None
    if 方法 == "POST":
        数据 = json.dumps(体 or {}, ensure_ascii=False).encode("utf-8")
        头["Content-Type"] = "application/json"
        头["Origin"] = 基址 if 来源 == "默认" else 来源
    try:
        with urllib.request.urlopen(urllib.request.Request(网址, data=数据, headers=头),
                                  timeout=10) as 响应:
            return 响应.status, 响应.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as 异常:
        return 异常.code, 异常.read().decode("utf-8", "replace")


课堂留言.清空()
一条 = 课堂留言.记一条("老师转述", "学生问：倒数为什么要交换分子分母")
检查("① 窗口来的留言：序号/时间/谁/来源都对",
    一条["序号"] == 1 and 一条["来源"] == "窗口", json.dumps(一条, ensure_ascii=False)[:60])
蓝牙条 = 课堂留言.从设备记一条("麦克风（蓝牙）", "老师，我还是不明白")
有线条 = 课堂留言.从设备记一条("麦克风（有线）", "老师，第二个例题没听清")
检查("② 设备接口是通的，而且两类设备分得清（蓝牙 / 有线各记一条，来源各自对）",
    蓝牙条["来源"] == "麦克风（蓝牙）" and 有线条["来源"] == "麦克风（有线）",
    "蓝牙=%s 有线=%s" % (蓝牙条["来源"], 有线条["来源"]))

之前 = 课堂留言.取新的(0)["共"]
两次 = [课堂留言.记一条("老师转述", "同一句话")["序号"] for _ in range(2)]
检查("③ 同一句 5 秒内重发 → 丢掉（两次拿到同一个序号，且没多出一条）",
    两次[0] == 两次[1] and 课堂留言.取新的(0)["共"] == 之前 + 1,
    "两次序号=%s 共=%d" % (两次, 课堂留言.取新的(0)["共"]))
上次取到 = 课堂留言.取新的(0)["留言"][-1]["序号"]
检查("④ 取新的按序号增量（拿上一条的序号去取，只回它之后的）",
    len(课堂留言.取新的(上次取到 - 1)["留言"]) == 1
    and len(课堂留言.取新的(上次取到)["留言"]) == 0,
    "自 %d 应剩 1 条" % (上次取到 - 1))

for 坏例, 关键词, 说明 in (("   ", "空的", "空内容"), ("字" * 300, "太长了", "超长")):
    之前 = 课堂留言.取新的(0)["共"]
    try:
        课堂留言.记一条("老师转述", 坏例)
        检查("⑤ %s → 拦住" % 说明, False, "放过去了")
    except ValueError as 异常:
        检查("⑤ %s → 拦住、给人话，而且没记进去" % 说明,
           关键词 in str(异常) and 课堂留言.取新的(0)["共"] == 之前,
           str(异常)[:44])

课堂留言.清空()
起 = 课堂留言.取新的(0)
起共 = 起["共"]
号首 = None
for 号 in range(520):
    条 = 课堂留言.记一条("某同学", "第 %d 句" % 号)
    if 号首 is None:
        号首 = 条["序号"]
满 = 课堂留言.取新的(0)
检查("⑥ 满了丢最旧的，但记下丢过多少（上限 500 → 丢 20）",
    满["共"] == 起共 + 520 and 满["丢过"] == 20 and 满["留言"][0]["序号"] == 号首 + 20,
    "共=%d（起 %d）丢过=%d 最旧序号=%d（首条 %s）"
    % (满["共"], 起共, 满["丢过"], 满["留言"][0]["序号"], 号首))
课堂留言.清空()

规格 = importlib.util.spec_from_file_location(
    "本地服务模块", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "本地服务.py"))
模块 = importlib.util.module_from_spec(规格)
规格.loader.exec_module(模块)
服务 = http.server.ThreadingHTTPServer(("127.0.0.1", 0), 模块.请求处理)
基址 = "http://127.0.0.1:%d" % 服务.server_address[1]
threading.Thread(target=服务.serve_forever, daemon=True).start()
模块.本机来源 = tuple(模块.本机来源) + (基址,)

原问 = 模块.大模型.问
问过 = []


def 假问(*a, **k):
    问过.append(1)
    return "因为除以一个数，就等于乘它的倒数呀。"


模块.大模型.问 = 假问
try:
    码1, 文1 = 取(基址, "/api/记留言", "POST", {"谁": "老师转述", "内容": "学生问：为什么交换分子分母"})
    码2, 文2 = 取(基址, "/api/记留言", "POST", {"谁": "老师转述", "内容": "学生问：零为什么没有倒数"})
    检查("⑦ 按键后记一条：200 且有回执（回的来源是「窗口」）",
        码1 == 200 and json.loads(文1).get("来源") == "窗口", "码=%s %s" % (码1, 文1[:44]))
    首序号 = json.loads(文1).get("序号")

    码, 文 = 取(基址, "/api/取留言?since=%d" % 首序号)
    增量 = json.loads(文).get("留言") if 码 == 200 else []
    检查("⑧ 按序号增量取：拿第 1 条的序号去取，只回第 2 条",
        码 == 200 and len(增量) == 1 and int(增量[0]["序号"]) > int(首序号),
        "码=%s 回 %d 条（序号 %s）" % (码, len(增量), [x["序号"] for x in 增量]))

    检查("⑨ 按键之前，模型一次都没被调过（触发式的命门：不按不花钱）",
        len(问过) == 0, "已调 %d 次" % len(问过))

    码, 文 = 取(基址, "/api/课堂回应", "POST", {"序号": 首序号})
    回答 = json.loads(文).get("回答") if 码 == 200 else ""
    检查("⑩ 按键之后才调模型（正好 1 次），并拿到回答",
        码 == 200 and len(问过) == 1 and "倒数" in 回答,
        "调了 %d 次；码=%s；答=%s" % (len(问过), 码, 回答[:24]))
    留言 = 课堂留言.取新的(0)["留言"]
    检查("⑪ 邵新的回答也进了留言表（窗口上就成了一段对话）",
        len(留言) == 3 and 留言[-1]["来源"] == "邵新", str([x["来源"] for x in 留言]))

    码, 文 = 取(基址, "/api/课堂回应", "POST", {"序号": 999})
    检查("⑫ 序号不存在 → 400 人话（不是 500、也不是空回答）",
        码 == 400 and "要回应哪一句" in 文, "码=%s %s" % (码, 文[:40]))
    检查("⑫b 被拒的那次没有再调模型（拒绝要发生在花钱之前）", len(问过) == 1,
        "已调 %d 次" % len(问过))
    码, 文 = 取(基址, "/api/记留言", "POST", {"内容": "   "})
    检查("⑬ 空内容：400 + 人话", 码 == 400 and "空" in 文, "码=%s" % 码)

    原判 = 模块.请求处理.是对端本机
    模块.请求处理.是对端本机 = lambda self: False
    码不, _ = 取(基址, "/api/记留言", "POST", {"内容": "不该进去"}, 带令牌=False)
    码坏, _ = 取(基址, "/api/记留言", "POST", {"内容": "不该进去"}, 来源="http://evil.example.com")
    码好, _ = 取(基址, "/api/记留言", "POST", {"内容": "该进去"}, 来源=基址)
    模块.请求处理.是对端本机 = 原判
    检查("⑭ 网络来路：不带令牌 403 / 坏来源 403 / 好来源 200",
        码不 == 403 and 码坏 == 403 and 码好 == 200, "不带=%s 坏源=%s 好源=%s" % (码不, 码坏, 码好))

    码1, _ = 取(基址, "/api/学生留言", "POST", {"内容": "x"})
    码2, _ = 取(基址, "/api/学生入口")
    检查("⑮ 手机那条路已经删掉（/api/学生留言 与 /api/学生入口 都 404）",
        码1 == 404 and 码2 == 404, "码=%s/%s" % (码1, 码2))
    页 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "网页", "学生.html")
    检查("⑯ 学生自助页也没留下（学校禁手机，就不该有这个页面）", not os.path.isfile(页), 页)
    样本根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    规格2 = importlib.util.spec_from_file_location("课堂悬浮窗模块", os.path.join(样本根, "课堂悬浮窗.py"))
    窗模块 = importlib.util.module_from_spec(规格2)
    规格2.loader.exec_module(窗模块)
    窗模块.地址 = 基址

    class 假窗:
        已看到 = 0
        队 = queue.Queue()

    窗模块.窗口.取(假窗())
    类, 数据 = 假窗.队.get_nowait()
    检查("⑱ 窗口自己的取留言代码能跑通（中文路径要自己编码，缺了就 UnicodeEncodeError）",
        类 == "留言" and isinstance(数据, dict) and "共" in 数据, "%s：%s" % (类, str(数据)[:50]))

    前 = len(问过)
    窗记 = 窗模块.窗口.发一条(None, "/api/记留言",
                           {"谁": "老师转述", "内容": "窗口按键那条路", "来源": "窗口"})
    窗回 = 窗模块.窗口.发一条(None, "/api/课堂回应", {"序号": 窗记["序号"]}, 超时=30)
    检查("⑲ 窗口自己的按键代码能跑通（写操作要带 Origin，缺了就 403）",
        窗记.get("好") is True and bool(str(窗回.get("回答") or "")),
        "记序号=%s 回=%s" % (窗记.get("序号"), str(窗回.get("回答"))[:30]))
    检查("⑲b 走窗口这条路时，模型也正好只多调 1 次", len(问过) == 前 + 1,
        "多调了 %d 次" % (len(问过) - 前))

    假清 = type("假清", (), {})()
    假清.队 = queue.Queue()

    def _炸(*a, **k):
        raise RuntimeError("服务回了 500")

    假清.发一条 = _炸
    窗模块.窗口._清屏(假清)
    类清, 文清, *余清 = 假清.队.get_nowait()
    坏了 = bool(余清 and 余清[0])
    检查("⑳ 清屏没成时说出来、而且标成坏消息（用红字，不再用成功色）",
        类清 == "提示" and "清屏没成" in 文清 and 坏了, "%s：%s 坏消息=%s" % (类清, 文清[:40], 坏了))
finally:
    模块.大模型.问 = 原问
    服务.shutdown()
    if 原令牌环境 is None:
        os.environ.pop("SHAOXIN_TOKEN", None)
    else:
        os.environ["SHAOXIN_TOKEN"] = 原令牌环境
    课堂留言.清空()

窗源码 = io.open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "课堂悬浮窗.py"), encoding="utf-8").read()
缺键 = [x for x in ("接受学生发言（按一下）", "清屏", "现在刷新") if x not in 窗源码]
检查("⑰ 窗口源码里三个键都在（静态核对：触发键是额外新增的，不是把旧的换掉）",
    not 缺键, "缺：" + str(缺键) if 缺键 else "接受学生发言 / 清屏 / 现在刷新")

try:
    课堂留言.清空()
    清前 = 课堂留言.取新的(0).get("留言") or []
    第一条 = 课堂留言.记一条("老师转述", "清屏后说的第一句")
    取回 = [x for x in (课堂留言.取新的(0).get("留言") or [])]
    序号只增 = all(x["序号"] > 0 for x in 取回) and bool(取回)
    客户端视角 = 课堂留言.取新的(第一条["序号"] - 1).get("留言") or []
    检查("清屏后新留言仍然取得到（序号只增不减，不回绕）",
       序号只增 and any(x["内容"] == "清屏后说的第一句" for x in 客户端视角),
       "取回 %d 条；按客户端视角（since=序号-1）拿到 %d 条" % (len(取回), len(客户端视角)))
except Exception as _异常:
    检查("清屏后新留言仍然取得到（序号只增不减，不回绕）", False,
       type(_异常).__name__ + "：" + str(_异常)[:60])

for 序号, (名字, 通过, 说明) in enumerate(结果, 1):
    print("  %2d. %s %s：%s" % (序号, "通过" if 通过 else "不过", 名字, 说明))
通过数 = sum(1 for _名, 通, _说 in 结果 if 通)
print()
print("通过 %d / 共 %d" % (通过数, len(结果)))
sys.exit(0 if 通过数 == len(结果) else 1)
