
import os
import time

from 地基 import 大模型, 图片, 提示词, 注册表, 审计


def _临时落点(原名):
    根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    目录 = os.path.join(根, "材料", "_读图临时")
    os.makedirs(目录, exist_ok=True)
    净 = "".join(ch for ch in os.path.basename(str(原名)) if ch not in '\\/:*?"<>| ')
    return os.path.join(目录, (净 or "图") + ".jpg")


def 处理(路径="", 要求=""):
    路径 = str(路径 or "").strip()
    要求 = str(要求 or "").strip() or "把图里的内容完整读出来，保留原有的题号、勾选与手写。"
    尝试 = {"要求字数": len(要求)}
    开始 = time.time()

    if not 路径:
        raise ValueError("要读哪张图？给我图片路径（可以放在 材料/ 里，也可以给绝对路径）")
    if not os.path.isfile(路径):
        from 地基 import 材料 as _材料
        候选们 = []
        try:
            候选们.append(_材料.材料路径(路径))
        except Exception:
            pass
        命中 = next((c for c in 候选们 if os.path.isfile(c)), None)
        if not 命中:
            要 = os.path.basename(路径)
            for 目录, 子们, 文件们 in os.walk(os.path.join(os.getcwd(), "材料")):
                if 要 in 文件们:
                    命中 = os.path.join(目录, 要)
                    break
                if 目录.count(os.sep) - os.path.join(os.getcwd(), "材料").count(os.sep) >= 2:
                    子们[:] = []
        if not 命中:
            raise ValueError("这张图不在了：%s（放在 材料/ 下面，或给绝对路径）"
                             % os.path.basename(路径))
        路径 = 命中

    目标 = _临时落点(路径)
    try:
        果 = 图片.预处理(路径, 目标)
        if not 果["ok"]:
            审计.记一笔("读图片", 尝试, 成功=False, 秒数=time.time() - 开始,
                        备注="预处理失败")
            raise ValueError(果["错误"])
        try:
            提示 = 提示词.填充(提示词.读取("读图片"), 要求=要求)
            文本 = 大模型.问(大模型.拼内容(提示, 图=[目标]), 随机度=0.0)
        except ValueError:
            raise
        except Exception as 异常:
            审计.记一笔("读图片", 尝试, 成功=False, 秒数=time.time() - 开始,
                        备注=type(异常).__name__)
            raise RuntimeError("读图失败：" + type(异常).__name__ + "（" + str(异常)[:80] + "）") from None
    finally:
        目录 = os.path.dirname(目标)
        try:
            if os.path.isdir(目录) and not os.listdir(目录):
                os.rmdir(目录)
        except OSError:
            pass
        if os.path.isfile(目标):
            try:
                os.remove(目标)
            except OSError:
                pass

    审计.记一笔("读图片", 尝试, 成功=True, 秒数=time.time() - 开始)
    return {"文本": 文本,
            "图片": {"原尺寸": 果["原尺寸"], "新尺寸": 果["新尺寸"],
                   "原字节": 果["原字节"], "新字节": 果["新字节"]}}


注册表.登记(
    代号="读图片",
    标题="读图片",
    说明="把一张图片（教材页、手写问卷、练习卷）交给视觉模型读成文字。"
         "手写内容比本机 OCR 准；图会先缩到长边 1600 再发，原图不动。",
    参数=[
        {"代号": "路径", "标签": "图片路径（材料/ 里或绝对路径）", "类型": "text", "必填": True,
         "示例": "材料/问卷照片/IMG_0001.jpg"},
        {"代号": "要求", "标签": "要它读什么（默认整页照读）", "类型": "text", "必填": False,
         "示例": "按题号列出勾选项与手写内容，输出 JSON"},
    ],
    处理函数=处理,
)
