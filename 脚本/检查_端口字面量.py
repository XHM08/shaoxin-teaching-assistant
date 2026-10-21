
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 配置

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


期望端口 = 18765

失败 = []
条数 = 0


def 记(名, 通过, 说明=""):
    global 条数
    条数 += 1
    print(("  ✓ " if 通过 else "  ✗ ") + 名 + ("" if 通过 else "　→　" + str(说明)))
    if not 通过:
        失败.append(名)


def 取默认端口():
    表 = getattr(配置, "默认配置", None)
    if not isinstance(表, dict):
        raise RuntimeError("地基/配置.py 里找不到 默认配置 这个字典")
    本地 = 表.get("本地服务")
    if not isinstance(本地, dict) or "端口" not in 本地:
        raise RuntimeError("默认配置 里没有 本地服务.端口")
    return int(本地["端口"])


def 读(相对):
    with open(os.path.join(根, 相对), encoding="utf-8") as 文件:
        return 文件.read()


def 问题列表(端口, 取端口源=None, 启动源=None, 客户端源=None, 服务商源=None):
    取端口源 = 读("脚本/取端口.py") if 取端口源 is None else 取端口源
    启动源 = 读("启动.bat") if 启动源 is None else 启动源
    客户端源 = 读("桌面客户端.py") if 客户端源 is None else 客户端源
    服务商源 = 读("服务商.示例.json") if 服务商源 is None else 服务商源

    问题 = []
    if re.search(r"^\s*默认\s*=\s*\d+", 取端口源, re.M):
        问题.append("脚本/取端口.py 还有默认端口兜底")
    if re.search(r"set\s+\"?PORT=\d+", 启动源, re.I):
        问题.append("启动.bat 还在自己兜底一个端口号")
    if re.search(r"本地服务[（(]\s*\d", 客户端源):
        问题.append("桌面客户端.py 的说明里还写死了端口号")
    for 数 in re.findall(r"127\.0\.0\.1:(\d+)", 服务商源):
        if int(数) != 端口:
            问题.append("服务商.示例.json 的示例地址是 %s，默认是 %d" % (数, 端口))
    return 问题


def 跑检查():
    端口 = 取默认端口()
    记("① 默认端口读得到，且等于团队定的那个号（%d）" % 期望端口, 端口 == 期望端口,
       "读到的是 %d" % 端口)

    问题 = 问题列表(端口)
    记("② 启动链上没有第二个端口来源、示例地址与默认一致", not 问题, "；".join(问题))

    取 = 读("脚本/取端口.py")
    记("③ 取端口.py 的语义仍转调 配置.取端口", "配置.取端口()" in 取, "那行没了")

    起 = 读("启动.bat")
    记("④ 启动.bat 拿不到端口会报错退出",
       "取不到服务端口" in 起 and "exit /b 1" in 起, "报错分支没了")

    记("⑤ 反向验：取端口.py 塞回 `默认 = 8765` 必须报红",
       bool(问题列表(端口, 取端口源=取 + "\n默认 = 8765\n")), "塞了还全绿")
    记("⑥ 反向验：启动.bat 塞回 set PORT=8765 必须报红",
       bool(问题列表(端口, 启动源=起 + '\nif not defined PORT set "PORT=8765"\n')), "塞了还全绿")
    记("⑦ 反向验：桌面客户端写死端口必须报红（半角括号也算）",
       bool(问题列表(端口, 客户端源=读("桌面客户端.py") + "\n本地服务(8765)\n")), "塞了还全绿")
    记("⑧ 反向验：示例地址数字不对必须报红",
       bool(问题列表(端口, 服务商源=json.dumps({"说明": ["http://127.0.0.1:8765"]}, ensure_ascii=False))),
       "塞了还全绿")


def 主():
    try:
        跑检查()
    except Exception as 错:

        记("检查本身跑完了", False, "%s: %s" % (type(错).__name__, 错))
    print()
    print("全部 %d 项通过" % 条数 if not 失败 else "通过 %d / 共 %d" % (条数 - len(失败), 条数))
    return 0 if not 失败 else 1


if __name__ == "__main__":
    sys.exit(主())
