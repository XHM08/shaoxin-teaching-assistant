
import base64
import io
import json
import os
import shutil
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 审计, 大模型, 配置

原取目录 = 配置.取目录
原urlopen = urllib.request.urlopen
原记一笔 = 审计.记一笔
假KEY名 = "SELFTEST_FAKE_KEY_DO_NOT_SET"
临时 = tempfile.mkdtemp(prefix="大模型图片自检_")
材料 = os.path.join(临时, "材料")
参考 = os.path.join(临时, "参考资料")
外面 = os.path.join(临时, "外面")
结果 = []
跳过 = []


def 记(名字, 通过, 说明):
    结果.append((名字, bool(通过), 说明))


def 该拦(名字, 函数, 关键词表):
    try:
        值 = 函数()
    except Exception as 异常:
        消息 = str(异常)
        缺的 = [词 for 词 in 关键词表 if 词 not in 消息]
        if 缺的:
            记(名字, False, "拦是拦了，可理由是别的（缺关键词 " + "、".join(缺的) + "）：" + 消息[:100])
        else:
            记(名字, True, "已拦：" + 消息[:70])
        return
    记(名字, False, "没拦住，放过去了：" + str(值)[:70])


def 该放(名字, 函数, 断言=None):
    try:
        值 = 函数()
    except Exception as 异常:
        记(名字, False, "不该出错却出错：" + type(异常).__name__ + "：" + str(异常)[:100])
        return
    if 断言 is None:
        记(名字, True, "放行")
        return
    try:
        说明 = 断言(值)
        记(名字, True, 说明 or "放行")
    except AssertionError as 异常:
        记(名字, False, "断言不过：" + str(异常)[:100])


def 该成(名字, 函数):
    try:
        记(名字, True, 函数() or "通过")
    except AssertionError as 异常:
        记(名字, False, "断言不过：" + str(异常)[:100])
    except Exception as 异常:
        记(名字, False, "意外出错：" + type(异常).__name__ + "：" + str(异常)[:100])


def 造图(名字, 边长=48, 补到字节=0, 在哪=None):
    从 = os.path.join(在哪 or 材料, 名字)
    有PIL = True
    try:
        from PIL import Image
        Image.new("RGB", (边长, 100 if 边长 > 200 else 边长), (200, 40, 40)).save(从, format="JPEG")
    except ImportError:
        有PIL = False
        with open(从, "wb") as 文件:
            文件.write(b"\xff\xd8\xff" + b"\0" * 200)
    if 补到字节 and os.path.getsize(从) < 补到字节:
        with open(从, "ab") as 文件:
            文件.write(b"\0" * (补到字节 - os.path.getsize(从)))
    return 从, 有PIL


os.makedirs(材料)
os.makedirs(参考)
os.makedirs(外面)
配置.取目录 = lambda 名: {"材料": 材料, "参考资料": 参考}.get(名) or 原取目录(名)

好图, 有PIL = 造图("讲义插图.jpg")
参考图, _ = 造图("参考图.png", 在哪=参考)
目录当图 = os.path.join(材料, "子目录")
os.makedirs(目录当图)
坏格式 = os.path.join(材料, "板书.bmp")
with open(坏格式, "wb") as 文件:
    文件.write(b"BM" + b"\0" * 100)
胖图 = [造图("胖%d.jpg" % 序, 补到字节=7 * 1024 * 1024)[0] for 序 in range(4)]
单张大, _ = 造图("大图.jpg", 补到字节=12 * 1024 * 1024)
长条, _ = 造图("长条.jpg", 边长=8200)
假图 = os.path.join(材料, "这其实是个目录.jpg")
os.makedirs(假图)
配置路径 = os.path.join(临时, "服务商.json")
with open(配置路径, "w", encoding="utf-8") as 文件:
    json.dump({
        "default": "能看图的",
        "providers": {
            "能看图的": {"base_url": "https://例子.invalid", "model": "看图的模型",
                       "key_env": 假KEY名, "支持图片": True},
            "纯文本的": {"base_url": "https://例子.invalid", "model": "纯文本模型",
                       "key_env": "自检用的另一个KEY"},
        },
    }, 文件, ensure_ascii=False)


def 验无图(值):
    assert isinstance(值, str), "无图时不是纯字符串：%r" % (值,)
    assert 值 == "你好", "无图时内容变了：%r" % (值,)
    return "与原文逐字相同（不打扰已有的缓存命中）"


def 验一块(值):
    assert isinstance(值, list), "没变成块数组：%r" % (值,)
    assert len(值) == 2, "块数不对：%d" % len(值)
    assert 值[0] == {"type": "text", "text": "看图"}, "文本块不对：%r" % (值[0],)
    assert 值[1]["type"] == "image_url", "第二块不是图"
    地址 = 值[1]["image_url"]["url"]
    assert 地址.startswith("data:image/jpeg;base64,"), "前缀不对：" + 地址[:30]
    with open(好图, "rb") as 文件:
        原字节 = 文件.read()
    assert base64.b64decode(地址.split(",", 1)[1]) == 原字节, "解回来跟原文件不一样"
    return "两块；data 地址 %d 字，解回来与原文件逐字节相同" % len(地址)


def 验元组(值):
    assert isinstance(值, list) and len(值) == 2, "不认元组：%r" % (值,)
    return "块数=2"


def 验报错不带路径():
    try:
        大模型.拼内容("看图", [os.path.join(外面, "照片.jpg")])
    except ValueError as 异常:
        消息 = str(异常)
        assert 临时 not in 消息, "报错里带上了本地临时路径：" + 消息
        assert 外面 not in 消息, "报错里带上了那个目录：" + 消息
        assert "照片.jpg" in 消息, "报错里没给文件名，老师不知道是哪张：" + 消息
        return "只给了文件名：" + 消息[:50]
    raise AssertionError("没拦住")


def 验缩(值):
    assert isinstance(值, list) and len(值) == 2, "没出块"
    地址 = 值[1]["image_url"]["url"]
    assert 地址.startswith("data:image/jpeg;base64,"), "缩完类型不对：" + 地址[:30]
    字节 = base64.b64decode(地址.split(",", 1)[1])
    原大小 = os.path.getsize(单张大)
    assert len(字节) < 原大小, "没缩小（%d 对 %d）" % (len(字节), 原大小)
    assert len(字节) <= 大模型.单张图上限, "缩完还是超上限"
    return "缩到 %.1f MB（原 %.1f MB）" % (len(字节) / 1048576, 原大小 / 1048576)


def 验边长(值):
    from PIL import Image
    字节 = base64.b64decode(值[1]["image_url"]["url"].split(",", 1)[1])
    with Image.open(io.BytesIO(字节)) as 图:
        长边 = max(图.size)
    assert 长边 <= 大模型.缩放后边长, "长边还是 %d" % 长边
    return "长边缩到 %d px（原 8200）" % 长边


class 假响应:
    def __init__(self, 数据):
        self._数据 = 数据

    def read(self):
        return self._数据

    def __enter__(self):
        return self

    def __exit__(self, *异常):
        return False


收到 = []
收到请求 = []


def 假urlopen(请求, timeout=None):
    收到请求.append(请求)
    return 假响应(json.dumps({
        "choices": [{"message": {"content": "看到了一张红色方块"}}],
        "usage": {"prompt_tokens": 1234, "completion_tokens": 56,
                  "prompt_tokens_details": {"cached_tokens": 1000}},
    }, ensure_ascii=False).encode("utf-8"))


def 验请求体():
    assert len(收到请求) == 1, "没发出请求"
    体 = json.loads(收到请求[0].data.decode("utf-8"))
    块 = 体["messages"][0]["content"]
    assert isinstance(块, list) and len(块) == 2, "发出去的 content 不是两块：%r" % (块,)
    assert 体["messages"][0]["role"] == "user", "图片必须放在 user 消息里（官方要求）"
    assert 块[0]["type"] == "text" and 块[0]["text"] == "这张图讲什么", "文本块不对"
    assert 块[1]["image_url"]["url"].startswith("data:image/jpeg;base64,"), "图块不对"
    return "content = [text, image_url] 两块，role=user"


def 验审计():
    找到 = [内容 for 类别, 内容 in 收到 if 类别 == "模型调用"]
    assert 找到, "没记审计"
    条目 = 找到[-1]
    assert 条目.get("图片张数") == 1, "审计没记图片张数：%r" % (条目,)
    assert 条目.get("输入token") == 1234, "token 没记上：%r" % (条目,)
    文本 = json.dumps(条目, ensure_ascii=False)
    assert "讲义插图" not in 文本, "审计里带了图片文件名（文件名可能就带学生姓名）：" + 文本
    return "记了图片张数=1，且不含文件名"


def 验假回复(值):
    assert 值 == 大模型.假回复, "不是假回复"
    return "返回演示回复，没碰图片校验"


try:
    该放("① 无图 → 仍是纯字符串", lambda: 大模型.拼内容("你好"), 验无图)
    该放("② 一张图 → 文本块+图块，且能解回原图", lambda: 大模型.拼内容("看图", [好图]), 验一块)
    该放("③ 图=[] → 仍是纯字符串", lambda: 大模型.拼内容("你好", []), 验无图)
    该拦("④ 图传字符串 → 拦，理由要是那条契约", lambda: 大模型.拼内容("看图", 好图),
         ["列表", "不能传单个字符串"])
    该放("⑤ 图传元组 → 放行", lambda: 大模型.拼内容("看图", (好图,)), 验元组)
    该拦("⑥ 9 张 → 拦，理由要是张数", lambda: 大模型.拼内容("看图", [好图] * 9), ["一次最多发"])
    该拦("⑦ 参考目录之外的图 → 拦", lambda: 大模型.拼内容("看图", [os.path.join(外面, "x.jpg")]),
         ["不能发"])
    该拦("⑧ 路径是个目录 → 拦", lambda: 大模型.拼内容("看图", [目录当图]), ["不能发"])
    该拦("⑨ 文件不存在 → 拦", lambda: 大模型.拼内容("看图", [os.path.join(材料, "没有这张.jpg")]),
         ["不能发"])
    该拦("⑩ .bmp → 拦，理由要是格式", lambda: 大模型.拼内容("看图", [坏格式]),
         ["格式不能发给模型"])
    该成("⑪ 报错只带文件名、不带本地路径", 验报错不带路径)
    该放("⑫ 参考资料/ 下的图 → 放行", lambda: 大模型.拼内容("看图", [参考图]), 验元组)
    该拦("⑬ 4×7MB 累计超限 → 拦，理由要是累计",
         lambda: 大模型.拼内容("看图", 胖图), ["已计入", "超过一次能发"])
    if not 有PIL:
        跳过.append(("⑭ 单张 12MB 自动缩小", "这台电脑没装 Pillow，缩不了（代码会给一句人话提示）"))
        跳过.append(("⑮ 边长 8200px 自动缩小", "同上"))
    else:
        该放("⑭ 单张 12MB → 自动缩小", lambda: 大模型.拼内容("看图", [单张大]), 验缩)
        该放("⑮ 边长 8200px → 自动缩小", lambda: 大模型.拼内容("看图", [长条]), 验边长)

    该拦("⑯ 服务商没标支持图片 → 拦，且不需要密钥",
         lambda: 大模型.问("看图", 服务商="纯文本的", 图=[好图], 配置文件路径=配置路径),
         ["没标「支持图片」", "纯文本的"])
    该拦("⑰ 标了支持图片但没密钥 → 报的是密钥（说明它过了闸门）",
         lambda: 大模型.问("看图", 服务商="能看图的", 图=[好图], 配置文件路径=配置路径),
         ["没找到", "Key"])
    def 验支持图():
        断言表 = [({}, False), ({"支持图片": True}, True), ({"支持图片": "true"}, False),
                 ({"支持图片": False}, False), (None, False)]
        for 条目, 期望 in 断言表:
            实际 = 大模型.服务商支持图(条目)
            assert 实际 == 期望, "服务商支持图(%r) = %r，期望 %r" % (条目, 实际, 期望)
        return "5 组都对（写 true 才算，写字符串/缺省都当不支持）"
    该成("⑱ 服务商支持图 只有显式 true 才算", 验支持图)

    os.environ[假KEY名] = "自检用的假密钥"
    urllib.request.urlopen = 假urlopen
    审计.记一笔 = lambda 类别, 内容, **其余: 收到.append((类别, dict(内容)))
    该放("⑲ 全链路（替身）带图问一次成功",
         lambda: 大模型.问("这张图讲什么", 服务商="能看图的", 图=[好图], 配置文件路径=配置路径),
         lambda 值: "回答：" + str(值)[:20])
    该成("⑳ 真发出去的请求体形状对", 验请求体)
    该成("㉑ 审计记了发几张图、但不记文件名", 验审计)

    def 验读不出来():
        真判断 = 大模型.图片能发吗
        大模型.图片能发吗 = lambda 路径: True
        try:
            大模型.拼内容("看图", [假图])
        except ValueError as 异常:
            assert "读不出来" in str(异常), "报的不是「读不出来」：" + str(异常)[:80]
            return "OSError 被接成人话：" + str(异常)[:44]
        except Exception as 异常:
            raise AssertionError("抛的不是 ValueError 而是 %s。界面上会变成 500：%s"
                                 % (type(异常).__name__, str(异常)[:60]))
        finally:
            大模型.图片能发吗 = 真判断
        raise AssertionError("没拦住")
    该成("㉓ open() 抛 OSError → 接成人话而不是 500", 验读不出来)

    该放("㉔ 假模式不碰图片校验",
         lambda: 大模型.问("看图", 图=[os.path.join(外面, "x.jpg")], 假模式=True), 验假回复)

    def 验带标签():
        块 = 大模型.拼内容("看图", [("文件名：讲义插图.jpg", 好图)])
        assert isinstance(块, list) and len(块) == 3, "块数不对：%r" % (块 if not isinstance(块, list) else len(块),)
        assert 块[0]["type"] == "text" and 块[0]["text"] == "看图", "第一块该是提示词"
        assert 块[1] == {"type": "text", "text": "文件名：讲义插图.jpg"}, "标签块不对：%r" % (块[1],)
        assert 块[2]["type"] == "image_url", "第三块该是图"
        return "3 块：提示词 / 标签 / 图，标签逐字保留"
    该成("㉕ (标签, 图) 成对发 → 标签块紧挨在图块之前", 验带标签)

    def 验审计带标签():
        收到.clear()
        收到请求.clear()
        大模型.问("这张图讲什么", 服务商="能看图的",
                图=[("文件名：讲义插图.jpg", 好图)], 配置文件路径=配置路径)
        assert len(收到请求) == 1, "没发出请求"
        块 = json.loads(收到请求[0].data.decode("utf-8"))["messages"][0]["content"]
        assert len(块) == 3 and 块[1]["text"].startswith("文件名："), "标签没发出去：%r" % (块,)
        条目 = [内容 for 类别, 内容 in 收到 if 类别 == "模型调用"][-1]
        assert 条目.get("图片张数") == 1, "审计把 1 张记成了 %r" % (条目.get("图片张数"),)
        return "请求体 3 块，审计记图片张数=1"
    该成("㉖ 带标签时审计仍记 1 张（不能按块数反推）", 验审计带标签)
finally:
    配置.取目录 = 原取目录
    urllib.request.urlopen = 原urlopen
    审计.记一笔 = 原记一笔
    if 假KEY名 in os.environ:
        del os.environ[假KEY名]
    shutil.rmtree(临时, ignore_errors=True)

for 序号, (名字, 通过, 说明) in enumerate(结果, 1):
    print("  %2d. %s %s：%s" % (序号, "通过" if 通过 else "不过", 名字, 说明))
for 名字, 原因 in 跳过:
    print("     跳过 %s：%s" % (名字, 原因))

try:
    大模型.取密钥("自检-非法名", {"key_env": "../x"})
    记("key_env 不像环境变量名就直接拒（防被拼成 密钥/ 之外的路径）", False, "居然放过了")
except RuntimeError as _异常:
    记("key_env 不像环境变量名就直接拒（防被拼成 密钥/ 之外的路径）",
      "不像环境变量名" in str(_异常), str(_异常)[:70])

通过数 = sum(1 for _名, 通, _说 in 结果 if 通)
尾巴 = ("，" + str(len(跳过)) + " 项跳过") if 跳过 else ""
print("\n%d/%d%s" % (通过数, len(结果), 尾巴))
if 通过数 < len(结果):
    sys.exit(1)
sys.exit(3 if 跳过 else 0)
