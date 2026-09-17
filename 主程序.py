

import os
import sys

from 地基 import 配置, 注册表, 工具箱


def 加载():
    结果 = 注册表.全部加载(os.path.join(配置.根目录, "能力"))
    工具箱.接上MCP(记录=lambda 一条: print("  " + 一条))
    return 结果


def 解析键值(片段表):
    实参 = {}
    for 片段 in 片段表:
        if "=" not in 片段:
            raise SystemExit(
                "参数要写成 键=值 的形式，收到的是：" + repr(片段)
                + "\n例如：python 主程序.py 运行 蒸馏 文件=a.txt 代号=teacher-a 描述=小学数学"
            )
        键, 值 = 片段.split("=", 1)
        实参[键.strip()] = 值
    return 实参


def 列出():
    if not 注册表.已登记能力:
        print("没有加载到任何能力。检查 能力/ 目录。")
        return 0
    print("已登记能力（" + str(len(注册表.已登记能力)) + " 个）：")
    for 代号 in 注册表.全部名字():
        条目 = 注册表.已登记能力[代号]
        参数字段 = "、".join(参数项["代号"] for 参数项 in 条目["参数"]) or "无参数"
        print("  " + 代号.ljust(16) + 条目["标题"])
        print("      " + 条目["说明"])
        print("      参数：" + 参数字段)
    return 0


def 看工具():
    from 地基 import 工具箱
    if not 工具箱.已登记工具:
        print("没有登记任何工具。")
        return 0
    print("已登记工具（" + str(len(工具箱.已登记工具)) + " 个）—— 这是给模型用的白名单：")
    for 工具名 in 工具箱.全部名字():
        工具 = 工具箱.已登记工具[工具名]
        参数字段 = "、".join(参数项["代号"] for 参数项 in 工具["参数"]) or "无参数"
        print("  " + 工具名.ljust(24) + 工具["说明"] + "（参数：" + 参数字段 + "）")
    return 0


def 运行(名字, 实参):
    try:
        处理函数 = 注册表.校验参数(名字, 实参)
    except (KeyError, ValueError) as 异常:
        raise SystemExit(异常.args[0] if 异常.args else str(异常))

    结果 = 处理函数(**实参)
    if isinstance(结果, dict):
        if 结果.get("提示"):
            print(结果["提示"])
        if 结果.get("正文"):
            print()
            print(结果["正文"])
        for 一行 in 结果.get("条目") or []:
            print("  " + "  ".join(str(键) + "=" + str(值) for 键, 值 in 一行.items()))
        for 一条 in 结果.get("待确认命令") or []:
            print("  [待确认命令，要在网页界面上点确认才会执行] " + str(一条.get("命令", "")))
    else:
        print(结果)
    return 0


def 起服务():
    import 本地服务
    本地服务.主程序()
    return 0


def 主程序(命令行参数):
    if len(命令行参数) < 2 or 命令行参数[1] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return 0

    try:
        加载()
    except Exception as 异常:
        raise SystemExit("能力加载失败（能力/ 里有文件写错了）：\n  "
                         + type(异常).__name__ + ": " + str(异常))

    命令 = 命令行参数[1]

    try:
        if 命令 == "列出":
            return 列出()
        if 命令 == "工具":
            return 看工具()
        if 命令 == "运行":
            if len(命令行参数) < 3:
                raise SystemExit("用法：python 主程序.py 运行 <能力名> [键=值 ...]")
            return 运行(命令行参数[2], 解析键值(命令行参数[3:]))
        if 命令 == "起服务":
            return 起服务()
    except (KeyError, ValueError, OSError, RuntimeError) as 异常:
        raise SystemExit("[" + type(异常).__name__ + "] " + str(异常))

    raise SystemExit("不认识这个命令：" + 命令 + "\n可用：列出 / 运行 / 工具 / 起服务")


if __name__ == "__main__":
    sys.exit(主程序(sys.argv))
