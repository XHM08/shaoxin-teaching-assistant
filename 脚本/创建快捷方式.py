
import base64
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)

客户端exe = os.path.join(BASE, "dist", "邵新", "邵新.exe")
if os.path.isfile(客户端exe):
    TARGET = 客户端exe
    WORKDIR = os.path.dirname(客户端exe)
    SHORTCUT_DESC = "启动「邵新」辅助教育系统（桌面客户端）"
else:
    TARGET = os.path.join(BASE, "启动.bat")
    WORKDIR = BASE
    SHORTCUT_DESC = "启动「邵新」辅助教育系统（本地服务 + 自动打开浏览器）"

SHORTCUT_NAME = "「邵新」辅助教育系统.lnk"
自备图标 = os.path.join(BASE, "邵新.ico")
ICON = 自备图标 if os.path.isfile(自备图标) else r"C:\Windows\System32\shell32.dll,137"


def ps(script):
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def parse(out):
    data = {}
    for line in out.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def build_create_script():
    return "\n".join([
        "$ErrorActionPreference = 'Stop'",
        "$target = '" + TARGET.replace("'", "''") + "'",
        "$workdir = '" + WORKDIR.replace("'", "''") + "'",
        "if (-not (Test-Path $target))  { throw ('TARGET_MISSING: ' + $target) }",
        "if (-not (Test-Path $workdir)) { throw ('WORKDIR_MISSING: ' + $workdir) }",
        "$desktop = [Environment]::GetFolderPath('Desktop')",
        "$name = '" + SHORTCUT_NAME.replace("'", "''") + "'",
        "$linkPath = Join-Path $desktop $name",
        "$existed = Test-Path $linkPath",
        "$ws = New-Object -ComObject WScript.Shell",
        "$lnk = $ws.CreateShortcut($linkPath)",
        "$lnk.TargetPath = $target",
        "$lnk.WorkingDirectory = $workdir",
        "$lnk.IconLocation = '" + ICON.replace("'", "''") + "'",
        "$lnk.Description = '" + SHORTCUT_DESC.replace("'", "''") + "'",
        "$lnk.Save()",
        "Write-Output ('EXISTED_BEFORE=' + $existed)",
        "Write-Output ('DESKTOP=' + $desktop)",
        "Write-Output ('LINK=' + $linkPath)",
        "Write-Output ('LINK_EXISTS=' + (Test-Path $linkPath))",
        "Write-Output ('WORKDIR_EXISTS=' + (Test-Path $workdir))",
        "Write-Output ('TARGET_EXISTS=' + (Test-Path $target))",
        "$c = $ws.CreateShortcut($linkPath)",
        "Write-Output ('ECHO_TARGET=' + $c.TargetPath)",
        "Write-Output ('ECHO_WORKDIR=' + $c.WorkingDirectory)",
    ])


def build_remove_script():
    return "\n".join([
        "$ErrorActionPreference = 'Stop'",
        "$desktop = [Environment]::GetFolderPath('Desktop')",
        "$name = '" + SHORTCUT_NAME.replace("'", "''") + "'",
        "$linkPath = Join-Path $desktop $name",
        "$existed = Test-Path $linkPath",
        "if ($existed) { Remove-Item $linkPath -Force }",
        "Write-Output ('EXISTED_BEFORE=' + $existed)",
        "Write-Output ('LINK=' + $linkPath)",
        "Write-Output ('LINK_EXISTS=' + (Test-Path $linkPath))",
    ])


def 主程序():
    remove = "--remove" in sys.argv[1:]

    if not os.path.isfile(TARGET):
        print("要指的目标不存在：" + TARGET)
        return 1
    if not os.path.isdir(WORKDIR):
        print("工作目录不存在：" + WORKDIR)
        return 1
    if not os.path.isdir(BASE):
        print("工作目录不存在：" + BASE)
        return 1

    code, out = ps(build_remove_script() if remove else build_create_script())
    data = parse(out)

    if code != 0:
        print("PowerShell 执行失败（退出码 " + str(code) + "）：")
        print(out)
        return code

    if remove:
        if data.get("EXISTED_BEFORE") == "True":
            print("已删除：" + data.get("LINK", ""))
        else:
            print("桌面上本来就没有这个快捷方式")
        return 0

    if data.get("EXISTED_BEFORE") == "True":
        print("注意：桌面已有同名快捷方式，已覆盖")
    print("已创建：" + data.get("LINK", ""))
    print("指向：  " + TARGET)
    print()
    print("以下几项是实际检查（不是照抄写入的值）：")
    print("  快捷方式文件存在：" + data.get("LINK_EXISTS", "?"))
    print("  目标文件存在：    " + data.get("TARGET_EXISTS", "?"))
    print("  工作目录存在：    " + data.get("WORKDIR_EXISTS", "?"))
    print()
    print("以下几项只是写入回显，只说明字符串存进去了：")
    print("  目标（回显）：    " + data.get("ECHO_TARGET", "?"))
    print("  工作目录（回显）：" + data.get("ECHO_WORKDIR", "?"))
    print()
    print("「双击能不能打开」我无法在这里验证。请到桌面双击一次确认。")
    print("   图标不满意可在「属性 → 更改图标」里换。")
    return 0


if __name__ == "__main__":
    sys.exit(主程序())
