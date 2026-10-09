
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 能力 import _环境

结果 = []
桩文本 = ("Python was not found; run without arguments to install from the Microsoft Store, "
        "or disable this shortcut from Settings > Apps > Advanced app settings > "
        "App execution aliases.")


def 检查(名字, 通过, 说明=""):
    结果.append((名字, bool(通过), 说明))


def 造桩(目录, 退出码):
    os.makedirs(目录, exist_ok=True)
    路径 = os.path.join(目录, "python.cmd")
    with open(路径, "w", encoding="utf-8", newline="\r\n") as 文件:
        文件.write("@echo off\necho " + 桩文本 + "\nexit /b " + str(退出码))
    return 目录


def 在路径下(前置目录, 函数):
    原 = os.environ.get("PATH", "")
    os.environ["PATH"] = 前置目录 + os.pathsep + 原
    try:
        return 函数()
    finally:
        os.environ["PATH"] = 原


def main():
    临时 = tempfile.mkdtemp(prefix="huanjing_stub_")
    try:
        可用, 说明 = _环境.检测("python")
        检查("① 真 Python 仍然判成已就绪，版本号是正常形状（'Python 3.x…'）",
            可用 and 说明.startswith("Python 3"), repr(说明))

        pip = _环境._版本("python", "-m", "pip", "--version", 样式名="pip")
        检查("①b pip 版本也读得出来（按可执行名查样式会把它误判成缺失）",
            bool(pip) and pip.startswith("pip "), repr(pip))

        桩0 = 造桩(os.path.join(临时, "stub0"), 0)
        可用0, 说明0 = 在路径下(桩0, lambda: _环境.检测("python"))
        检查("② 别名桩（退出码 0）→ 未配齐，且**不把商店提示当版本号**",
            (not 可用0) and 桩文本[:20] not in 说明0, repr(说明0)[:70])
        检查("②b 这一条还要给能照着做的提示（点名「别名桩」、指向 python.org）",
            ("别名桩" in 说明0) and ("python.org" in 说明0), repr(说明0)[:80])

        桩49 = 造桩(os.path.join(临时, "stub49"), 49)
        可用49, 说明49 = 在路径下(桩49, lambda: _环境.检测("python"))
        检查("③ 别名桩（退出码 49）→ 未配齐", not 可用49, repr(说明49)[:60])

        from 能力 import 环境配置

        def 看页面():
            条目 = {一条["代号"]: 一条 for 一条 in _环境.清单()}
            return 条目["python"]

        条目 = 在路径下(桩0, 看页面)
        检查("④ 桩生效时：状态「未配齐」、「怎么装」不是「—」、说明里看得见那句提示",
            条目["状态"] == "未配齐" and 条目["怎么装"] != "—" and "别名桩" in 条目["版本 / 说明"],
            "%s / %s / %s" % (条目["状态"], 条目["怎么装"], str(条目["版本 / 说明"])[:40]))
        回 = 在路径下(桩0, lambda: 环境配置.处理("python"))
        检查("④b 单看一项时也说要装（需要确认=True，老师才看得到「确认安装」）",
            "未配齐" in 回["提示"] and 回["需要确认"] is True,
            "%s ｜ %s" % (回["提示"], str(回["正文"])[:40]))

        for 代号, 期望前缀 in (("node", "v"), ("git", "git version")):
            条目 = {一条["代号"]: 一条 for 一条 in _环境.清单()}[代号]
            路径 = _环境._解析可执行文件(代号)
            if 路径 is None:
                检查("⑤ %s：这台机器上没有 → 跳过（这一条没验）" % 代号, True, "找不到可执行文件")
            else:
                检查("⑤ %s 有就必须仍然判成已就绪，且版本号形状正常" % 代号,
                    条目["状态"] == "已就绪" and 期望前缀 in 条目["版本 / 说明"],
                    "%s ｜ %s" % (条目["状态"], 条目["版本 / 说明"])[:70])
    finally:
        import shutil as _shutil
        _shutil.rmtree(临时, ignore_errors=True)

    print()
    坏 = 0
    for 名字, 过, 说明 in 结果:
        print(("  通过  " if 过 else "  失败  ") + 名字 + ("　→　" + 说明 if 说明 else ""))
        坏 += 0 if 过 else 1
    print("全部 %d 项通过" % len(结果) if not 坏 else "%d 项失败" % 坏)
    return 0 if not 坏 else 1


if __name__ == "__main__":
    sys.exit(main())
