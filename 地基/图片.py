
import os
import shutil

长边上限 = 1600
JPEG质量 = 85
最短边长 = 100
质量范围 = (30, 95)
支持后缀 = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff")


def _取PIL():
    try:
        from PIL import Image, ImageOps
        return Image, ImageOps
    except ImportError:
        raise ValueError("这台电脑没装 Pillow，图片预处理用不了。"
                         "装一下：pip install pillow（只影响图片，不影响其它功能）") from None


def _校验(长边, 质量):
    try:
        边 = int(长边)
    except (TypeError, ValueError):
        raise ValueError("长边要一个整数，收到 %r" % (长边,)) from None
    try:
        质 = int(质量)
    except (TypeError, ValueError):
        raise ValueError("质量要一个整数，收到 %r" % (质量,)) from None
    if 边 < 最短边长:
        raise ValueError("长边至少 %d 像素，收到 %d（再小就认不出字了）" % (最短边长, 边))
    if not (质量范围[0] <= 质 <= 质量范围[1]):
        raise ValueError("质量要在 %d 到 %d 之间，收到 %d" % (质量范围[0], 质量范围[1], 质))
    return 边, 质


def 预处理(源路径, 目标路径, 长边=None, 质量=None):
    结果 = {"ok": False, "已处理": False, "原尺寸": None, "新尺寸": None,
            "原字节": None, "新字节": None, "目标": 目标路径, "错误": ""}
    try:
        边, 质 = _校验(长边上限 if 长边 is None else 长边, JPEG质量 if 质量 is None else 质量)
        Image, ImageOps = _取PIL()
    except ValueError as 异常:
        结果["错误"] = str(异常)
        return 结果

    if not os.path.isfile(源路径):
        结果["错误"] = "这张图不在了：" + os.path.basename(str(源路径))
        return 结果
    结果["原字节"] = os.path.getsize(源路径)

    try:
        with Image.open(源路径) as 图:
            原尺寸 = 图.size
            朝向 = 0
            try:
                朝向 = int(图.getexif().get(274) or 0)
            except Exception:
                朝向 = 0
            转正 = ImageOps.exif_transpose(图)
            转正后尺寸 = 转正.size
            需要缩 = max(转正后尺寸) > 边
            if not 需要缩 and 朝向 in (0, 1):
                目录 = os.path.dirname(目标路径)
                if 目录:
                    os.makedirs(目录, exist_ok=True)
                shutil.copyfile(源路径, 目标路径)
                结果.update({"ok": True, "已处理": False, "原尺寸": 原尺寸, "新尺寸": 原尺寸,
                           "新字节": os.path.getsize(目标路径)})
                return 结果
            图2 = 转正.convert("RGB")
            if 需要缩:
                比 = 边 / float(max(转正后尺寸))
                图2 = 图2.resize((max(1, int(图2.size[0] * 比)), max(1, int(图2.size[1] * 比))),
                               Image.LANCZOS)
            目录 = os.path.dirname(目标路径)
            if 目录:
                os.makedirs(目录, exist_ok=True)
            图2.save(目标路径, "JPEG", quality=质, optimize=True)
            结果.update({"ok": True, "已处理": True, "原尺寸": 原尺寸, "新尺寸": 图2.size,
                       "新字节": os.path.getsize(目标路径)})
            return 结果
    except ValueError as 异常:
        结果["错误"] = str(异常)
        return 结果
    except Exception as 异常:
        结果["错误"] = ("这张图打不开（可能是改了扩展名的其它格式、或者是 HEIC）："
                     + os.path.basename(str(源路径))
                     + "　" + type(异常).__name__)
        return 结果


def 批量(源目录, 目标目录, 长边=None, 质量=None):
    产出 = {"清单": [], "跳过": [], "错误": ""}
    if not os.path.isdir(源目录):
        产出["错误"] = "这个目录不存在：" + str(源目录)
        return 产出

    名字们 = sorted(os.listdir(源目录))
    见的 = {}
    for 名 in 名字们:
        干名, 后 = os.path.splitext(名)
        if 后.lower() not in 支持后缀:
            产出["跳过"].append(名)
            continue
        if 干名 in 见的:
            产出["错误"] = ("这两个文件会写成同一个名字，先改掉一个：%s / %s"
                         % (见的[干名], 名))
            return 产出
        见的[干名] = 名

    for 名 in 名字们:
        后 = os.path.splitext(名)[1].lower()
        if 后 not in 支持后缀:
            continue
        目标 = os.path.join(目标目录, os.path.splitext(名)[0] + ".jpg")
        结果 = 预处理(os.path.join(源目录, 名), 目标, 长边, 质量)
        结果["文件名"] = 名
        产出["清单"].append(结果)
    return 产出
