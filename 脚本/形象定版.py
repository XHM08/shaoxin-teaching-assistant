
import argparse
import io
import json
import os
import sys

from PIL import Image
import numpy as np

边距比 = 0.06
透明阈值 = 20
透明上限 = 44


def 主体框(图):
    甲 = np.asarray(图).astype(int)
    角 = np.concatenate([甲[:10, :10].reshape(-1, 3), 甲[:10, -10:].reshape(-1, 3),
                         甲[-10:, :10].reshape(-1, 3), 甲[-10:, -10:].reshape(-1, 3)])
    底 = 角.mean(axis=0)
    人 = np.abs(甲 - 底).sum(axis=2) > 60
    行, 列 = np.where(人)
    if 行.size == 0:
        raise SystemExit("这张图里找不到主体：整幅都像背景")
    return int(列.min()), int(行.min()), int(列.max()), int(行.max()), 底


def 裁(图, 框, 留白比):
    左, 上, 右, 下, _ = 框
    高 = 下 - 上
    宽 = 右 - 左
    边 = int(max(宽, 高) * 留白比)
    外 = 3
    return (max(0, 左 - 边 - 外), max(0, 上 - 边 - 外),
            min(图.width, 右 + 边 + 外), min(图.height, 下 + 边 + 外))


def 缩到高(图, 目标高):
    比 = 目标高 / float(图.height)
    缩 = 图.resize((max(1, int(round(图.width * 比))), 目标高), Image.LANCZOS)
    补 = (-缩.width) % 8
    if not 补:
        return 缩
    出 = Image.new("RGB", (缩.width + 补, 缩.height), (255, 255, 255))
    出.paste(缩, (0, 0))
    return 出


def 透明化(图, 底, 羽化=1.2):
    from PIL import ImageFilter
    甲 = np.asarray(图.convert("RGB")).astype(int)
    差 = np.abs(甲 - np.array(底)).sum(axis=2).astype(float)
    下限 = float(透明阈值)
    上限 = float(透明上限)
    alpha = np.clip((差 - 下限) / max(1.0, 上限 - 下限), 0.0, 1.0)
    蒙 = Image.fromarray((alpha * 255).astype(np.uint8), mode="L")
    if 羽化:
        蒙 = 蒙.filter(ImageFilter.GaussianBlur(羽化))
    甲2 = 甲.clip(0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([甲2, np.asarray(蒙)]), mode="RGBA")


def 主():
    解 = argparse.ArgumentParser()
    解.add_argument("母图")
    解.add_argument("--出", default="")
    参 = 解.parse_args()
    if not os.path.isfile(参.母图):
        raise SystemExit("找不到母图：" + 参.母图)
    出目录 = 参.出 or os.path.join(os.path.dirname(os.path.abspath(参.母图)), "定版")
    os.makedirs(出目录, exist_ok=True)

    原 = Image.open(参.母图).convert("RGB")
    框 = 主体框(原)
    裁框 = 裁(原, 框, 边距比)
    剪 = 原.crop(裁框)

    记 = {"母图": os.path.basename(参.母图), "原尺寸": list(原.size),
          "主体框": list(框[:4]), "裁框": list(裁框), "留白比": 边距比,
          "透明阈值": [透明阈值, 透明上限], "背景色": [round(float(v), 1) for v in 框[4]],
          "产物": []}

    for 目标 in (1024, 512):
        白 = 缩到高(剪, 目标)
        路白 = os.path.join(出目录, "定版-白底-%d.png" % 目标)
        白.save(路白)
        透 = 透明化(白, 框[4])
        路透 = os.path.join(出目录, "定版-透明-%d.png" % 目标)
        透.save(路透)
        记["产物"].append({"尺寸": list(白.size), "白底": os.path.basename(路白),
                         "透明": os.path.basename(路透)})
        print("  %d 高：%s / %s（%d×%d）" % (目标, os.path.basename(路白),
                                           os.path.basename(路透), *白.size))

    io.open(os.path.join(出目录, "定版.json"), "w", encoding="utf-8").write(
        json.dumps(记, ensure_ascii=False, indent=1))
    print("记要：" + os.path.join(出目录, "定版.json"))
    return 0


if __name__ == "__main__":
    sys.exit(主())
