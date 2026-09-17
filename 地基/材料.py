
import os

from 地基 import 配置

文字后缀 = (".txt", ".md")


def 清洗文字(原文):
    文字 = 原文.strip()
    while "\n\n\n" in 文字:
        文字 = 文字.replace("\n\n\n", "\n\n")
    return 文字


def 读材料(路径):
    with open(路径, "r", encoding="utf-8") as 文件:
        原文 = 文件.read()
    return 清洗文字(原文)


def 校验材料名(文件名):
    if not 文件名 or 文件名 in (".", ".."):
        raise ValueError("材料文件名不能为空")
    if "/" in 文件名 or os.sep in 文件名 or ":" in 文件名:
        raise ValueError("材料文件名不能带路径分隔符：" + repr(文件名))
    if not 文件名.endswith(文字后缀):
        raise ValueError("材料只支持 " + " / ".join(文字后缀) + "：" + repr(文件名))


def 材料路径(文件名):
    校验材料名(文件名)
    return os.path.join(配置.取目录("材料"), 文件名)


def 材料清单():
    目录 = 配置.取目录("材料")
    if not os.path.isdir(目录):
        return []

    条目表 = []
    for 文件名 in sorted(os.listdir(目录)):
        完整路径 = os.path.join(目录, 文件名)
        if not os.path.isfile(完整路径):
            continue
        if not 文件名.endswith(文字后缀):
            continue
        if 文件名 == "说明.md":
            continue
        条目表.append({"文件名": 文件名, "大小(字节)": os.path.getsize(完整路径)})
    return 条目表
