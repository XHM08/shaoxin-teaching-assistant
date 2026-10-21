# -*- mode: python ; coding: utf-8 -*-
"""邵新 · PyInstaller 打包描述

用法：python 脚本/打包.py     （它负责跑 pyinstaller 并事后核对 + 冒烟）

为什么 contents_directory="."：让产物目录镜像源代码树，exe 与
网页/ 地基/ 能力/ 提示词/ 等平铺在同一层。于是
`配置.取根目录(冻结=True)` = exe 目录 = 原来的 样本/，一处改动就够。
若塞进 `_internal/`，资源根与数据根就要分成两套（一个走 sys._MEIPASS、
一个走 exe 目录），改动面大得多。

为什么要在 spec 里扫导入：`能力/*.py` 是 `importlib` 从目录里动态加载的，
PyInstaller 的静态分析追不到它们，于是它们用的标准库（`wave` 之类）一个都不会进包。
2026-10-08 第一次打包就是这么炸的：包内服务起来时
`ModuleNotFoundError: No module named 'wave'`（`能力/讲稿配音.py` 用的）。
所以这里把 能力/ / 地基/ / 语音/ 下所有 import 到的顶层模块名都扫出来，
能 import 的一律列进 hiddenimports。以后有人加能力、用了新的标准库，不用改这个文件。

语音服务不进包：它在外部 GPT-SoVITS 的 venv 里跑（5~11 GB）。这里只把
语音/ 下那几个启动脚本与说明带上，好让客户端找得到、起得来。
语音/参考音/ 绝不进包：那是某个人的声音录音，《知情同意书》里明确"不收"。
"""

import ast
import importlib.util
import os

SPEC = SPECPATH            # noqa: F821：PyInstaller 执行 spec 时会提供它

数据目录 = ["网页", "地基", "能力", "提示词", "样例", "脚本"]
数据文件 = [
    "配置.json", "MCP说明.md", "MCP服务器.示例.json", "服务商.示例.json",
    "邵新.ico",
    "MicrosoftEdgeWebview2Setup.exe",        # WebView2 引导安装器，随包发出去
    "语音/启动语音服务.py", "语音/启动语音服务.bat", "语音/说明.md", "语音/程序目录.txt",
]


def 扫导入(目录):
    """扫一个目录下所有 .py 的顶层导入名（不递归进 __pycache__）。"""
    名字 = set()
    for 根, 目录们, 文件们 in os.walk(目录):
        目录们[:] = [d for d in 目录们 if d != "__pycache__"]
        for 一个 in 文件们:
            if not 一个.endswith(".py"):
                continue
            try:
                with open(os.path.join(根, 一个), encoding="utf-8") as 文件:
                    树 = ast.parse(文件.read())
            except (OSError, SyntaxError):
                continue          # 读不了/解析不了就跳过，可忽略：它要么会被别处扫到，要么本来就有问题
            for 节点 in ast.walk(树):
                if isinstance(节点, ast.Import):
                    for 别名 in 节点.names:
                        名字.add(别名.name.split(".")[0])
                elif isinstance(节点, ast.ImportFrom) and 节点.level == 0 and 节点.module:
                    名字.add(节点.module.split(".")[0])
    return 名字


自有 = {"地基", "能力", "语音", "主程序", "本地服务", "课堂悬浮窗", "桌面客户端"}
扫到的 = set()
for 子 in ("能力", "地基", "语音"):
    扫到的 |= 扫导入(os.path.join(SPEC, 子))

自动补 = []
for 名 in sorted(扫到的 - 自有):
    try:
        if importlib.util.find_spec(名) is not None:
            自动补.append(名)
    except (ImportError, ValueError):
        continue          # 找不到就算了，可忽略：那是可选依赖，装都没装

hiddenimports = 自动补 + [
    # pywebview 在 Windows 上走 EdgeChromium（靠 pythonnet/clr 调 WebView2）。
    # 这几个是运行时按条件导入的，静态分析看不到，得点名。
    "webview.platforms.edgechromium",
    "webview.platforms.winforms",
    "clr_loader",
    "pythonnet",
]

datas = [(os.path.join(SPEC, d), d) for d in 数据目录]
datas += [(os.path.join(SPEC, f), os.path.dirname(f) or ".") for f in 数据文件]

a = Analysis(
    [os.path.join(SPEC, "主程序.py")],
    pathex=[SPEC],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter.test", "test", "unittest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="邵新",
    debug=False,
    strip=False,
    upx=False,
    console=False,              # 不开黑窗口：客户端要"像个正式软件"
    icon=os.path.join(SPEC, "邵新.ico"),
    contents_directory=".",     # 见文件头说明
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="邵新")
