
import os
import sys

from PIL import Image, ImageDraw, ImageFont

底色 = (14, 61, 120)
字色 = (255, 255, 255)
画布 = 1024
字 = "邵"
字体路径 = "C:/Windows/Fonts/msyhbd.ttc"

项目根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
图标路径 = os.path.join(项目根, "邵新.ico")
预览路径 = "C:/tmp/邵新-预览.png"
要的尺寸 = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def 主程序():
    if not os.path.isfile(字体路径):
        print("找不到字体：" + 字体路径 + "（图标里的「邵」要靠它渲染）")
        return 1
    try:
        font = ImageFont.truetype(字体路径, int(画布 * 0.74), index=0)
    except OSError as 异常:
        print("字体打不开：" + str(异常))
        return 1

    图 = Image.new("RGB", (画布, 画布), 底色)
    笔 = ImageDraw.Draw(图)
    左, 上, 右, 下 = 笔.textbbox((0, 0), 字, font=font)
    宽, 高 = 右 - 左, 下 - 上
    if 宽 < 画布 * 0.4 or 高 < 画布 * 0.4:
        print("字形尺寸反常（%dx%d）：多半是字体里没有「%s」这个字" % (宽, 高, 字))
        return 1

    笔.text(((画布 - 宽) / 2 - 左, (画布 - 高) / 2 - 上), 字, font=font, fill=字色)

    直方图 = 图.convert("L").histogram()
    墨迹 = sum(直方图[201:])
    占比 = 墨迹 / float(画布 * 画布)
    if not 0.15 <= 占比 <= 0.40:
        print("墨迹占比 %.4f 不在 0.15~0.40。图标可能是空白，或糊成一团" % 占比)
        return 1

    图.save(图标路径, format="ICO", sizes=要的尺寸)
    图.resize((256, 256), Image.LANCZOS).save(预览路径)

    回 = Image.open(图标路径)
    实际 = sorted(回.info.get("sizes", []))
    if 实际 != 要的尺寸:
        print("图标里的尺寸不对：" + str(实际) + "，应有 " + str(要的尺寸))
        return 1

    print("已写出 " + 图标路径 + "（" + str(os.path.getsize(图标路径)) + " 字节）")
    print("墨迹占比 %.4f，%d 种尺寸，都对得上" % (占比, len(实际)))
    return 0


if __name__ == "__main__":
    sys.exit(主程序())
