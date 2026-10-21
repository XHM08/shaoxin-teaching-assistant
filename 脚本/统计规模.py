

import os
import shutil
import sys
import tempfile

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


代码类 = {".py": "Python", ".html": "网页", ".css": "样式", ".bat": "启动脚本",
        ".ps1": "PowerShell", ".spec": "打包配置", ".md": "文档与提示词",
        ".json": "配置"}
不算的目录 = ("_备份", "_不是原始副本", "__pycache__", ".git", "node_modules", "_页面截图",
           "dist", "build", "密钥",
           "学生数据", "教师数据", "材料", "课件输出", "技能包", "日志")
运行时数据 = ("学生数据", "教师数据", "材料", "课件输出", "技能包", "日志")
构建产物 = ("dist", "build")


def 走一遍(起=根):
    出 = []
    for 头, 目录们, 文件们 in os.walk(起):
        目录们[:] = [d for d in 目录们
                     if d not in 不算的目录 and not d.startswith("_备份")]
        for f in 文件们:
            出.append(os.path.relpath(os.path.join(头, f), 起).replace("\\", "/"))
    return 出


def 数代码(文件们, 起=根):
    组 = {}
    for 相对 in 文件们:
        扩 = os.path.splitext(相对)[1].lower()
        if 扩 not in 代码类:
            continue
        try:
            with open(os.path.join(起, 相对), encoding="utf-8", errors="replace") as f:
                n = sum(1 for _ in f)
        except OSError:
            continue
        组.setdefault(扩, [0, 0])
        组[扩][0] += 1
        组[扩][1] += n
    return {k: tuple(v) for k, v in 组.items()}


def 量体积(子目录, 起=根):
    n = 0
    for 头, 目录们, 文件们 in os.walk(os.path.join(起, 子目录)):
        for f in 文件们:
            try:
                n += os.path.getsize(os.path.join(头, f))
            except OSError:
                pass
    return n


def 自测():
    临时 = tempfile.mkdtemp(prefix="规模自测-")
    try:
        要造的 = ("a.py", "网页/首页.html", "文档.md", "配置.json",
                "忽略.xyz",
                "dist/产物.py", "build/缓存.py",
                "密钥/KEY.txt", "学生数据/名册.json", "材料/说明.md",
                "_备份/旧.py", "__pycache__/x.py")
        for 相对 in 要造的:
            全 = os.path.join(临时, 相对.replace("/", os.sep))
            os.makedirs(os.path.dirname(全), exist_ok=True)
            with open(全, "w", encoding="utf-8") as f:
                f.write("线1\n线2\n")

        文件们 = 走一遍(临时)
        进了 = {k: v[0] for k, v in 数代码(文件们, 临时).items()}
        该进 = {".py": 1, ".html": 1, ".md": 1, ".json": 1}
        绿1 = 进了 == 该进
        绿2 = all(not 他.startswith(("dist/", "build/", "密钥/", "学生数据/", "材料/",
                                 "_备份/", "__pycache__/")) for 他 in 文件们)

        绿3 = "忽略.xyz" in 文件们 and ".xyz" not in 进了

        原先 = 不算的目录
        漏进 = None
        try:
            globals()["不算的目录"] = tuple(d for d in 原先 if d != "dist")
            漏进 = [他 for 他 in 走一遍(临时) if 他.startswith("dist/")]
        finally:
            globals()["不算的目录"] = 原先
        绿4 = bool(漏进)

        print("  %s 代码统计只认代码类扩展名：%s（应为 %s）" % ("✓" if 绿1 else "✗", 进了, 该进))
        print("  %s dist/build/密钥/学生数据/材料/_备份/__pycache__ 一个都没漏进走一遍():%s"
              % ("✓" if 绿2 else "✗", [他 for 他 in 文件们
                                  if 他.startswith(("dist/", "build/", "密钥/", "学生数据/",
                                                    "材料/", "_备份/", "__pycache__/"))]))
        print("  %s 分工对：走一遍 原样带出 .xyz，数代码 把它过滤掉：%s"
              % ("✓" if 绿3 else "✗", sorted(文件们)))
        print("  %s 反向：把 dist 从排除清单里拿掉，它就会漏进来（%s）—— 证明这条真在管"
              % ("✓" if 绿4 else "✗", 漏进))
        return 0 if (绿1 and 绿2 and 绿3 and 绿4) else 1
    finally:
        shutil.rmtree(临时, ignore_errors=True)


def main():
    if "--自测" in sys.argv:
        return 自测()
    文件们 = 走一遍()
    组 = 数代码(文件们)
    print("代码：%d 个文件 / %d 行（含空行与注释）"
          % (sum(v[0] for v in 组.values()), sum(v[1] for v in 组.values())))
    for 扩, (n, m) in sorted(组.items(), key=lambda x: -x[1][1]):
        print("   %-12s %3d 个  %7d 行" % (代码类[扩], n, m))

    源码 = 0
    for 相对 in 文件们:
        if os.path.splitext(相对)[1].lower() not in 代码类:
            continue
        try:
            源码 += os.path.getsize(os.path.join(根, 相对))
        except OSError:
            pass
    print("\n体积（分三段说，别合成一个数）")
    print("   源码            %7.1f MB" % (源码 / 1048576))
    逐项 = [(d, 量体积(d)) for d in 运行时数据]
    print("   运行时数据      %7.1f MB" % (sum(n for _, n in 逐项) / 1048576))
    for d, n in 逐项:
        print("      %-12s %7.1f MB" % (d, n / 1048576))
    逐项 = [(d, 量体积(d)) for d in 构建产物]
    print("   构建产物        %7.1f MB   （可随时重打，不算老师的数据）"
          % (sum(n for _, n in 逐项) / 1048576))
    for d, n in 逐项:
        print("      %-12s %7.1f MB" % (d, n / 1048576))


    全量 = 0
    for 头, _, 文件们 in os.walk(根):
        for f in 文件们:
            try:
                全量 += os.path.getsize(os.path.join(头, f))
            except OSError:
                pass
    print("\n   样本/ 整个目录  %7.1f MB   （全量走一遍，不排除任何子目录）" % (全量 / 1048576))
    return 0


if __name__ == "__main__":
    sys.exit(main())
