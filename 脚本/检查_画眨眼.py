
import importlib.util
import os
import shutil
import sys
import tempfile

import numpy as np
from PIL import Image

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)
源 = os.path.join(根, "脚本", "画眨眼.py")
母路 = os.path.join(os.environ.get("AVATAR_HOME", ""), "母图", "定版-白底-1024.png")
左 = (170, 147, 204, 173)
右 = (227, 147, 263, 173)

失败 = []
条数 = 0


def 记(名, 通过, 说明=""):
    global 条数
    条数 += 1
    print(("  ✓ " if 通过 else "  ✗ ") + 名 + ("" if 通过 else "　→　" + str(说明)))
    if not 通过:
        失败.append(名)


def 载():
    规格 = importlib.util.spec_from_file_location("画眨眼_被检", 源)
    模 = importlib.util.module_from_spec(规格)
    规格.loader.exec_module(模)
    return 模


def 亮比(图, 带):
    x0, y0, x1, y1 = 带
    a = np.asarray(图.crop(带)).astype(int)
    return 100.0 * (a.mean(axis=2) > 150).mean()


def 暗心(图, 带):
    a = np.asarray(图.crop(带)).astype(int).mean(axis=2)
    ys, xs = np.where(a < 110)
    if not len(xs):
        return None
    return float(xs.mean()), float(ys.mean())


def 主():
    if not os.path.isfile(母路):
        print("  跳过：没设 AVATAR_HOME（形象资产在仓库外），这一条这次没验")
        print("  （设好 AVATAR_HOME 再跑：set AVATAR_HOME=…\形象）")
        sys.exit(3)
    模 = 载()
    母 = Image.open(母路).convert("RGB")

    原亮 = (亮比(母, 左), 亮比(母, 右))
    原心 = (暗心(母, 左), 暗心(母, 右))
    记("母图两条眼带里都有眼睛（暗像素重心算得出来）", all(原心), 原心)

    临时 = tempfile.mkdtemp(prefix="画眨眼自检")
    try:
        输出 = {}
        for 比, 名 in ((0.40, "半"), (0.30, "闭")):
            合 = 母.copy()
            for 带 in (左, 右):
                块 = 模.造带(母, 带, "画" if 比 <= 0.35 else "压", 比)
                合.paste(块, (带[0], 带[1]))
            输出[名] = 合
            合.save(os.path.join(临时, 名 + ".png"))

        半, 闭 = 输出["半"], 输出["闭"]
        半亮 = (亮比(半, 左), 亮比(半, 右))
        闭亮 = (亮比(闭, 左), 亮比(闭, 右))

        原暗 = (100 - 原亮[0], 100 - 原亮[1])
        闭暗 = (100 - 闭亮[0], 100 - 闭亮[1])
        记("① 闭眼时亮像素明显变多（+25 点以上）且暗像素掉一半以上",
            all(闭亮[i] - 原亮[i] >= 25 for i in (0, 1))
            and all(闭暗[i] <= 原暗[i] * 0.5 for i in (0, 1)),
            "亮 %.1f/%.1f → %.1f/%.1f；暗 %.1f/%.1f → %.1f/%.1f"
            % (原亮[0], 原亮[1], 闭亮[0], 闭亮[1], 原暗[0], 原暗[1], 闭暗[0], 闭暗[1]))
        记("② 半闭介于母图与闭眼之间",
            all(半亮[i] - 原亮[i] >= 10 and 闭亮[i] - 半亮[i] >= 15 for i in (0, 1)),
            "母图 %s → 半闭 %s → 闭眼 %s" % (原亮, 半亮, 闭亮))

        漂 = []
        for 图 in (半, 闭):
            for 带, 原 in ((左, 原心[0]), (右, 原心[1])):
                新 = 暗心(图, 带)
                漂.append(abs(新[0] - 原[0]) if 新 else 99)
        记("③ 眼线重心横向漂移不超过 1.5 像素", max(漂) <= 1.5, "最大漂移 %.1f" % max(漂))

        外改 = 0
        for 图 in (半, 闭):
            甲 = np.abs(np.asarray(母).astype(int) - np.asarray(图).astype(int)).sum(axis=2)
            外 = np.ones(甲.shape, bool)
            for x0, y0, x1, y1 in (左, 右):
                外[max(0, y0 - 2):y1 + 2, max(0, x0 - 2):x1 + 2] = False
            外改 += int((甲[外] > 0).sum())
        记("④ 眼带以外一个像素都没动", 外改 == 0, "被改 %d 像素" % 外改)

        记("⑤ 产物文件名与动画脚本读的一致",
            os.path.isfile(os.path.join(os.environ["AVATAR_HOME"], "母图", "部件", "闭眼-绘制.png"))
            and os.path.isfile(os.path.join(os.environ["AVATAR_HOME"], "母图", "部件", "半闭眼-绘制.png")),
            "缺 闭眼-绘制.png 或 半闭眼-绘制.png")
    finally:
        shutil.rmtree(临时, ignore_errors=True)

    坏带 = 模.解析带("100,300,130,320;200,300,230,320")
    记("⑥ 把眼带挪到不存在眼睛的地方，会被 最少暗像素 这条挡住",
        坏带 and 模.暗像素数(母, 坏带[0]) < 模.最少暗像素,
        "那条带上暗像素 %d（阈值 %d）" % (模.暗像素数(母, 坏带[0]), 模.最少暗像素))

    print()
    if 失败:
        print("失败 %d / 共 %d：%s" % (len(失败), 条数, "、".join(失败)))
        sys.exit(1)
    print("全部 %d 项通过" % 条数)
    sys.exit(0)


if __name__ == "__main__":
    主()
