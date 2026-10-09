
import json
import uuid
import os
import time
import wave

from 地基 import 审计, 课件, 配置, 注册表, 语音

配音台账名 = "配音.json"

参数表 = [
    {"代号": "课件文件", "标签": "给哪份课件配音", "类型": "text", "必填": True,
     "示例": "例如：张老师-分数的除法.pptx"},
    {"代号": "语速", "标签": "语速（默认 1.0）", "类型": "text", "必填": False},
]

配音后缀 = "_配音"
最长语速 = 2.0
最慢语速 = 0.5
不要的说法 = ("不", "否", "no", "No", "不用", "不要", "skip")


def 要配音吗(值):
    return str(值 or "").strip() not in 不要的说法


def 能配音吗():
    if not 语音.服务在吗():
        return False, "语音服务没在跑（" + 语音.取地址() + "）—— 双击 语音/启动语音服务.bat 就有了"
    try:
        语音.取参考音()
    except Exception as 异常:
        return False, str(异常).splitlines()[0]
    return True, ""


def 取课件路径(名字):
    名字 = str(名字 or "").strip()
    if not 名字:
        raise ValueError("请填课件文件名（在 课件输出/ 里的那个 .pptx）")
    if os.path.basename(名字) != 名字 or "/" in 名字 or "\\" in 名字:
        raise ValueError("只填文件名就行，不要带目录：" + 名字)
    目录 = 配置.取目录("课件输出")
    路径 = os.path.join(目录, 名字)
    if not os.path.isfile(路径):
        现有 = []
        if os.path.isdir(目录):
            现有 = sorted(名 for 名 in os.listdir(目录) if 名.lower().endswith(".pptx"))
        raise ValueError(
            "课件输出/ 里没有这份课件：" + 名字
            + ("\n现有的是：" + "、".join(现有[:8]) if 现有 else
               "\n（课件输出/ 里还没有 .pptx —— 先去「PPT 生成」做一份）"))
    return 路径


def 取讲稿们(课件路径):
    return [(一页["页"], 一页["备注"]) for 一页 in 课件.读各页(课件路径)]


def 取配置语速():
    try:
        return 读语速(配置.读取().get("语音", {}).get("语速", "1.0"))
    except Exception:
        return 1.0


def 读语速(值):
    文本 = str(值 or "").strip() or "1.0"
    try:
        数 = float(文本)
    except ValueError:
        raise ValueError("语速要填数字（例如 1.0；越小越慢）：" + 文本) from None
    if not 最慢语速 <= 数 <= 最长语速:
        raise ValueError("语速只在 %.1f–%.1f 之间（这次填的是 %s）" % (最慢语速, 最长语速, 文本))
    return 数


def 读台账(输出目录):
    路径 = os.path.join(输出目录, 配音台账名)
    if not os.path.isfile(路径):
        return {}
    try:
        with open(路径, "r", encoding="utf-8") as 文件:
            return json.load(文件)
    except Exception:
        return {}


def 写台账(输出目录, 台账):
    路径 = os.path.join(输出目录, 配音台账名)
    临时 = 路径 + ".写中" + "." + uuid.uuid4().hex[:8]
    with open(临时, "w", encoding="utf-8") as 文件:
        json.dump(台账, 文件, ensure_ascii=False, indent=1)
    os.replace(临时, 路径)


def _量秒数(路径):
    try:
        with wave.open(路径, "rb") as 音频:
            return round(音频.getnframes() / float(音频.getframerate() or 1), 1)
    except Exception:
        return 0.0


def 合成整份(课件路径, 语速=1.0, 警告=None):
    参考音, 参考音文本 = 语音.取参考音()
    页们 = 课件.读各页(课件路径)
    有讲稿 = [一页 for 一页 in 页们 if 一页["备注"]]
    if not 有讲稿:
        raise ValueError("这份课件的每一页都没有讲稿（备注是空的）。"
                         "课件生成时每页都会写讲稿 —— 这份可能是别处来的。")

    课件名 = os.path.splitext(os.path.basename(课件路径))[0]
    目录名 = 课件名 + 配音后缀
    输出目录 = os.path.join(配置.取目录("课件输出"), 目录名)
    os.makedirs(输出目录, exist_ok=True)

    旧台账 = 读台账(输出目录)
    旧页 = 旧台账.get("页") or {}
    旧语速 = 旧台账.get("语速")
    新页 = {}
    条目 = {}
    复用, 重配, 只改了字 = [], [], []
    for 一页 in 有讲稿:
        号 = str(一页["页"])
        文件名 = "第" + 号 + "页.wav"
        路径 = os.path.join(输出目录, 文件名)
        备注印 = 课件.文本指纹(一页["备注"])
        文字印 = 课件.文本指纹(一页["文字"])
        旧这页 = 旧页.get(号) or {}
        能用旧 = (旧这页.get("备注指纹") == 备注印
                and 旧这页.get("文件") == 文件名
                and 旧语速 == 语速
                and os.path.isfile(路径))
        if 能用旧:
            复用.append(一页["页"])
        else:
            语音.合成到文件(一页["备注"], 路径, 参考音, 参考音文本, 语速=语速)
            重配.append(一页["页"])
        if 旧这页.get("文字指纹") and 旧这页["文字指纹"] != 文字印:
            只改了字.append(一页["页"])
        秒 = _量秒数(路径)
        新页[号] = {"备注指纹": 备注印, "文字指纹": 文字印,
                   "文件": 文件名, "秒数": 秒}
        条目[一页["页"]] = {"页": 一页["页"], "字数": len(一页["备注"]), "秒数": 秒,
                         "文件": 文件名, "音频": "/配音/" + 目录名 + "/" + 文件名}

    写台账(输出目录, {"课件指纹": 课件.指纹(课件路径), "语速": 语速, "页": 新页})

    空页 = [一页["页"] for 一页 in 页们 if not 一页["备注"]]
    if 空页:
        告一声(警告, "有 %d 页没有讲稿，跳过没配音（第 %s 页）"
                 % (len(空页), "、".join(str(x) for x in 空页)))
    if 重配 and 复用:
        告一声(警告, "讲稿改过的是第 %s 页，只重配了这几页；其余 %d 页沿用上次的配音"
                 % ("、".join(str(x) for x in 重配), len(复用)))
    elif 重配:
        告一声(警告, "这次新配了 %d 页" % len(重配))
    else:
        告一声(警告, "这 %d 页的配音与上次一样，一页都没重配" % len(复用))
    if 只改了字:
        告一声(警告, "第 %s 页的**页面文字**改了、但讲稿（备注）没动 —— "
                   "配音念的还是原来那段；要改讲稿就改那几页的备注"
                 % "、".join(str(x) for x in 只改了字))
    return 目录名, [条目[号] for 号 in sorted(条目)]


def 告一声(警告, 话):
    if isinstance(警告, list):
        警告.append(话)


def 处理(课件文件, 语速="1.0"):
    开始时刻 = time.time()
    路径 = 取课件路径(课件文件)
    速度 = 读语速(语速)
    警告 = []
    目录名, 条目 = 合成整份(路径, 速度, 警告)

    参考音, _ = 语音.取参考音()
    审计.记一笔("讲稿配音", {"课件": os.path.splitext(os.path.basename(路径))[0],
                       "合成页数": len(条目),
                       "字数": sum(条["字数"] for 条 in 条目)},
                成功=True, 秒数=time.time() - 开始时刻)

    提示 = ("配音好了：%d 页，共 %.1f 分钟，放在 课件输出/%s/ 里"
          % (len(条目), sum(条["秒数"] for 条 in 条目) / 60.0, 目录名))
    for 一句 in 警告:
        提示 += "；" + 一句
    return {
        "提示": 提示,
        "正文": "参考音：" + os.path.basename(参考音) + "（全程本机合成，没有上传）\n"
              + "语速：" + str(速度),
        "条目": 条目,
        "配音目录": 目录名,
    }


注册表.登记(
    代号="讲稿配音",
    标题="讲稿配音",
    说明="把课件里每页的讲稿合成本地语音（每页一个 wav，全部在本机跑，不上传）",
    参数=参数表,
    处理函数=处理,
)
