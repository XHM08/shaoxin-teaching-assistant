
import argparse
import io
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
眼框 = (168, 144, 266, 176)
嘴框 = (198, 184, 238, 206)
眉框 = (170, 136, 264, 150)
羽化 = 2


def 载(路, 目标高):
    if not os.path.isfile(路):
        return None
    图 = Image.open(路).convert("RGB")
    比 = 目标高 / float(图.height)
    return 图.resize((max(1, int(round(图.width * 比))), 目标高), Image.LANCZOS)


def 缩框(框, 原高, 新图):
    比 = 新图.height / float(原高)
    return tuple(int(round(v * 比)) for v in 框)


def 合(底, 层, 框):
    出 = 底.copy()
    蒙 = Image.new("L", 底.size, 0)
    ImageDraw.Draw(蒙).rectangle(框, fill=255)
    if 羽化:
        蒙 = 蒙.filter(ImageFilter.GaussianBlur(羽化))
    出.paste(层, (0, 0), 蒙)
    return 出


def 核(帧, 母, 框们, 边=8):
    a = np.asarray(母).astype(int)
    b = np.asarray(帧).astype(int)
    差 = np.abs(a - b).sum(axis=2)
    外 = np.ones(差.shape, bool)
    for x0, y0, x1, y1 in 框们:
        外[max(0, y0 - 边):y1 + 边, max(0, x0 - 边):x1 + 边] = False
    return int((差[外] > 0).sum()), int(差[外].max()), float(差[~外].mean())


def 加透明(帧们, 底色=(253, 253, 253)):
    import importlib.util
    规 = importlib.util.spec_from_file_location("透明化", os.path.join(根, "脚本", "透明化.py"))
    模 = importlib.util.module_from_spec(规)
    规.loader.exec_module(模)
    return [模.抠图(图, 容差=24) for 图 in 帧们]


def 写(帧序, 目录, 名):
    图们 = [图 for 图, _ in 帧序]
    时长 = [毫秒 for _, 毫秒 in 帧序]
    rgba = 加透明(图们)
    rgba[0].save(os.path.join(目录, 名 + ".webp"), save_all=True, append_images=rgba[1:],
                 duration=时长, loop=0, lossless=True, quality=100, method=6)
    白 = []
    for 图 in rgba:
        底 = Image.new("RGB", 图.size, (255, 255, 255))
        底.paste(图, (0, 0), 图)
        白.append(底)
    白[0].save(os.path.join(目录, 名 + ".gif"), save_all=True, append_images=白[1:],
               duration=时长, loop=0, disposal=2)
    return os.path.getsize(os.path.join(目录, 名 + ".webp")) // 1024


def 读时长(路):
    import struct
    数据 = open(路, "rb").read()
    i, 出 = 12, []
    while i + 8 <= len(数据):
        标, 长 = 数据[i:i+4], struct.unpack("<I", 数据[i+4:i+8])[0]
        if 标 == b"ANMF":
            体 = 数据[i+8:i+8+长]
            出.append(体[12] | (体[13] << 8) | (体[14] << 16))
        i += 8 + 长 + (长 & 1)
    return 出


def 主():
    解 = argparse.ArgumentParser()
    解.add_argument("--高", type=int, default=512)
    解.add_argument("--帧率", type=int, default=24)
    参 = 解.parse_args()

    目录 = os.path.join(os.environ.get("AVATAR_HOME", ""), "母图")
    if not os.path.isdir(目录):
        raise SystemExit("找不到母图目录（先设 AVATAR_HOME）")
    件 = os.path.join(目录, "部件")
    出 = os.path.join(目录, "动画2")
    os.makedirs(出, exist_ok=True)

    高 = 参.高
    原高 = Image.open(os.path.join(目录, "定版-白底-1024.png")).height
    母 = 载(os.path.join(目录, "定版-白底-1024.png"), 高)
    宽 = 母.width
    眼, 嘴, 眉 = 缩框(眼框, 原高, 母), 缩框(嘴框, 原高, 母), 缩框(眉框, 原高, 母)

    def 取(名):
        return 载(os.path.join(件, 名 + ".png"), 高)

    def 取眨眼(名):
        return 取(名 + "-绘制") or 取(名)
    闭, 半 = 取眨眼("闭眼"), 取眨眼("半闭眼")
    说 = [取("说话%d" % i) for i in (1, 2, 3)]
    if not (闭 and 半) or any(v is None for v in 说):
        raise SystemExit("缺部件帧：先跑 形象表情2.py")

    组 = {}
    闭帧, 半帧 = 合(母, 闭, 眼), 合(母, 半, 眼)
    组["待机"] = ([(母, 2200), (半帧, 60), (闭帧, 110), (半帧, 60), (母, 400)], [眼])

    说帧 = [(合(母, 说[i - 1], 嘴), 130) for i in (1, 2, 3, 2)]
    组["说话"] = (说帧, [嘴])

    眨 = {"微笑": True, "生气": True, "难过": True, "开心": True,
          "惊讶": True, "思考": True}
    眨层 = {名: (名 + "-半闭眼-绘制", 名 + "-闭眼-绘制") for 名 in ("开心", "惊讶", "思考")}
    for 名 in ("微笑", "开心", "生气", "难过", "惊讶", "思考"):
        层 = 取(名)
        if 层 is None:
            continue
        框们 = []
        基 = 母
        if 名 in ("开心", "惊讶"):
            基 = 合(基, 层, 眼)
            框们.append(眼)
        if 名 in ("生气", "难过"):
            基 = 合(基, 层, 眉)
            框们.append(眉)
        if 名 in ("微笑", "开心", "生气", "难过", "惊讶"):
            基 = 合(基, 层, 嘴)
            框们.append(嘴)
        if 名 == "思考":
            基 = 合(基, 层, 眼)
            框们.append(眼)
        if 眨[名]:
            半层, 闭层 = (取(眨层[名][0]), 取(眨层[名][1])) if 名 in 眨层 else (半, 闭)
            if 半层 is None or 闭层 is None:
                半层, 闭层 = 半, 闭
            组[名] = ([(基, 2200), (合(基, 半层, 眼), 60),
                       (合(基, 闭层, 眼), 110), (合(基, 半层, 眼), 60), (基, 400)],
                      框们 + [眼])
        else:
            组[名] = ([(基, 2400)], 框们)

    挥1, 挥2 = 取("挥手"), 取("挥手2")
    if 挥1 and 挥2:
        臂框 = 缩框((266, 300, 412, 592), 原高, 母)
        组["挥手"] = ([(母, 400), (挥1, 170), (挥2, 170), (挥1, 170),
                       (挥2, 170), (挥1, 170), (母, 400)], [臂框])

    for 姿, 框 in (("举手", (266, 300, 412, 592)), ("指向", (266, 300, 412, 592))):
        层 = 取(姿)
        if 层:
            框缩 = 缩框(框, 原高, 母)
            组[姿] = ([(母, 300), (层, 260), (层, 700), (母, 400)], [框缩])

    坏 = []
    for 名, (帧序, 框们) in 组.items():
        最大外 = 0
        for f, _ in 帧序:
            数, 极, _ = 核(f, 母, 框们)
            最大外 = max(最大外, 数)
        大小 = 写(帧序, 出, 名)
        时长 = 读时长(os.path.join(出, 名 + ".webp"))
        总 = sum(时长)
        print("  %-4s %d 帧  %4d KB  总时长 %.2f 秒  框外被改像素 %d  时长 %s"
              % (名, len(帧序), 大小, 总 / 1000.0, 最大外, 时长))
        if 最大外:
            坏.append("%s：框外被改了 %d 像素" % (名, 最大外))

    print("成 %d 个" % (len(组) - len(坏)))
    if 坏:
        print("失败：" + "；".join(坏))
    return 0 if not 坏 else 1


if __name__ == "__main__":
    sys.exit(主())
