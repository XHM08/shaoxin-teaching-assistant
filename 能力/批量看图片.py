
import io
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

from 地基 import 注册表, 配置

默认最多 = 20
硬上限 = 200
并发 = 4
默认要求 = "把这一页的内容完整读出来：有文字就抄文字（保留题号与勾选），没文字就描述画面在讲什么。"


def _根们():
    根们 = []
    for 名 in ("材料", "教师数据"):
        try:
            根们.append(os.path.normpath(配置.取目录(名)))
        except Exception:
            continue
    根们.append(os.path.normpath(os.path.join(os.getcwd(), "材料")))
    return 根们


def _找目录(目录):
    目录 = str(目录 or "").strip()
    if not 目录:
        raise ValueError("要给我一个目录名，例如「肖泽云-语文」，也可以给绝对路径")
    if os.path.isabs(目录):
        全 = os.path.normpath(目录)
        if not any(全 == 根 or 全.startswith(根 + os.sep) for 根 in _根们()):
            raise ValueError("绝对路径只认 材料/ 或 教师数据/ 下面的目录，现在给的是：%s" % 目录)
        if not os.path.isdir(全):
            raise ValueError("这个目录不存在：%s" % 目录)
        return 全
    目录 = 目录.strip("/\\")
    根 = os.path.normpath(os.path.join(os.getcwd(), "材料"))
    全 = os.path.normpath(os.path.join(根, 目录))
    if not 全.startswith(根):
        raise ValueError("只能读 材料/ 下面的目录，现在给的是：%s" % 目录)
    if not os.path.isdir(全):
        raise ValueError("材料/ 下面没有这个目录：%s" % 目录)
    return 全


编号式 = re.compile(r"([A-Za-z]*)(\d+)")


def _编号(文件名, 序号):
    命中们 = list(编号式.finditer(文件名))
    m = 命中们[-1] if 命中们 else None
    if m:
        前缀, 数字 = m.group(1), m.group(2)
        return 前缀 + ("%0" + str(len(数字)) + "d") % int(数字)
    return "%03d" % 序号


def _图们(全目录):
    后缀 = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
    名们 = sorted(n for n in os.listdir(全目录) if n.lower().endswith(后缀))
    return 名们


def 处理(目录="", 要求="", 最多="", 输出名=""):
    全目录 = _找目录(目录)
    要 = str(要求 or "").strip() or 默认要求
    try:
        限 = int(最多) if str(最多).strip() else 默认最多
    except (TypeError, ValueError):
        raise ValueError("「最多几张」要写整数")
    if 限 < 1:
        raise ValueError("「最多几张」不能小于 1")
    限 = min(限, 硬上限)

    名们 = _图们(全目录)
    if not 名们:
        return {"正文": "这个目录里没有图片（只认 jpg/png/bmp/webp）。", "张数": 0, "文件": ""}

    要做 = 名们[:限]
    from 能力 import 读图片

    结果们, 失败们 = [], []

    编号表 = {名: _编号(名, 序) for 序, 名 in enumerate(要做, 1)}
    def 看(名):
        try:
            果 = 读图片.处理(os.path.join(全目录, 名), 要)
            文本 = (果 or {}).get("文本") or ""
            return 名, 编号表[名], 文本.strip(), ""
        except Exception as 异常:
            return 名, 编号表[名], "", "%s：%s" % (type(异常).__name__, str(异常)[:80])

    起 = time.time()
    with ThreadPoolExecutor(max_workers=并发) as 池:
        for 名, 编, 文本, 错 in 池.map(看, 要做):
            if 错:
                失败们.append("%s（%s）" % (名, 错))
            else:
                结果们.append((编, 名, 文本))

    目录出 = os.path.join(os.getcwd(), "材料", "_批量识图")
    os.makedirs(目录出, exist_ok=True)
    名基 = str(输出名 or "").strip() or ("%s-%s" % (目录.strip("/\\").replace(os.sep, "-"),
                                                time.strftime("%Y%m%d-%H%M%S")))
    路 = os.path.join(目录出, 名基 + ".md")
    文 = ["# 批量识图：%s" % (输出名 or os.path.basename(全目录)), "XR: C", "",
          "以编号为键：每条的 ## 后面就是编号（取自文件名里的数字），括号里留源文件名便于回查。",
          "识别全部走视觉模型，不经过本机 OCR。",
          "",
          "- 要求：%s" % 要,
          "- 目录共 %d 张，本次看了 %d 张，成功 %d 张，失败 %d 张"
          % (len(名们), len(要做), len(结果们), len(失败们)),
          "- 用时 %.0f 秒，并发 %d" % (time.time() - 起, 并发), ""]
    for 编, 名, 文本 in 结果们:
        文 += ["## " + 编 + "（" + 名 + "）", "", 文本 or "（没读出内容）", ""]
    if 失败们:
        文 += ["## 失败清单", ""] + ["- " + 一 for 一 in 失败们] + [""]
    with io.open(路, "w", encoding="utf-8") as 文件:
        文件.write(chr(10).join(文) + chr(10))

    正文 = ("看完了 %d 张（目录里共 %d 张），成功 %d、失败 %d，用时 %.0f 秒。"
            "结果在 %s，用「读材料」读它就能拿到全部正文。"
            % (len(要做), len(名们), len(结果们), len(失败们), time.time() - 起, 路))
    if len(名们) > len(要做):
        正文 += "（本次只看了前 %d 张，要看更多就把「最多几张」调大，上限 %d）" % (限, 硬上限)
    return {"正文": 正文, "张数": len(要做), "成功": len(结果们),
            "失败": 失败们, "文件": 路, "目录总数": len(名们)}


注册表.登记(
    代号="批量看图片",
    标题="批量看图片",
    说明="把一个目录里的图片逐张交给视觉模型，结果合并成一份 markdown 落在 教师数据/批量识图/。",
    参数=[
        {"代号": "目录", "标签": "材料下的目录名（如 肖泽云-语文）", "类型": "text", "必填": True,
         "示例": "肖泽云-语文"},
        {"代号": "要求", "标签": "每张要它看什么（留空用默认：抄文字或描述画面）", "类型": "textarea",
         "必填": False, "示例": ""},
        {"代号": "最多", "标签": "最多看几张（默认 20，上限 200）", "类型": "number",
         "必填": False, "示例": 20},
        {"代号": "输出名", "标签": "输出文件名（留空自动按时间命名）", "类型": "text",
         "必填": False, "示例": ""},
    ],
    处理函数=处理,
)
