
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 材料

结果 = []


def 检查(名字, 通过, 说明=""):
    结果.append((名字, bool(通过), 说明))


def 建联接(链接, 指向):
    跑 = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                      "New-Item -ItemType Junction -Path '%s' -Target '%s' | Out-Null" % (链接, 指向)],
                      capture_output=True, text=True)
    return 跑.returncode == 0 and os.path.isdir(链接), (跑.stderr or 跑.stdout or "")[:90]


def 删联接(链接):
    subprocess.run(["cmd", "/c", "rmdir", 链接.replace("/", "\\")], capture_output=True, text=True)


def main():
    连根 = tempfile.mkdtemp(prefix="jtest_root_")
    连外 = tempfile.mkdtemp(prefix="jtest_out_")
    内 = os.path.join(连根, "inside")
    os.makedirs(内, exist_ok=True)
    with open(os.path.join(内, "x.txt"), "w", encoding="utf-8") as 文件:
        文件.write("里面")
    with open(os.path.join(连外, "y.txt"), "w", encoding="utf-8") as 文件:
        文件.write("外面")

    外链 = os.path.join(连根, "link_out")
    内链 = os.path.join(连根, "link_in")
    建好了 = []
    try:
        for 链接, 指向 in ((外链, 连外), (内链, 内)):
            成, 错 = 建联接(链接, 指向)
            建好了.append(成)
        if not all(建好了):
            print("  跳过：这台机器上建不出 junction（%s 个没建成）—— **这一条这次没验**" % 建好了.count(False))
            print("  （常见原因：没有 PowerShell，或权限不允许建联接）")
            return 0

        原取目录 = 材料.配置.取目录
        材料.配置.取目录 = lambda 名: 连根 if 名 == "材料" else 原取目录(名)
        try:
            名字 = [条["文件名"] for 条 in 材料.材料清单()]
            检查("正常文件照旧列得到", "inside/x.txt" in 名字, str(名字))
            检查("指到 材料/ 外面的联接**不跟着走**（不然会列出外面一堆文件）",
                not any(n.startswith("link_out") for n in 名字), str(名字))
            检查("指到里面的联接**不重复列**（真身去过就不再列第二遍）",
                not any(n.startswith("link_in") for n in 名字), str(名字))
            try:
                材料.材料路径("link_out/y.txt")
                检查("外面那份文件读不了（清单与读取同一把尺子）", False, "居然读到了")
            except ValueError as 异常:
                检查("外面那份文件读不了（清单与读取同一把尺子）", True, str(异常)[:46])
            检查("里面的那份（经内链）读得到", os.path.isfile(材料.材料路径("link_in/x.txt")))
        finally:
            材料.配置.取目录 = 原取目录
    finally:
        for 链接 in (外链, 内链):
            删联接(链接)
        shutil.rmtree(连根, ignore_errors=True)
        剩下 = os.path.isfile(os.path.join(连外, "y.txt"))
        检查("清理时只删链接、没连带动目标里的文件", 剩下, "目标里的 y.txt 还在=" + str(剩下))
        shutil.rmtree(连外, ignore_errors=True)

    print()
    坏 = 0
    for 名字, 过, 说明 in 结果:
        print(("  通过  " if 过 else "  失败  ") + 名字 + ("　→　" + 说明 if 说明 else ""))
        坏 += 0 if 过 else 1
    print("全部 %d 项通过" % len(结果) if not 坏 else "%d 项失败" % 坏)
    return 0 if not 坏 else 1


if __name__ == "__main__":
    sys.exit(main())
