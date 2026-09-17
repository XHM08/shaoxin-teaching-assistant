
import os
import subprocess
import time

需确认动作 = ("清临时文件", "清空回收站")

最短存放秒数 = 3600

动作清单 = [
    {"代号": "系统状态", "名称": "看看电脑状态", "说明": "内存和磁盘各用了多少（只看不动）"},
    {"代号": "占用排行", "名称": "谁最占内存", "说明": "占用内存最多的几个程序（只看不动）"},
    {"代号": "扫临时文件", "名称": "看看能清多少垃圾", "说明": "只统计，不删除"},
    {"代号": "清临时文件", "名称": "清理临时文件", "说明": "删掉系统临时目录里的旧文件"},
    {"代号": "清空回收站", "名称": "清空回收站", "说明": "清空后无法恢复"},
]

关键词表 = {
    "系统状态": ("内存", "卡不卡", "电脑状态", "磁盘", "还剩多少", "配置"),
    "占用排行": ("谁占", "哪个程序", "哪些程序", "占内存", "占用高", "谁在跑"),
    "扫临时文件": ("能清多少", "看看垃圾", "多少垃圾", "扫一下", "扫扫"),
    "清临时文件": ("垃圾", "临时文件", "清一下", "清理", "变慢", "腾空间", "磁盘满"),
    "清空回收站": ("回收站",),
}

状态脚本 = (
    "$os = Get-CimInstance Win32_OperatingSystem;"
    "$t = [math]::Round($os.TotalVisibleMemorySize/1MB,2);"
    "$f = [math]::Round($os.FreePhysicalMemory/1MB,2);"
    "Write-Output ('MEM|' + $t + '|' + $f);"
    "Get-PSDrive -PSProvider FileSystem | ForEach-Object {"
    " if ($_.Used -ne $null -and $_.Free -ne $null) {"
    "  Write-Output ('DISK|' + $_.Name + '|' + [math]::Round($_.Used/1GB,1) + '|' +"
    " [math]::Round(($_.Used + $_.Free)/1GB,1)) } }"
)

占用脚本 = (
    "Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 8 |"
    " ForEach-Object { $_.ProcessName + '|' + [math]::Round($_.WorkingSet64/1MB,0) }"
)


def 跑PowerShell(脚本, 超时=120):
    结果 = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", 脚本],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=超时)
    return (结果.stdout or "").strip(), (结果.stderr or "").strip()


def 临时目录表():
    结果 = []
    for 环境变量 in ("TEMP", "TMP"):
        路径 = os.environ.get(环境变量)
        if 路径 and os.path.isdir(路径) and 路径 not in 结果:
            结果.append(路径)
    系统临时 = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Temp")
    if os.path.isdir(系统临时) and 系统临时 not in 结果:
        结果.append(系统临时)
    return 结果


def _遍历(目录):
    for 根, 子目录, 文件表 in os.walk(目录, onerror=lambda 异常: None):
        for 文件名 in 文件表:
            yield os.path.join(根, 文件名)


def 系统状态():
    输出, 错误 = 跑PowerShell(状态脚本, 超时=90)
    if not 输出:
        raise RuntimeError("读不到系统信息：" + (错误 or "（没有输出）"))
    条目 = []
    for 行 in 输出.splitlines():
        片段 = 行.strip().split("|")
        if 片段[0] == "MEM" and len(片段) == 3:
            总数, 空闲 = float(片段[1]), float(片段[2])
            已用 = round(总数 - 空闲, 2)
            条目.append({"项目": "内存", "已用": "%.1f GB" % 已用, "总数": "%.1f GB" % 总数,
                         "占用": "%d%%" % round(已用 / 总数 * 100)})
        elif 片段[0] == "DISK" and len(片段) == 4:
            已用, 总数 = float(片段[2]), float(片段[3])
            条目.append({"项目": "磁盘 " + 片段[1] + ":", "已用": "%.1f GB" % 已用,
                         "总数": "%.1f GB" % 总数,
                         "占用": "%d%%" % round(已用 / 总数 * 100)})
    return 条目


def 占用排行():
    输出, 错误 = 跑PowerShell(占用脚本, 超时=90)
    if not 输出:
        raise RuntimeError("读不到进程信息：" + (错误 or "（没有输出）"))
    条目 = []
    for 行 in 输出.splitlines():
        片段 = 行.strip().split("|")
        if len(片段) == 2:
            条目.append({"程序": 片段[0], "占用内存(MB)": 片段[1]})
    return 条目


_扫描缓存 = {"时刻": 0.0, "数据": None}


def 扫临时文件(缓存秒数=0):
    现在 = time.time()
    if 缓存秒数 and _扫描缓存["数据"] is not None and 现在 - _扫描缓存["时刻"] < 缓存秒数:
        return dict(_扫描缓存["数据"])
    总计 = 0
    个数 = 0
    for 目录 in 临时目录表():
        for 路径 in _遍历(目录):
            try:
                总计 += os.path.getsize(路径)
                个数 += 1
            except OSError:
                pass
    结果 = {"文件数": 个数, "可释放(MB)": round(总计 / 1048576, 1),
            "清理范围": "、".join(临时目录表())}
    _扫描缓存.update({"时刻": 现在, "数据": 结果})
    return 结果


def 清临时文件():
    截止时刻 = time.time() - 最短存放秒数
    释放 = 0
    删除数 = 0
    跳过 = 0
    for 目录 in 临时目录表():
        for 路径 in _遍历(目录):
            try:
                if os.path.getmtime(路径) > 截止时刻:
                    continue
                大小 = os.path.getsize(路径)
                os.remove(路径)
                释放 += 大小
                删除数 += 1
            except OSError:
                跳过 += 1
    _扫描缓存["数据"] = None
    return {"已删除文件": 删除数, "跳过（正在使用）": 跳过,
            "释放(MB)": round(释放 / 1048576, 1)}


def 清空回收站():
    输出, 错误 = 跑PowerShell("Clear-RecycleBin -Force -ErrorAction SilentlyContinue;"
                              "Write-Output 'DONE'", 超时=300)
    if "DONE" not in 输出:
        raise RuntimeError("清空回收站没成功：" + (错误 or "（没有输出）"))
    return {"结果": "回收站已清空"}


处理表 = {
    "系统状态": 系统状态,
    "占用排行": 占用排行,
    "扫临时文件": 扫临时文件,
    "清临时文件": 清临时文件,
    "清空回收站": 清空回收站,
}


def 取动作(代号):
    for 动作 in 动作清单:
        if 动作["代号"] == 代号:
            return 动作
    return None


def 要确认吗(代号):
    return 代号 in 需确认动作


def 预览(代号):
    if 代号 == "清临时文件":
        信息 = 扫临时文件(缓存秒数=30)
        return 信息, ("将要清理 " + 信息["清理范围"] + " 下 1 小时没动过的文件，"
                      "预计释放 " + str(信息["可释放(MB)"]) + " MB。正在使用中的会跳过。\n"
                      "确认后才会真正删除。")
    return {}, ("将要清空回收站。清空后里面的东西无法恢复。\n"
                "确认后才会真正执行。")
