
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

颈 = (219, 218)
腰 = (219, 500)
脚底 = (219, 986)
颈线 = 225
腰线 = 508
留边 = 16


def 载(路, 高):
    图 = Image.open(路).convert("RGB")
    比 = 高 / float(图.height)
    return 图.resize((max(1, int(round(图.width * 比))), 高), Image.LANCZOS)


def 转身段(母, 支点, 线, 角度, 羽化=5):
    旋 = 母.rotate(角度, resample=Image.BICUBIC, center=支点, fillcolor=(253, 253, 253))
    蒙 = Image.new("L", 母.size, 0)
    ImageDraw.Draw(蒙).rectangle((0, 0, 母.width, 线), fill=255)
    蒙 = 蒙.filter(ImageFilter.GaussianBlur(羽化))
    出 = 母.copy()
    出.paste(旋, (0, 0), 蒙)
    return 出


def 转全身(母, 角度, 缩放=1.0):
    旋 = 母.rotate(角度, resample=Image.BICUBIC, center=脚底, fillcolor=(253, 253, 253))
    if 缩放 != 1.0:
        宽, 高 = 旋.size
        内 = 旋.resize((int(宽 * 缩放), int(高 * 缩放)), Image.LANCZOS)
        底 = Image.new("RGB", (宽, 高), (253, 253, 253))
        底.paste(内, ((宽 - 内.width) // 2, 高 - 内.height))
        旋 = 底
    return 旋


def 上下(母, 位移, 挤压=1.0):
    甲 = 母
    if 挤压 != 1.0:
        宽, 高 = 甲.size
        内 = 甲.resize((宽, max(1, int(高 * 挤压))), Image.LANCZOS)
        底 = Image.new("RGB", (宽, 高), (253, 253, 253))
        底.paste(内, (0, 高 - 内.height))
        甲 = 底
    底 = Image.new("RGB", 甲.size, (253, 253, 253))
    底.paste(甲, (0, 位移))
    return 底


def 颜色集合(图):
    甲 = np.asarray(图.convert("RGB")).reshape(-1, 3)
    return {tuple(v) for v in np.unique(甲, axis=0)}


def 核(母, 帧, 线=None):
    a = np.asarray(母).astype(int)
    b = np.asarray(帧).astype(int)
    差 = np.abs(a - b).sum(axis=2)
    动过 = int((差 > 0).sum())
    下改 = int((差[线 + 留边:, :] > 0).sum()) if 线 else 0
    return 动过, 下改


def 加透明(帧们):
    import importlib.util
    规 = importlib.util.spec_from_file_location("透明化", os.path.join(根, "脚本", "透明化.py"))
    模 = importlib.util.module_from_spec(规)
    规.loader.exec_module(模)
    return [模.抠图(图) for 图 in 帧们]


def 写(帧序, 目录, 名):
    图们 = [g for g, _ in 帧序]
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


def 主():
    解 = argparse.ArgumentParser()
    解.add_argument("--高", type=int, default=512)
    参 = 解.parse_args()

    目录 = os.path.join(os.environ.get("AVATAR_HOME", ""), "母图")
    母路 = os.path.join(目录, "定版-白底-1024.png")
    if not os.path.isfile(母路):
        raise SystemExit("找不到母图（先设 AVATAR_HOME）")
    出 = os.path.join(目录, "动作")
    os.makedirs(出, exist_ok=True)

    原高 = Image.open(母路).height
    母 = 载(母路, 参.高)
    比 = 参.高 / float(原高)
    global 颈, 腰, 脚底, 颈线, 腰线
    颈 = (int(颈[0] * 比), int(颈[1] * 比))
    腰 = (int(腰[0] * 比), int(腰[1] * 比))
    脚底 = (int(脚底[0] * 比), int(脚底[1] * 比))
    颈线 = int(颈线 * 比)
    腰线 = int(腰线 * 比)

    组 = {
        "点头": ([(母, 500), (转身段(母, 颈, 颈线, 4), 110), (转身段(母, 颈, 颈线, 8), 160),
                 (转身段(母, 颈, 颈线, 4), 110), (母, 260),
                 (转身段(母, 颈, 颈线, -3), 110), (母, 400)], 颈线),
        "鞠躬": ([(母, 500), (转身段(母, 腰, 腰线, 4), 180), (转身段(母, 腰, 腰线, 8), 280),
                 (转身段(母, 腰, 腰线, 8), 460), (转身段(母, 腰, 腰线, 4), 180), (母, 500)], 腰线),
        "跳跃": ([(母, 400), (上下(母, 0, 0.985), 110), (上下(母, -14), 130),
                 (上下(母, 0, 0.99), 110), (母, 500)], None),
        "摇摆": ([(转全身(母, -2.0), 700), (转全身(母, 0), 500), (转全身(母, 2.0), 700),
                 (转全身(母, 0), 500)], None),
    }

    坏 = []
    for 名, (帧序, 线) in 组.items():
        最多动, 最大下改 = 0, 0
        for 图, _ in 帧序:
            动过, 下改 = 核(母, 图, 线)
            最多动 = max(最多动, 动过)
            最大下改 = max(最大下改, 下改)
        大小 = 写(帧序, 出, 名)
        合格 = 最多动 > 0 and 最大下改 == 0
        print("  %s %-3s %d 帧  %4d KB  动过像素 %6d  保护线以下被改 %d"
              % ("✓" if 合格 else "✗", 名, len(帧序), 大小, 最多动, 最大下改))
        if not 合格:
            坏.append("%s：动过 %d、线下改动 %d" % (名, 最多动, 最大下改))

    print("成 %d 个" % (len(组) - len(坏)))
    if 坏:
        print("不合格：" + "；".join(坏))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(主())
