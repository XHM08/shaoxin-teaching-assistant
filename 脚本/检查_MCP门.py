
import json
import os
import shutil
import subprocess
import sys
import tempfile

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)

自检服务器 = os.path.join(根, "脚本", "_自检MCP服务器.py")
失败 = []
条数 = 0


def 记(名, 通过, 说明=""):
    global 条数
    条数 += 1
    print(("  ✓ " if 通过 else "  ✗ ") + 名 + ("" if 通过 else "　→　" + str(说明)))
    if not 通过:
        失败.append(名)


def 跑一份配置(额外字段, 临时目录):
    配置路 = os.path.join(临时目录, "MCP服务器.json")
    项 = {"名字": "自检门", "命令": sys.executable, "参数": [自检服务器]}
    项.update(额外字段)
    with open(配置路, "w", encoding="utf-8") as 文件:
        json.dump({"启用": True, "服务器们": [项]}, 文件, ensure_ascii=False)

    脚本 = (
        "import json, sys\n"
        "sys.path.insert(0, %r)\n"
        "from 地基 import 工具箱\n"
        "说 = []\n"
        "工具箱.接上MCP(记录=说.append, 配置路径=%r)\n"
        "print(json.dumps({'工具': [n for n in 工具箱.全部名字() if '·' in n], '说': 说},\n"
        "                 ensure_ascii=False))\n"
        "工具箱.关MCP()\n" % (根, 配置路)
    )
    跑 = subprocess.run([sys.executable, "-c", 脚本], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=根, timeout=120)
    行 = [x for x in (跑.stdout or "").splitlines() if x.startswith("{")]
    if not 行:
        raise RuntimeError("子进程没吐出结果：%s" % ((跑.stderr or "")[-200:]))
    return json.loads(行[-1])


def 跑检查():
    from 地基 import 工具箱

    记("① 判据本身：read_file / 查取消 算只读，删除全部 / 写日志 不算",
       all([工具箱.像只读工具("read_file"), 工具箱.像只读工具("查取消"),
            工具箱.像只读工具("list_directory"),
            not 工具箱.像只读工具("删除全部"), not 工具箱.像只读工具("写日志"),
            not 工具箱.像只读工具("execute_shell")]),
       "判据表：" + str([(n, 工具箱.像只读工具(n)) for n in
                        ("read_file", "查取消", "删除全部", "写日志", "execute_shell")]))

    临时 = tempfile.mkdtemp(prefix="MCP门-")
    try:
        甲 = 跑一份配置({}, 临时)
        工具甲 = 甲["工具"]
        记("② 什么都不写：只挂只读的「查取消」，写类一个都不挂",
           工具甲 == ["自检门·查取消"], "挂上了：" + str(工具甲))
        记("③ 被挡的会在启动记录里说清数目与名字",
           any("可能写入" in s and "写日志" in s for s in 甲["说"]),
           "记录：" + " ｜ ".join(甲["说"])[:160])

        乙 = 跑一份配置({"允许工具": ["写日志"]}, 临时)
        工具乙 = sorted(乙["工具"])
        记("④ 允许工具里列了「写日志」：它被挂上，其余写类仍被挡",
           工具乙 == sorted(["自检门·查取消", "自检门·写日志"]), "挂上了：" + str(工具乙))

        丙 = 跑一份配置({"全部工具": True}, 临时)
        记("⑤ 全部工具: true：6 个全挂", len(丙["工具"]) == 6, "只挂上 %d 个：%s" % (
            len(丙["工具"]), 丙["工具"]))
    finally:
        shutil.rmtree(临时, ignore_errors=True)

    源码 = open(os.path.join(根, "地基", "工具箱.py"), encoding="utf-8").read()
    记("⑥ 门还在源码里（不是只靠文档说）",
       "像只读工具" in 源码 and "允许工具" in 源码 and "全部工具" in 源码,
       "工具箱.py 里找不到那道门")

    说明 = open(os.path.join(根, "MCP说明.md"), encoding="utf-8").read()
    记("⑦ 说明文档同步写了这道门", "允许工具" in 说明 and "全部工具" in 说明,
       "MCP说明.md 里没写")


def 主():
    try:
        跑检查()
    except Exception as 错:
        记("检查本身跑完了", False, "%s: %s" % (type(错).__name__, 错))
    print()
    print("全部 %d 项通过" % 条数 if not 失败 else "通过 %d / 共 %d" % (条数 - len(失败), 条数))
    return 0 if not 失败 else 1


if __name__ == "__main__":
    sys.exit(主())
