
import json
import uuid
import os
import subprocess

from 地基 import 课件, 配置

页图后缀 = "_页图"
台账名 = "页图.json"
导出宽 = 1600
导出高 = 900
导出超时 = 180

导出脚本骨架 = r"""
param([string]$Prog, [string]$Pptx, [string]$Out)
$ErrorActionPreference = 'Stop'
$app = New-Object -ComObject $Prog
$p = $null
try {
  $p = $app.Presentations.Open($Pptx, $true, $false, $false)
  $i = 0
  foreach ($s in $p.Slides) {
    $i++
    $s.Export((Join-Path $Out ("page" + $i + ".png")), "PNG", __宽__, __高__)
  }
  Write-Output ("OK " + $i)
} finally {
  if ($p) { try { $p.Close() } catch {} }
  try { $app.Quit() } catch {}
}
"""


def 找放映程序():
    try:
        import winreg
    except ImportError:
        return None
    for 名 in ("KWPP.Application", "PowerPoint.Application"):
        for 根 in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                键 = winreg.OpenKey(根, "SOFTWARE\\Classes\\" + 名)
                键.Close()
                return 名
            except OSError:
                continue
    return None


def 能导出吗():
    名 = 找放映程序()
    if not 名:
        return False, ("这台电脑上没有找到 WPS 演示或 PowerPoint（导出每页图要借它们的接口）。"
                    "不装也行：播放页会退回用文字显示这一页。")
    return True, 名


def 取位置(课件路径):
    课件名 = os.path.splitext(os.path.basename(str(课件路径)))[0]
    目录名 = 课件名 + 页图后缀
    return {"目录名": 目录名, "目录": os.path.join(配置.取目录("课件输出"), 目录名)}


def 读台账(输出目录):
    路径 = os.path.join(输出目录, 台账名)
    try:
        with open(路径, "r", encoding="utf-8") as 文件:
            账 = json.load(文件)
    except Exception:
        return {}
    if not isinstance(账, dict):
        return {}
    图 = 账.get("图")
    if isinstance(图, dict):
        干净 = {}
        for 号, 名 in 图.items():
            try:
                干净[str(int(号))] = str(名)
            except (TypeError, ValueError):
                continue
        账["图"] = 干净
    else:
        账["图"] = {}
    return 账


def 写台账(输出目录, 台账):
    路径 = os.path.join(输出目录, 台账名)
    临时 = 路径 + ".写中" + "." + uuid.uuid4().hex[:8]
    with open(临时, "w", encoding="utf-8") as 文件:
        json.dump(台账, 文件, ensure_ascii=False, indent=1)
    os.replace(临时, 路径)


def 导出各页(课件路径, 警告=None):
    位置 = 取位置(课件路径)
    输出目录, 目录名 = 位置["目录"], 位置["目录名"]
    现在指纹 = 课件.指纹(课件路径)
    旧 = 读台账(输出目录)
    首次 = not 旧
    旧图 = {}
    for 号 in sorted(旧.get("图") or {}, key=lambda x: int(x)):
        旧图[号] = 旧["图"][号]
    图们 = [旧图[号] for 号 in 旧图]
    if (课件.指纹一样吗(旧.get("课件指纹"), 现在指纹)
            and 图们
            and all(os.path.isfile(os.path.join(输出目录, 名)) for 名 in 图们)):
        位置.update({"图": 图们, "页数": len(图们)})
        return 位置

    能, 为什么 = 能导出吗()
    if not 能:
        raise RuntimeError(为什么)

    页数 = len(课件.读各页(课件路径))
    os.makedirs(输出目录, exist_ok=True)
    脚本路径 = os.path.join(输出目录, "_导出.ps1")
    脚本 = 导出脚本骨架.replace("__宽__", str(导出宽)).replace("__高__", str(导出高))
    with open(脚本路径, "w", encoding="utf-8", newline="\r\n") as 文件:
        文件.write(脚本)
    try:
        跑 = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                          "-File", 脚本路径, "-Prog", 为什么,
                          "-Pptx", os.path.abspath(str(课件路径)), "-Out", os.path.abspath(输出目录)],
                         capture_output=True, text=True, encoding="utf-8", timeout=导出超时)
    except subprocess.TimeoutExpired:
        raise RuntimeError("导出每页图超时了（%d 秒）：放映软件可能卡住了；" % 导出超时
                         + "把 WPS/PowerPoint 里打开的那份关掉再试")
    finally:
        try:
            os.remove(脚本路径)
        except OSError:
            pass
    出 = ((跑.stdout or "") + (跑.stderr or "")).strip().splitlines()
    末 = 出[-1] if 出 else ""
    if not 末.startswith("OK "):
        raise RuntimeError("导出每页图失败：" + (末[:160] or "没有任何输出"))
    导了 = int(末.split()[1])
    if 导了 != 页数:
        raise RuntimeError("导出的页数（%d）与课件的页数（%d）对不上，不敢用这批图" % (导了, 页数))

    图们 = []
    for 序号 in range(1, 导了 + 1):
        名 = "page%d.png" % 序号
        如果 = os.path.join(输出目录, 名)
        if not os.path.isfile(如果) or os.path.getsize(如果) < 1024:
            raise RuntimeError("导出的第 %d 页图不对劲（没生成或太小）" % 序号)
        图们.append(名)

    for 名 in os.listdir(输出目录):
        if 名.startswith("page") and 名.endswith(".png") and 名 not in 图们:
            try:
                os.remove(os.path.join(输出目录, 名))
            except OSError:
                pass

    写台账(输出目录, {"课件指纹": 现在指纹, "页数": len(图们),
                   "图": {str(i + 1): 名 for i, 名 in enumerate(图们)}})
    if isinstance(警告, list):
        警告.append(("已导出 %d 页图" if 首次 else "课件改了，重新导出了 %d 页图") % len(图们))
    位置.update({"图": 图们, "页数": len(图们)})
    return 位置


def 页图地址(目录名, 页码):
    return "/课件图/" + str(目录名) + "/page%d.png" % int(页码)
