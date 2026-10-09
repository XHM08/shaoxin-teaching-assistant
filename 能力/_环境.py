
import os
import re
import shutil
import subprocess

VSCODE安装位置 = (
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
    r"C:\Program Files\Microsoft VS Code\Code.exe",
)

环境清单 = [
    {"id": "python", "名称": "Python", "用途": "跑脚本、跑本系统",
     "winget": "Python.Python.3.12"},
    {"id": "node", "名称": "Node.js", "用途": "跑 JavaScript 工具",
     "winget": "OpenJS.NodeJS.LTS"},
    {"id": "git", "名称": "Git / Git Bash", "用途": "版本管理 + 命令行环境",
     "winget": "Git.Git"},
    {"id": "vscode", "名称": "VS Code", "用途": "写代码的编辑器",
     "winget": "Microsoft.VisualStudioCode"},
    {"id": "wsl", "名称": "WSL（Linux 子系统）", "用途": "在 Windows 里跑 Linux",
     "winget": ""},
]

_按代号索引 = {一项["id"]: 一项 for 一项 in 环境清单}


def 取环境项(环境代号):
    return _按代号索引.get(str(环境代号).strip())


版本样式 = {
    "python": r"^Python \d+\.\d+",
    "pip": r"^pip \d+",
    "node": r"^v?\d+\.\d+\.\d+$",
    "npm": r"^\d+\.\d+\.\d+",
    "git": r"^git version \d+",
    "bash": r"^GNU bash, version \d+",
    "code": r"^\d+\.\d+\.\d+",
}

跑不起来的提示 = {
    "python": ("找到的 python 跑不出正常版本号 —— **多半是 Windows 应用商店的那个「别名桩」**："
               "没装 Python 也会有这个 python.exe，运行它只会打开应用商店，系统这边就永远找不到真的 python。\n"
               "两种做法（挑一种）：\n"
               "  · 正常装一个：去 python.org 下载 Python 3，安装时**务必勾上 Add python.exe to PATH**；\n"
               "  · 已经装过、只是被桩挡住：打开「设置 → 应用 → 高级应用设置 → 应用执行别名」，"
               "把 python.exe / python3.exe 这两项**关掉**。\n"
               "两种做法做完，都把本系统关掉重开，再点一次「检测本机环境」。"),
}


def _跑不起来说明(命令名):
    if _解析可执行文件(命令名) is None:
        return ""
    return 跑不起来的提示.get(
        命令名, "找到了 " + 命令名 + "，但它跑不出正常的版本号 —— 多半是别名桩，或是装坏了。")


def _解析可执行文件(命令名):
    路径 = shutil.which(命令名)
    if not 路径:
        return None
    if 路径.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", 路径]
    return [路径]


def _跑(命令, 超时=60, 解码="utf-8"):
    try:
        结果 = subprocess.run(命令, capture_output=True, timeout=超时)
    except FileNotFoundError:
        return None, ""
    except subprocess.TimeoutExpired:
        return None, "(超时)"
    except OSError as 异常:
        return None, "(" + type(异常).__name__ + ")"
    原始字节 = 结果.stdout or 结果.stderr or b""
    return 结果.returncode, 原始字节.decode(解码, "replace").strip()


def _首行(文本):
    行表 = [行.strip() for 行 in str(文本).splitlines() if 行.strip()]
    return 行表[0][:70] if 行表 else ""


def _版本(命令名, *参数, 样式名=None):
    命令 = _解析可执行文件(命令名)
    if 命令 is None:
        return ""
    状态码, 文本 = _跑(命令 + list(参数), 超时=60)
    if 状态码 != 0:
        return ""
    行 = _首行(文本)
    样式 = 版本样式.get(样式名 or 命令名)
    if 样式 and not re.match(样式, 行):
        return ""
    return 行


def _WSL情况():
    命令 = _解析可执行文件("wsl")
    if 命令 is None:
        return False, []
    状态码, _ = _跑(命令 + ["--status"], 超时=60, 解码="utf-16-le")
    _, 列表 = _跑(命令 + ["-l", "-q"], 超时=60, 解码="utf-16-le")
    return (状态码 == 0), [行.strip() for 行 in 列表.splitlines() if 行.strip()]


def 手动提示(环境代号):
    if 环境代号 == "wsl":
        已启用, 发行版表 = _WSL情况()
        if not 已启用:
            return ("WSL 功能还没启用。\n"
                    "做法：右键开始菜单 →「终端(管理员)」→ 输入 wsl --install → 重启电脑。")
        if not 发行版表:
            return ("WSL 功能已启用，但一个 Linux 发行版都没装，所以还不能用。\n"
                    "做法：右键开始菜单 →「终端(管理员)」→ 输入 wsl --install -d Ubuntu → 重启电脑。")
        return ""
    return ""


def 检测(环境代号):
    if 环境代号 == "python":
        版本 = _版本("python", "--version")
        if not 版本:
            return False, _跑不起来说明("python")
        pip = _版本("python", "-m", "pip", "--version", 样式名="pip")
        return True, 版本 + ("（" + pip.split(" from ")[0] + "）" if pip else "（pip 缺失）")

    if 环境代号 == "node":
        版本 = _版本("node", "--version")
        if not 版本:
            return False, _跑不起来说明("node")
        npm = _版本("npm", "--version")
        return True, 版本 + ("（npm " + npm + "）" if npm else "（npm 缺失）")

    if 环境代号 == "git":
        版本 = _版本("git", "--version")
        if not 版本:
            return False, _跑不起来说明("git")
        bash = _版本("bash", "--version")
        if bash:
            短版本 = bash.replace("GNU bash, version ", "").split("(")[0].strip()
            版本 += "（Git Bash " + 短版本 + "）"
        return True, 版本

    if 环境代号 == "vscode":
        版本 = _版本("code", "--version")
        if 版本:
            return True, 版本
        for 路径 in VSCODE安装位置:
            if os.path.exists(路径):
                return True, "已安装（命令行工具不可用）"
        return False, ""

    if 环境代号 == "wsl":
        已启用, 发行版表 = _WSL情况()
        if not 已启用:
            return False, ""
        if not 发行版表:
            return False, "功能已启用，但没有发行版"
        return True, "已启用 · 发行版：" + "、".join(发行版表)

    return False, ""


def 清单():
    条目 = []
    for 环境项 in 环境清单:
        可用, 说明 = 检测(环境项["id"])
        if 可用:
            怎么装, 提示文字 = "—", ""
        elif 环境项.get("winget"):
            怎么装, 提示文字 = "点「安装」自动装", ""
        else:
            怎么装, 提示文字 = "需管理员权限", 手动提示(环境项["id"])
        条目.append({
            "代号": 环境项["id"],
            "环境": 环境项["名称"],
            "状态": "已就绪" if 可用 else "未配齐",
            "版本 / 说明": 说明 or "—",
            "怎么装": 怎么装,
            "补充提示": 提示文字,
        })
    return 条目


def 方案(环境代号):
    环境项 = 取环境项(环境代号)
    if 环境项 is None:
        return {}
    可用, 说明 = 检测(环境项["id"])
    方式 = ("winget install --id " + 环境项["winget"] + " -e") if 环境项.get("winget") else "手动（需管理员）"
    return {"环境": 环境项["名称"], "当前状态": "已就绪" if 可用 else "未配齐",
            "现在": 说明 or "—", "安装方式": 方式}


def 安装(环境代号):
    环境项 = 取环境项(环境代号)
    if 环境项 is None:
        raise ValueError("没有这个环境项：" + str(环境代号))
    if not 环境项.get("winget"):
        raise ValueError(环境项["名称"] + " 需要手动安装：\n" + 手动提示(环境项["id"]))

    命令 = _解析可执行文件("winget")
    if 命令 is None:
        raise RuntimeError("这台电脑上没有 winget，装不了。"
                           "到微软商店搜「应用安装程序」装上，再回来试。")

    参数 = 命令 + ["install", "--id", 环境项["winget"], "-e", "--silent",
                  "--disable-interactivity",
                  "--accept-source-agreements", "--accept-package-agreements"]
    状态码, 文本 = _跑(参数, 超时=1800)
    行表 = [行 for 行 in 文本.splitlines() if 行.strip()]
    return {
        "环境": 环境项["名称"],
        "结果": "成功" if 状态码 == 0 else "失败",
        "退出码": 状态码,
        "输出末尾": "\n".join(行表[-6:])[:600],
    }
