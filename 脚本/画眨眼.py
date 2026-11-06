
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

左带默认 = (152, 160, 222, 205)
右带默认 = (228, 160, 298, 205)
最少暗像素 = 90
至少降幅 = 0.45


def 解析带(文本):
    if not 文本:
        return 左带默认, 右带默认
    try:
        组们 = [[int(v) for v in 段.split(",")] for 段 in 文本.split(";") if 段.strip()]
    except ValueError:
        raise SystemExit("--参数 要写成 左4个数;右4个数，例如 152,160,222,205;228,160,298,205")
    if len(组们) != 2 or any(len(g) != 4 for g in 组们):
        raise SystemExit("--参数 要两个框、每框四个整数")
    for x0, y0, x1, y1 in 组们:
        if x1 <= x0 or y1 <= y0:
            raise SystemExit("框的右下角要大于左上角，现在是 %d,%d,%d,%d" % (x0, y0, x1, y1))
    return tuple(组们[0]), tuple(组们[1])


def 暗像素数(图, 带):
    甲 = np.asarray(图.crop(带)).astype(int)
    return int((甲.mean(axis=2) < 110).sum())


def 暗重心(图, 带):
    甲 = np.asarray(图.crop(带)).astype(int)
    暗 = 甲.mean(axis=2) < 110
    ys, xs = np.where(暗)
    if not len(xs):
        return None
    return float(xs.mean()), float(ys.mean())


def 取样色(带图):
    平 = 带图.reshape(-1, 3)
    亮 = 平[平.mean(axis=1) > 170]
    暗 = 平[平.mean(axis=1) < 95]
    if len(亮) < 20 or len(暗) < 20:
        raise SystemExit("这条带里分不出肤色和睫毛色，坐标大概给偏了")
    return (np.median(亮, axis=0).round().astype(np.uint8),
            np.median(暗, axis=0).round().astype(np.uint8))


def 眼球列(带图):
    暗 = (带图.mean(axis=2) < 110)
    列和 = 暗.sum(axis=0)
    有 = np.where(列和 > max(2, 带图.shape[0] // 8))[0]
    if not len(有):
        return 0, 带图.shape[1]
    左, 右 = int(有.min()), int(有.max())
    ys, xs = np.where(暗)
    重心 = float(xs.mean()) if len(xs) else (左 + 右) / 2.0
    半 = max((右 - 左) / 2.0, 3)
    左 = int(max(0, round(重心 - 半)))
    右 = int(min(带图.shape[1], round(重心 + 半)))
    return 左, 右


def 眼球行(带图):
    暗 = (带图.mean(axis=2) < 110).sum(axis=1)
    有 = np.where(暗 > max(2, 带图.shape[1] // 12))[0]
    if not len(有):
        raise SystemExit("这条带里没找到眼球")
    return int(max(0, 有.min() - 1)), int(min(带图.shape[0], 有.max() + 2))


def 造带(图, 带, 模式, 比):
    带图 = np.asarray(图.crop(带)).astype(np.uint8)
    高, 宽 = 带图.shape[0], 带图.shape[1]
    肤, 睫 = 取样色(带图)
    上, 下 = 眼球行(带图)
    底 = np.tile(肤, (高, 宽, 1)).astype(np.uint8)
    底[:上] = 带图[:上]
    底[下:] = 带图[下:]
    def 找肤色行(起, 方向):
        y = 起
        while 0 <= y < 高:
            if 带图[y].mean() > 165:
                return 带图[y].astype(float)
            y += 方向
        return 肤.astype(float)
    顶行 = 找肤色行(上 - 1, -1)
    底行 = 找肤色行(下 + 1, 1)
    行数 = 下 - 上
    for i in range(行数):
        权重 = (i + 1) / float(行数 + 1)
        底[上 + i] = (顶行 * (1 - 权重) + 底行 * 权重).round().astype(np.uint8)

    if 模式 == "压":
        可见 = max(1, int(round((下 - 上) * 比)))
        底[上:上 + 可见] = 带图[上:上 + 可见]
        中 = 上 + 可见
        左列, 右列 = 眼球列(带图)
        大 = Image.new("RGB", (宽 * 4, 高 * 4), (255, 255, 255))
        画 = ImageDraw.Draw(大)
        半宽 = max(1.0, (右列 - 左列) / 2.0)
        点们 = []
        for i in range(左列 * 4, 右列 * 4):
            x = i / 4.0
            相位 = (x - (左列 + 右列) / 2.0) / 半宽
            点们.append((i, 中 * 4 + int(round((1 - 相位 * 相位) * 1.4 * 4))))
        画.line(点们, fill=tuple(int(v) for v in 睫), width=2 * 4, joint="curve")
        线甲 = np.asarray(大.resize((宽, 高), Image.LANCZOS))
        深 = 线甲.mean(axis=2) < 150
        底[深] = 线甲[深]
    else:
        左列, 右列 = 眼球列(带图)
        大 = Image.new("RGB", (宽 * 4, 高 * 4), (255, 255, 255))
        画 = ImageDraw.Draw(大)
        中 = (上 + 下) // 2
        半宽 = max(1.0, (右列 - 左列) / 2.0)
        点们 = []
        for i in range(左列 * 4, 右列 * 4):
            x = i / 4.0
            相位 = (x - (左列 + 右列) / 2.0) / 半宽
            弯 = int(round((1 - 相位 * 相位) * 2.0 * 4))
            点们.append((i, 中 * 4 + 弯))
        画.line(点们, fill=tuple(int(v) for v in 睫), width=3 * 4, joint="curve")
        线 = 大.resize((宽, 高), Image.LANCZOS)
        线甲 = np.asarray(线)
        深 = 线甲.mean(axis=2) < 150
        底[深] = 线甲[深]
    return Image.fromarray(底)


def 主():
    解 = argparse.ArgumentParser()
    解.add_argument("--参数", default="")
    解.add_argument("--输入", default="", help="对哪张图做眨眼；默认是母图")
    解.add_argument("--前缀", default="", help="产物名前缀，例如 开心-")
    解.add_argument("--漂移上限", type=float, default=1.5,
                    help="重心允许漂多少像素；表情图眼睛本身不对称，可以放宽")
    参 = 解.parse_args()

    目录 = os.path.join(os.environ.get("AVATAR_HOME", ""), "母图")
    母路 = 参.输入 or os.path.join(目录, "定版-白底-1024.png")
    if not os.path.isfile(母路):
        raise SystemExit("找不到母图：" + 母路)
    左, 右 = 解析带(参.参数)

    母 = Image.open(母路).convert("RGB")
    for 名, 带 in (("左", 左), ("右", 右)):
        if 带[2] > 母.width or 带[3] > 母.height:
            raise SystemExit("%s眼框超出图像范围：%s" % (名, 带))
        数 = 暗像素数(母, 带)
        if 数 < 最少暗像素:
            raise SystemExit("%s眼框里只有 %d 个暗像素，先量一遍坐标（现在 %s）" % (名, 数, 带))

    出目录 = os.path.join(目录, "部件")
    os.makedirs(出目录, exist_ok=True)
    原数 = 暗像素数(母, 左) + 暗像素数(母, 右)
    原心 = (暗重心(母, 左), 暗重心(母, 右))

    坏 = []
    for 比, 名, 要求降 in ((0.40, 参.前缀 + "半闭眼-绘制", 0.25), (0.30, 参.前缀 + "闭眼-绘制", 至少降幅)):
        合 = 母.copy()
        for 带 in (左, 右):
            块 = 造带(母, 带, "画" if 比 <= 0.35 else "压", 比)
            蒙 = Image.new("L", (带[2] - 带[0], 带[3] - 带[1]), 255)
            蒙 = 蒙.filter(ImageFilter.GaussianBlur(1))
            合.paste(块, (带[0], 带[1]), 蒙)

        路 = os.path.join(出目录, 名 + ".png")
        合.save(路)

        新数 = 暗像素数(合, 左) + 暗像素数(合, 右)
        降幅 = 1 - 新数 / max(1, 原数)
        新心 = (暗重心(合, 左), 暗重心(合, 右))
        漂移 = max(abs(新心[i][0] - 原心[i][0]) if (新心[i] and 原心[i]) else 99 for i in (0, 1))

        带外 = 0
        a = np.asarray(母).astype(int)
        b = np.asarray(合).astype(int)
        差 = np.abs(a - b).sum(axis=2)
        外 = np.ones(差.shape, bool)
        for x0, y0, x1, y1 in (左, 右):
            外[max(0, y0 - 2):y1 + 2, max(0, x0 - 2):x1 + 2] = False
        带外 = int((差[外] > 0).sum())

        合格 = 降幅 >= 要求降 and 漂移 <= 参.漂移上限 and 带外 == 0
        print("  %s %-10s 暗像素 %d → %d（降 %.0f%%）  重心漂移 %.1f px  带外改动 %d"
              % ("✓" if 合格 else "✗", 名, 原数, 新数, 100 * 降幅, 漂移, 带外))
        if not 合格:
            坏.append("%s：降幅 %.0f%%（要 %.0f%%）、漂移 %.1f、带外 %d"
                      % (名, 100 * 降幅, 100 * 要求降, 漂移, 带外))

    print("成 %d 张" % (2 - len(坏)))
    if 坏:
        print("不合格：" + "；".join(坏))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(主())
