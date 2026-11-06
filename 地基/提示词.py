
import os

from 地基 import 配置


def 取路径(名字):
    return os.path.join(配置.取目录("提示词"), 名字 + ".md")


def 读取(名字):
    路径 = 取路径(名字)
    if not os.path.isfile(路径):
        raise RuntimeError("找不到提示词文件：" + 路径)
    with open(路径, "r", encoding="utf-8") as 文件:
        return 文件.read()


def 填充(原文, **替换表):
    for 键, 值 in 替换表.items():
        原文 = 原文.replace("{" + 键 + "}", str(值))
    return 原文
