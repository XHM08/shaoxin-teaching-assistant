
import io
import os

from 地基 import 注册表, 配置, 落盘

允许根 = ("材料", "教师数据")


def _根们():
    return [(名, os.path.normpath(配置.取目录(名))) for 名 in 允许根]


def _定路(路径):
    路径 = str(路径 or "").strip()
    if not 路径:
        raise ValueError("要给我一个文件路径，例如 材料/教案摘要.md")
    if os.path.isabs(路径):
        全 = os.path.normpath(路径)
    else:
        全 = os.path.normpath(os.path.join(os.getcwd(), 路径))
    for 名, 根 in _根们():
        if 全 == 根 or 全.startswith(根 + os.sep):
            if os.path.isdir(全):
                raise ValueError("给的是目录，不是文件：%s" % 路径)
            return 全, 名
    raise ValueError("只能写到 %s 下面，现在给的是：%s" % ("/".join(允许根), 路径))


def 处理(路径="", 内容="", 编码="utf-8", XR="C", 加XR="是"):
    全, 根名 = _定路(路径)
    编码 = str(编码 or "utf-8").strip().lower()
    if 编码 not in ("utf-8", "utf8"):
        raise ValueError("编码只支持 UTF-8（这个项目一律不带 BOM），现在写的是：%s" % 编码)
    文本 = "" if 内容 is None else str(内容)
    if not 文本:
        raise ValueError("内容是空的，没东西可写")

    后缀 = os.path.splitext(全)[1].lower()
    写了XR = False
    if str(加XR or "是").strip() != "否" and 后缀 in (".md", ".txt", ".py"):
        等级 = str(XR or "C").strip().upper() or "C"
        行们 = [一行 for 一行 in 文本.split(chr(10))
                if not 一行.strip().upper().startswith("XR:")]
        if len(行们) == 1:
            行们.append("")
        行们.insert(1, "XR: " + 等级)
        文本 = chr(10).join(行们)
        写了XR = True

    try:
        os.makedirs(os.path.dirname(全), exist_ok=True)
        落盘.带时间备份(全)
        with open(全, "w", encoding="utf-8", newline="") as 空:
            空.write("")
        with open(全, "a", encoding="utf-8", newline="") as 文件:
            文件.write(文本)
    except OSError as 异常:
        raise ValueError("写不进去：%s（%s）" % (全, 异常))

    try:
        回来 = io.open(全, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError) as 异常:
        raise ValueError("写完读不回来：%s（%s）" % (全, 异常))
    if len(回来) != len(文本):
        raise ValueError("写完长度对不上：写进 %d 字，读回 %d 字（%s）" % (len(文本), len(回来), 全))
    if 回来.startswith("\ufeff"):
        raise ValueError("文件带了 BOM，不该出现：%s" % 全)

    return {"正文": "已写入 %s（%d 字，%s，无 BOM%s）。"
                    % (全, len(回来), 根名, "，XR 在第 2 行" if 写了XR else "，没写 XR"),
            "路径": 全, "字数": len(回来), "写了XR": 写了XR}


注册表.登记(
    代号="写文件",
    标题="写文件",
    说明="把一段文字写成文件（UTF-8 无 BOM），只能写 材料/ 或 教师数据/ 下面，写完会读回来核长度。",
    参数=[
        {"代号": "路径", "标签": "文件路径（相对项目根，或绝对路径）", "类型": "text", "必填": True,
         "示例": "材料/教案摘要.md"},
        {"代号": "内容", "标签": "正文", "类型": "textarea", "必填": True, "示例": ""},
        {"代号": "编码", "标签": "编码（只支持 utf-8）", "类型": "text", "必填": False, "示例": "utf-8"},
        {"代号": "XR", "标签": "XR 等级（写进首行）", "类型": "text", "必填": False, "示例": "C"},
        {"代号": "加XR", "标签": "是否自动加 XR 首行（是/否）", "类型": "text", "必填": False, "示例": "是"},
    ],
    处理函数=处理,
)
