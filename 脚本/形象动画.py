
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageFilter

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def 载透明(路, 目标高):
    图 = Image.open(路).convert("RGBA")
    比 = 目标高 / float(图.height)
    return 图.resize((max(1, int(round(图.width * 比))), 目标高), Image.LANCZOS)


def 浮(图, 宽, 高, 偏移):
    布 = Image.new("RGBA", (宽, 高), (0, 0, 0, 0))
    布.paste(图, ((宽 - 图.width) // 2, (高 - 图.height) // 2 + 偏移), 图)
    return 布


def 呼吸帧们(图, 宽, 高, 帧数, 幅度=6):
    import math
    出 = []
    for i in range(帧数):
        相 = i / float(帧数) * 2 * math.pi
        偏 = int(round(幅度 * math.sin(相)))
        比 = 1.0 + 0.012 * math.sin(相 + 0.9)
        缩 = 图.resize((max(1, int(图.width * 比)), max(1, int(图.height * 比))), Image.LANCZOS)
        横 = int(round(2 * math.sin(相 * 2 + 1.3)))
        布 = Image.new("RGBA", (宽, 高), (0, 0, 0, 0))
        布.paste(缩, ((宽 - 缩.width) // 2 + 横, (高 - 缩.height) // 2 + 偏), 缩)
        出.append(布)
    return 出


def 眨眼(睁, 半, 闭, 宽, 高):
    序 = [睁, 半, 闭, 半, 睁]
    return [浮(图, 宽, 高, 0) for 图 in 序]


def 说话帧们(a, b, c, 宽, 高):
    序 = [a, b, c, b]
    return [浮(图, 宽, 高, 0) for 图 in 序]


def 写webp(帧们, 路, 帧率):
    帧们[0].save(路, save_all=True, append_images=帧们[1:],
                duration=int(1000 / 帧率), loop=0,
                lossless=False, quality=90, method=4)


def 写webm(帧们, 路, 帧率):
    临时 = tempfile.mkdtemp(prefix="形象动画")
    try:
        宽, 高 = 帧们[0].size
        for i, 帧 in enumerate(帧们):
            帧.save(os.path.join(临时, "%04d.png" % i))
        命 = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
              "-framerate", str(帧率), "-i", os.path.join(临时, "%04d.png"),
              "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
              "-b:v", "0", "-crf", "32", "-auto-alt-ref", "0",
              "-metadata:s:v:0", "alpha_mode=1", 路]
        子 = subprocess.run(命, capture_output=True)
        if 子.returncode != 0:
            return False, 子.stderr.decode("utf-8", "replace")[:200]
        return True, ""
    finally:
        shutil.rmtree(临时, ignore_errors=True)


def 写gif(帧们, 路, 帧率, 时长毫秒=None):
    白 = []
    for 帧 in 帧们:
        底 = Image.new("RGB", 帧.size, (255, 255, 255))
        底.paste(帧, (0, 0), 帧)
        白.append(底)
    白[0].save(路, save_all=True, append_images=白[1:],
               duration=时长毫秒 or int(1000 / 帧率), loop=0, disposal=2)


def 主():
    解 = argparse.ArgumentParser()
    解.add_argument("--高", type=int, default=512)
    解.add_argument("--帧率", type=int, default=24)
    解.add_argument("--母图目录", default="")
    参 = 解.parse_args()

    目录 = 参.母图目录 or os.path.join(os.environ.get("AVATAR_HOME", ""), "母图")
    if not os.path.isdir(目录):
        raise SystemExit("找不到母图目录：" + (目录 or "（没设 AVATAR_HOME）"))
    出目录 = os.path.join(目录, "动画")
    os.makedirs(出目录, exist_ok=True)

    高 = 参.高
    定版 = 载透明(os.path.join(目录, "定版-透明-1024.png"), 高)
    宽, 高 = 定版.width, 定版.height

    def 表(名):
        路 = os.path.join(目录, "表情", 名 + "-透明.png")
        return 载透明(路, 高) if os.path.isfile(路) else None

    睁 = 定版
    半, 闭 = 表("半闭眼"), 表("闭眼")
    if not (半 and 闭):
        raise SystemExit("缺眨眼帧：先跑 形象表情.py --只 闭眼 / 半闭眼")

    待机 = 呼吸帧们(睁, 宽, 高, 48)
    眨 = 眨眼(睁, 半, 闭, 宽, 高)
    待机[22:27] = 眨

    说1, 说2, 说3 = 表("说话1"), 表("说话2"), 表("说话3")
    说话 = 说话帧们(说1 or 睁, 说2 or 睁, 说3 or 睁, 宽, 高)
    说话 = [浮(图, 宽, 高, 0) for 图 in 说话] * 6

    单帧 = {"待机": 待机, "说话": 说话}
    for 名 in ("微笑", "开心", "生气", "难过", "惊讶", "思考"):
        图 = 表(名)
        if 图:
            单帧[名] = 呼吸帧们(图, 宽, 高, 36)

    好, 坏 = [], []
    for 名, 帧们 in 单帧.items():
        路w = os.path.join(出目录, 名 + ".webp")
        try:
            写webp(帧们, 路w, 参.帧率)
        except Exception as 异:
            坏.append("%s webp：%s" % (名, type(异).__name__))
            continue
        写gif(帧们, os.path.join(出目录, 名 + ".gif"), 参.帧率)
        大小 = os.path.getsize(路w) // 1024
        好.append(名)
        print("  ✓ %-4s %3d 帧  %4d KB  %s" % (名, len(帧们), 大小, os.path.basename(路w)))

    验 = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True)
    if b"libvpx-vp9" in 验.stdout and 单帧:
        路 = os.path.join(出目录, "待机.webm")
        成, 错 = 写webm(单帧["待机"], 路, 参.帧率)
        if 成:
            查 = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                 "-show_entries", "stream=pix_fmt", "-of", "default=nw=1", 路],
                                capture_output=True)
            fmt = 查.stdout.decode("utf-8", "replace").strip()
            if "a" not in fmt.split("=")[-1]:
                os.remove(路)
                print("  · webm 没做成：本机 libvpx 把 alpha 丢了（%s），已删" % fmt)

    print("成 %d 个，败 %d 个" % (len(好), len(坏)))
    if 坏:
        print("失败：" + "；".join(坏))
    return 0 if 好 else 1


if __name__ == "__main__":
    sys.exit(主())
