
import io
import os
import shutil
import subprocess
import sys
import tempfile

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
快速项 = ("检查_纯函数.py", "检查_端口字面量.py", "检查_课件XR.py", "检查_提示词约定.py")

钩子模板 = """#!/bin/sh
# 由 脚本/装钩子.py 生成。只跑秒级的几条；慢的请手动跑 脚本/跑全部自检.py。
# 要跳过：git push --no-verify
fail=0
{{项}}
if [ "$fail" != "0" ]; then
  echo
  echo "有检查没过，这次没推。按上面的命令单独跑一遍看细节；赶时间可以用 git push --no-verify。"
  exit 1
fi
echo "快速检查都过了，继续推送。"
exit 0
"""

一项模板 = """if ! python "脚本/{名}"; then
  echo "  没过：{名}（单独跑：python 脚本/{名}）"
  fail=1
fi
"""

缺失模板 = """if [ ! -f "脚本/{名}" ]; then
  echo "  脚本不见了：脚本/{名}（钩子名单里还留着它）"
  fail=1
fi
"""


def 钩子正文(名单=快速项):
    段们 = []
    for 名 in 名单:
        段们.append(缺失模板.replace("{名}", 名))
        段们.append(一项模板.replace("{名}", 名))
    return 钩子模板.replace("{{项}}", "".join(段们))


def 写钩子(位置, 名单=快速项):
    with io.open(位置, "w", encoding="utf-8", newline="\n") as 文件:
        文件.write(钩子正文(名单))

    try:
        os.chmod(位置, os.stat(位置).st_mode | 0o111)
    except OSError:
        pass
    return 位置


def 装到(仓库根, 名单=快速项):
    钩子目录 = os.path.join(仓库根, ".git", "hooks")
    if not os.path.isdir(钩子目录):
        raise SystemExit("找不到 %s（这里不是 git 仓库，或 .git 不是目录）" % 钩子目录)
    return 写钩子(os.path.join(钩子目录, "pre-push"), 名单)


def 跑(钩子路径, 工作目录):
    return subprocess.run(["sh", 钩子路径], cwd=工作目录, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def 自测():
    临时 = tempfile.mkdtemp(prefix="钩子自测-")
    失败 = []
    try:
        仓库 = os.path.join(临时, "假仓库")
        os.makedirs(os.path.join(仓库, ".git", "hooks"))
        os.makedirs(os.path.join(仓库, "脚本"))
        for 名 in 快速项:
            io.open(os.path.join(仓库, "脚本", 名), "w", encoding="utf-8").write(
                "print('假的，直接过')\n")

        路 = 装到(仓库)
        正文 = io.open(路, encoding="utf-8").read()
        import re
        if re.search(r"[^\x00-\x7f]=", 正文):
            失败.append("钩子里出现了非 ASCII 变量名")
        if "\\" in 正文.replace('\\\\', ''):
            失败.append("钩子里出现了反斜杠路径")
        全绿 = 跑(路, 仓库)
        print("全绿一组：退出码 %d；最后一行 %r" % (全绿.returncode, (全绿.stdout or "").strip().splitlines()[-1:]))
        if 全绿.returncode != 0:
            失败.append("全绿却退出码 %d" % 全绿.returncode)


        坏 = os.path.join(仓库, "脚本", 快速项[0])
        io.open(坏, "w", encoding="utf-8").write("raise SystemExit(1)\n")
        有红 = 跑(路, 仓库)
        print("塞入失败项：退出码 %d；含「没过」字样 %s" % (
            有红.returncode, "没过" in (有红.stdout or "")))
        if 有红.returncode == 0:
            失败.append("有检查失败，钩子却放行")


        os.remove(坏)
        缺 = 跑(路, 仓库)
        print("删掉一个脚本：退出码 %d；提到「脚本不见了」 %s" % (
            缺.returncode, "脚本不见了" in (缺.stdout or "")))
        if 缺.returncode == 0 or "脚本不见了" not in (缺.stdout or ""):
            失败.append("缺脚本时没拦住或没说清")

        print("自测结果：" + ("通过" if not 失败 else "；".join(失败)))
        return 0 if not 失败 else 1
    finally:
        shutil.rmtree(临时, ignore_errors=True)


def 主():
    参数 = sys.argv[1:]
    if "--自测" in 参数:
        return 自测()
    路 = os.path.join(根, ".git", "hooks", "pre-push")
    if "--卸下" in 参数:
        if not os.path.isfile(路):
            print("本来就没装：" + 路)
            return 2
        os.remove(路)
        print("已卸下：" + 路)
        return 0

    装到(根)
    print("已装：" + 路)
    print("它跑：" + "、".join(快速项))
    print("可绕过：git push --no-verify")
    return 0


if __name__ == "__main__":
    sys.exit(主())
