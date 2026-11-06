
import io
import os
import re
import sys

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)

from 地基 import 材料, 配置
from 能力 import 读图片
import 能力.批量看图片 as 批

过, 失败 = [], []


def 记(条件, 说明):
    (过 if 条件 else 失败).append(说明)


表 = {"P01.jpg": "P01", "P97.jpg": "P97", "IMG_0031.png": "0031",
      "a1b22.jpg": "b22", "照片.jpg": "007"}
坏 = [名 for 名, 期望 in 表.items() if 批._编号(名, 7 if 名 == "照片.jpg" else 1) != 期望]
记(not 坏, "① 编号取自文件名（不等：%s）" % (坏 or "无"))
记(批._编号("照片.jpg", 7) == "007", "① 文件名没数字时退回三位序号（%s）" % 批._编号("照片.jpg", 7))

好相对 = 批._找目录("肖泽云-语文")
好绝对 = 批._找目录(os.path.abspath(os.path.join("材料", "肖泽云-语文")))
记(好相对 == 好绝对, "② 相对名与绝对路径解析到同一个目录")
拒了 = []
for 坏路径 in ("C:/Windows/System32", "..", ""):
    try:
        批._找目录(坏路径)
    except ValueError:
        拒了.append(坏路径)
记(len(拒了) == 3, "② 越界/空/上跳三种目录都被拒（拒了 %d 个）" % len(拒了))

原OCR = getattr(材料, "本机OCR", None)
被调OCR = {"次": 0}


def 炸OCR(*_甲, **_乙):
    被调OCR["次"] += 1
    raise AssertionError("批量识图不该走本机 OCR")


原处理 = 读图片.处理
收到 = []


def 假处理(路径="", 要求="", **其余):
    收到.append((路径, 要求))
    return {"文本": "【桩】%s" % os.path.basename(str(路径))}


材料.本机OCR = 炸OCR
读图片.处理 = 假处理
try:
    目录 = "肖泽云-语文"
    果 = 批.处理(目录=目录, 最多=2, 输出名="自检-批量识图")
finally:
    读图片.处理 = 原处理
    if 原OCR is not None:
        材料.本机OCR = 原OCR

记(被调OCR["次"] == 0, "③ 全程没有调用本机 OCR（调用 %d 次）" % 被调OCR["次"])
记(len(收到) == 2, "③ 视觉模型被调了 2 次（收到 %d 次）" % len(收到))
记(all(os.path.isabs(路) for 路, _ in 收到), "③ 交给视觉模型的是绝对路径（不靠 cwd 猜）")

文 = io.open(果["文件"], encoding="utf-8").read()
编号们 = re.findall(r"^## ([A-Za-z0-9]+)（", 文, re.M)
记(编号们 == ["P01", "P02"], "④ 小节以编号为键（拿到 %s）" % 编号们)
记("P01.jpg" in 文, "④ 小节标题里留了源文件名（便于回查）")
第二行 = 文.split(chr(10))[1] if chr(10) in 文 else ""
记(第二行.strip() == "XR: C", "④ 文件第 2 行是 XR: C（%r）" % 第二行)
记("不经过本机 OCR" in 文, "④ 文件里写明了识别方式（视觉模型、不走 OCR）")

真编号 = 批._编号
批._编号 = lambda 名, 序: "X"
try:
    假果 = 批.处理(目录=目录, 最多=2, 输出名="自检-批量识图-反向")
    假文 = io.open(假果["文件"], encoding="utf-8").read()
    假编号们 = re.findall(r"^## ([A-Za-z0-9]+)（", 假文, re.M)
finally:
    批._编号 = 真编号

记(假编号们 != ["P01", "P02"], "⑤ 反向验：编号函数被换掉后判据确实变红（%s）" % 假编号们)

for 路 in (果.get("文件"), 假果.get("文件") if "假果" in dir() else None):
    if 路 and os.path.isfile(路):
        os.remove(路)

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
