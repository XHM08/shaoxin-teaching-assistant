
import itertools
import re
import subprocess
import threading

禁用清单 = (
    (r"\bformat\b", "格式化磁盘", "format D: /q"),
    (r"\bdiskpart\b", "磁盘分区工具", "diskpart /s 脚本.txt"),
    (r"\b(?:mkfs|mke2fs)\b", "格式化文件系统", "mkfs.ext4 /dev/sda1"),
    (r"\bbcdedit\b", "改启动配置", "bcdedit /set safeboot minimal"),
    (r"\b(?:shutdown|logoff)\b", "关机 / 注销", "shutdown /s /t 0"),
    (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+/", "递归删根目录", "rm -rf /"),
    (r"\b(?:del|erase|rd|rmdir)\b[^\n]{0,40}/s\b[^\n]{0,20}[a-zA-Z]:\\",
     "递归删盘符", "rd /s /q C:\\"),
    (r"\breg\s+delete\b[^\n]{0,40}\b(?:hklm|hkcr)\b", "删系统注册表",
     "reg delete hklm\\software /f"),
    (r"\bvssadmin\b[^\n]{0,30}\bdelete\b", "删卷影副本（系统备份）",
     "vssadmin delete shadows /all"),
    (r"\bwbadmin\b[^\n]{0,30}\bdelete\b", "删系统备份", "wbadmin delete catalog"),
    (r"\bcipher\b[^\n]{0,20}/w", "擦除磁盘空闲空间", "cipher /w:C"),
)

禁用清单_等价写法 = (
    "format/q D:",
    "format.com C:",
    "diskpart",
    "reg  delete hklm\\software /f",
    "SHUTDOWN /s /t 0",
    "rd/s /q c:\\",
)

危险词 = (
    (r"\b(?:del|erase|rmdir|rd)\b", "删文件或目录"),
    (r"\brm\b", "删文件"),
    (r"\bremove-item\b", "删文件"),
    (r"\b(?:move|ren|rename)\b", "移动或改名"),
    (r"\b(?:copy|xcopy|robocopy)\b", "复制（会覆盖目标）"),
    (r"\b(?:taskkill|stop-process)\b", "结束进程"),
    (r"\breg\b", "改注册表"),
    (r"\bsc\b", "改系统服务"),
    (r"\b(?:winget|choco|scoop|apt|apt-get|brew|nuget|pip3?|npm|pnpm|yarn|npx|gem|cargo|dotnet)"
     r"\s+(?:i|install|add|upgrade|update|remove|uninstall)\b", "装或卸东西"),
    (r"\bpython[0-9.]*\s+-m\s+pip\b", "装或卸东西"),
    (r"\bgit\s+(?:clean|reset|restore|checkout\s+--)\b", "丢弃本地改动"),
    (r"\b(?:shutil\.rmtree|os\.remove|os\.rmdir|os\.unlink|\.unlink\()", "在脚本里删文件"),
    (r"\b(?:curl|wget|iwr|invoke-webrequest|invoke-restmethod|start-bitstransfer)\b",
     "联网下载"),
    (r"\b(?:powershell|pwsh)\b[^\n]{0,24}\s-(?:enc|encodedcommand)\b", "把命令编码藏起来"),
    (r"\bwmic\b", "用 wmic 改系统"),
    (r"\b(?:takeown|icacls|attrib)\b", "改文件权限或属性"),
    (r"\bnet\s+user\b", "改账户"),
    (r"\bmklink\b", "建链接"),
)

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
                             "票还留着：照登记时的原文再来一次就行。")
        _待确认表.pop(str(编号), None)


def 检查基本(命令文本):
    文本 = str(命令文本 or "").strip()
    if not 文本:
        raise ValueError("命令不能为空。")
    if len(文本) > 命令长度上限:
        raise ValueError("命令太长了（最多 " + str(命令长度上限) + " 字）。")
    return 文本


def 撞了禁用清单(命令文本):
    文本 = str(命令文本 or "")
    for 模式, 原因, _示例 in 禁用清单:
        if re.search(模式, 文本, re.I):
            return 原因
    return ""


def 检查(命令文本):
    文本 = 检查基本(命令文本)
    原因 = 撞了禁用清单(文本)
    if 原因:
        raise ValueError("这条命令被禁止（" + 原因 + "）：" + 文本)
    return 文本


def 风险提示(命令文本):
    文本 = str(命令文本 or "")
    命中 = []
    for 模式, 名字 in 危险词:
        if 名字 not in 命中 and re.search(模式, 文本, re.I):
            命中.append(名字)
    if not 命中:
        return ""
    return "⚠ 这条命令会" + "、".join(命中) + "，看清楚了再点。"


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
