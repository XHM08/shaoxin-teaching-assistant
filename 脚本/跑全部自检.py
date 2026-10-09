
import os
import re
import shutil
import subprocess
import sys
import time

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
日志目录 = r"C:/tmp/跑全部"
保留目录 = r"C:/tmp/跑全部_失败"
要确认的 = "_会写盘.py"
超时秒 = 290


def 分类(码, 输出):
    结论词 = (r"项通过|通过数|都对得上|都画得出来|正常。|个能力和|对了|与现场一致|处对不上"
         r"|\d+\s*/\s*\d+|通过\s*\d+\s*/\s*共")
    if 码 == 0:
        if re.search(r"跳过|没验|未验", 输出) and not re.search(结论词, 输出):
            return "跳过", "它自己说了跳过/没验"
        if not re.search(结论词, 输出):
            return "无计数", "退出码 0，但没有可解析的收尾行 —— 要看一眼"
        return "通过", ""
    if 码 == 3:
        return "跳过", "自检按约定用 3 表示跳过"
    if 码 == 124:
        return "超时", "超过 %d 秒被掐" % 超时秒
    return "失败", "退出码 %s" % 码


def main():
    只看失败 = "--只看失败" in sys.argv
    os.makedirs(日志目录, exist_ok=True)
    if os.path.isdir(保留目录):
        shutil.rmtree(保留目录, ignore_errors=True)
    脚本 = sorted(x for x in os.listdir(os.path.join(根, "脚本"))
                if x.startswith("检查_") and x.endswith(".py"))
    状态表 = []
    起 = time.time()
    for 名 in 脚本:
        命令 = [sys.executable, os.path.join("脚本", 名)]
        if 名.endswith(要确认的):
            命令.append("--确认")
        日志 = os.path.join(日志目录, 名[:-3] + ".log")
        try:
            with open(日志, "w", encoding="utf-8") as 文件:
                跑 = subprocess.run(命令, cwd=根, stdout=文件, stderr=subprocess.STDOUT,
                                 timeout=超时秒)
            码 = 跑.returncode
        except subprocess.TimeoutExpired:
            码 = 124
        输出 = open(日志, encoding="utf-8", errors="replace").read() if os.path.isfile(日志) else ""
        状态, 说明 = 分类(码, 输出)
        尾行 = [x.strip() for x in 输出.splitlines() if x.strip()]
        状态表.append((名, 状态, 尾行[-1][:64] if 尾行 else "(没有输出)", 说明, 日志))
        if 状态 in ("失败", "超时", "无计数"):
            os.makedirs(保留目录, exist_ok=True)
            shutil.copy2(日志, os.path.join(保留目录, 名[:-3] + ".log"))

    计 = {}
    for _名, 状态, _尾, _说, _日 in 状态表:
        计[状态] = 计.get(状态, 0) + 1
    print("共 %d 条自检，用了 %.0f 秒" % (len(状态表), time.time() - 起))
    print("  " + "  ".join("%s %d" % (k, 计.get(k, 0)) for k in ("通过", "失败", "跳过", "超时", "无计数") if 计.get(k)))
    print()
    for 名, 状态, 尾, 说明, 日志 in 状态表:
        if 只看失败 and 状态 == "通过":
            continue
        记号 = {"通过": "✓", "失败": "✗", "跳过": "·", "超时": "…", "无计数": "?"}[状态]
        print("  %s %-28s %-4s %s%s" % (记号, 名, 状态, 尾, ("　← " + 说明) if 说明 else ""))
    if 计.get("失败") or 计.get("超时"):
        print("\n失败/超时的原文留在：%s" % 保留目录)
    if 计.get("跳过"):
        print("跳过的那几条**不算通过**：%s" % "、".join(
            名 for 名, 状态, _t, _s, _l in 状态表 if 状态 == "跳过"))
    return 1 if (计.get("失败") or 计.get("超时") or 计.get("无计数")) else 0


if __name__ == "__main__":
    sys.exit(main())
