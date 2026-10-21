
import os
import re

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
标记路 = os.path.join(根, "网页", "首页.html")
脚本路 = os.path.join(根, "网页", "首页.js")
拼接分隔 = "\n<!-- ===== 以下来自 网页/首页.js（拼接后的行号不对应任一原文件） ===== -->\n"

_脚本引用 = re.compile(r'''<script[^>]*src=["']/网页/首页\.js["']''')
_所有脚本标签 = re.compile(r"<script\b[^>]*>")


class 页面缺文件(Exception):
    pass


def 读标记(路=None):
    return open(路 or 标记路, encoding="utf-8").read()


def 读脚本(路=None):
    目标 = 路 or 脚本路
    if not os.path.isfile(目标):
        raise 页面缺文件("读不到 " + 目标 + "（首页的脚本）。"
                       "要么它被改名，要么打包漏了，要么拆分没做完")
    return open(目标, encoding="utf-8").read()


def 引用了脚本(标记文本=None):
    文本 = 标记文本 if 标记文本 is not None else 读标记()
    return bool(_脚本引用.search(文本))


def 内联脚本数(标记文本=None):
    文本 = 标记文本 if 标记文本 is not None else 读标记()
    return len([标签 for 标签 in _所有脚本标签.findall(文本) if "src=" not in 标签])


def 读页面():
    return 读标记() + 拼接分隔 + 读脚本()
