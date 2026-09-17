
import itertools
import subprocess
import threading

禁用清单 = (
    ("format ", "格式化磁盘"),
    ("diskpart", "磁盘分区工具"),
    ("mkfs", "格式化"),
    ("bcdedit", "改启动配置"),
    ("shutdown", "关机 / 重启"),
    ("logoff", "注销"),
    ("rm -rf /", "递归删根目录"),
    ("del /f /s /q c:\\", "递归删 C 盘"),
    ("rd /s /q c:\\", "递归删 C 盘"),
    ("reg delete hklm", "删系统注册表"),
)

危险词 = ("del ", "erase ", "rmdir", "rd /s", "rm ", "remove-item", "move ",
          "ren ", "taskkill", "stop-process", "reg ", "sc ", "winget",
          "pip install", "npm install")

命令长度上限 = 500
输出上限 = 4000
待确认上限 = 50

_待确认表 = {}
_锁 = threading.Lock()
_编号序列 = itertools.count(1)


def 登记(命令文本):
    with _锁:
        编号 = str(next(_编号序列))
        _待确认表[编号] = 命令文本
        while len(_待确认表) > 待确认上限:
            _待确认表.pop(next(iter(_待确认表)))
    return 编号


def 取票(编号, 命令文本):
    with _锁:
        登记过的 = _待确认表.get(str(编号))
        if 登记过的 is None:
            raise ValueError("这条命令没有登记过，或已经用过了。请重新让 AI 提出一次。")
        if 登记过的 != str(命令文本):
            raise ValueError("要执行的命令和登记的原文对不上，已拒绝。"
                             "票还留着 —— 照登记时的原文再来一次就行。")
        _待确认表.pop(str(编号), None)


def 检查(命令文本):
    文本 = str(命令文本 or "").strip()
    if not 文本:
        raise ValueError("命令不能为空。")
    if len(文本) > 命令长度上限:
        raise ValueError("命令太长了（最多 " + str(命令长度上限) + " 字）。")
    小写 = 文本.lower()
    for 关键词, 原因 in 禁用清单:
        if 关键词 in 小写:
            raise ValueError("这条命令被禁止（" + 原因 + "）：" + 文本)
    return 文本


def 风险提示(命令文本):
    小写 = str(命令文本).lower()
    命中 = sorted({词.strip() for 词 in 危险词 if 词 in 小写})
    if not 命中:
        return ""
    return "⚠ 这条命令可能改动文件或安装东西，看清楚了再点：" + "、".join(命中)


def 预览文字(命令文本, 工作目录, 超时秒数):
    return ("要执行的命令：\n    " + 命令文本 + "\n\n"
            "在哪执行：" + str(工作目录) + "\n"
            "最多等：" + str(超时秒数) + " 秒\n\n"
            "确认后才会真的跑。")


def _解码(原始字节):
    for 编码 in ("utf-8", "gbk"):
        try:
            return 原始字节.decode(编码)
        except UnicodeDecodeError:
            continue
    return 原始字节.decode("utf-8", "replace")


def 运行(命令文本, 工作目录, 超时秒数):
    try:
        结果 = subprocess.run(命令文本, shell=True, cwd=工作目录,
                              capture_output=True, timeout=超时秒数)
    except subprocess.TimeoutExpired:
        return {"退出码": None, "输出": "超过 " + str(超时秒数) + " 秒还没跑完，已中断。"}
    except OSError as 异常:
        return {"退出码": None, "输出": "起不来：" + type(异常).__name__ + " " + str(异常)}

    输出 = _解码(结果.stdout or b"") + _解码(结果.stderr or b"")
    return {"退出码": 结果.returncode, "输出": 输出.strip()[:输出上限] or "（没有输出）"}
