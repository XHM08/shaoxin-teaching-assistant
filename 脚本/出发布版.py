
import ast
import io
import os
import re
import shutil
import subprocess
import sys
import tokenize

项目根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
远端引用 = "origin/main"


收录的顶层 = ("主程序.py", "本地服务.py", "课堂悬浮窗.py", "课堂悬浮窗.bat", "启动.bat",
          "安装WSL-Ubuntu-右键以管理员身份运行.bat", "MCP说明.md",
          "MCP服务器.json", "MCP服务器.示例.json", "服务商.示例.json", "配置.json",
          ".gitignore", "邵新.ico")
收录的目录 = ("地基", "能力", "网页", "提示词", "样例", "脚本", "材料", "语音", "技能包")


沿用远端的 = ("README.md", ".gitignore") + (
    "技能包/demo-real/SKILL.md", "技能包/qa-verify-pack/SKILL.md",
    "技能包/refactor-check/SKILL.md",
)


绝不收录 = (".git", "__pycache__", "dist", "build", "设计", "密钥", "学生数据",
         "课件输出", "日志", "教师数据", "参考音", "邵新-预览.png", "出发布版.py")

材料白名单 = ("材料/说明.md",)

二进制后缀 = (".ico", ".png", ".jpg", ".jpeg", ".gif", ".wav", ".pptx", ".xlsx", ".zip")


配置_json发布版 = '{\n  "合规": {\n    "同意书已签": false\n  }\n}\n'
程序目录_txt发布版 = ("# GPT-SoVITS 的安装目录。装到别处就改这一行。\n"
              "# 例：D:\\projects\\GPT-SoVITS\n")


def 去py(源):
    行 = 源.splitlines(True)
    删 = set()
    换 = {}
    for 节点 in ast.walk(ast.parse(源)):
        if isinstance(节点, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            体 = getattr(节点, "body", [])
            if not 体 or not isinstance(体[0], ast.Expr):
                continue
            if not (isinstance(体[0].value, ast.Constant) and isinstance(体[0].value.value, str)):
                continue
            文档 = 体[0]
            终 = 文档.end_lineno or 文档.lineno
            if len(体) == 1 and not isinstance(节点, ast.Module):

                首行 = 行[文档.lineno - 1]
                换[文档.lineno] = 首行[:len(首行) - len(首行.lstrip())] + "pass"
                for i in range(文档.lineno + 1, 终 + 1):
                    删.add(i)
            else:
                for i in range(文档.lineno, 终 + 1):
                    删.add(i)
    for 记号 in tokenize.generate_tokens(io.StringIO(源).readline):
        if 记号.type == tokenize.COMMENT and 记号.start[0] not in 删 and 记号.start[0] not in 换:
            换[记号.start[0]] = 记号.line[:记号.start[1]].rstrip()
    出 = []
    for i, 一 in enumerate(行, 1):
        if i in 删:
            continue
        尾 = 一[len(一.rstrip("\r\n")):]
        if i in 换:
            if 换[i]:
                出.append(换[i] + 尾)

        else:
            出.append(一)
    return "".join(出)


def 去js(源):
    源 = re.sub(r"/\*.*?\*/", "", 源, flags=re.S)


    return re.sub(r"^[ \t]*//.*?\r?\n", "", 源, flags=re.M)


def 去css(源):
    return re.sub(r"/\*.*?\*/", "", 源, flags=re.S)


def 去html(源):
    return re.sub(r"[ \t]*<!--.*?-->[ \t]*\r?\n?", "", 源, flags=re.S)


def 去bat(源):
    return "".join(一 for 一 in 源.splitlines(True)
                   if not 一.strip().lower().startswith("rem"))


规则 = {".py": 去py, ".js": 去js, ".css": 去css, ".html": 去html, ".bat": 去bat}


def 去注释(路径, 源):
    return 规则.get(os.path.splitext(路径)[1].lower(), lambda s: s)(源)


def git(参数):
    跑 = subprocess.run(["git"] + 参数, cwd=项目根, capture_output=True)
    return 跑.returncode, 跑.stdout


def 远端文件们():
    码, 出 = git(["ls-tree", "-r", "--name-only", "-z", 远端引用])
    if 码 != 0:
        return []
    return sorted(x for x in 出.decode("utf-8").split("\0") if x)


def 远端字节(路径):
    码, 出 = git(["show", "%s:%s" % (远端引用, 路径)])
    return 出 if 码 == 0 else None


def 收吗(相对):
    段 = 相对.split("/")
    if any(一 in 绝不收录 for 一 in 段):
        return False


    if os.path.basename(相对).endswith("说明.md"):
        return False
    if 相对 in 沿用远端的:
        return True
    if 相对.startswith("材料/"):
        return 相对 in 材料白名单
    if 相对.startswith("技能包/"):
        return 相对 in 沿用远端的
    if 段[0] in 收录的顶层 or 段[0] in 收录的目录:
        return not 相对.endswith(".pyc")
    return False


def 新字节(相对):
    if 相对 == "配置.json":
        return 配置_json发布版.encode("utf-8")
    if 相对 == "语音/程序目录.txt":
        return 程序目录_txt发布版.encode("utf-8")
    if 相对 in 沿用远端的:
        return 远端字节(相对)
    全 = os.path.join(项目根, 相对.replace("/", os.sep))
    if not os.path.isfile(全):
        return 远端字节(相对)
    if 相对.lower().endswith(二进制后缀):
        with open(全, "rb") as 文件:
            return 文件.read()
    with io.open(全, "r", encoding="utf-8", newline="") as 文件:
        文 = 文件.read()
    return 去注释(相对, 文).encode("utf-8")


def 算清单():
    新集 = {}
    for 根, 目录们, 文件们 in os.walk(项目根):
        目录们[:] = [d for d in 目录们 if d not in (".git", "__pycache__", "build", "dist")]
        for 名 in 文件们:
            相对 = os.path.relpath(os.path.join(根, 名), 项目根).replace(os.sep, "/")
            if 收吗(相对) and 相对 not in 新集:
                文 = 新字节(相对)
                if 文 is not None:
                    新集[相对] = 文
    for 相对 in 沿用远端的:
        if 相对 not in 新集 and 收吗(相对):
            文 = 新字节(相对)
            if 文 is not None:
                新集[相对] = 文

    旧集 = {}
    for p in 远端文件们():
        文 = 远端字节(p)
        if 文 is not None:
            旧集[p] = 文

    新增 = sorted(p for p in 新集 if p not in 旧集)
    删除 = sorted(p for p in 旧集 if p not in 新集)
    改了 = sorted(p for p in 新集 if p in 旧集 and 旧集[p] != 新集[p])
    没变 = sorted(p for p in 新集 if p in 旧集 and 旧集[p] == 新集[p])
    return 新集, 新增, 改了, 删除, 没变


def 核编译(新集):
    坏 = []
    for 相对, 文 in sorted(新集.items()):
        if not 相对.endswith(".py"):
            continue
        try:
            compile(文.decode("utf-8"), 相对, "exec")
        except (SyntaxError, UnicodeDecodeError) as 异常:
            坏.append("%s：%s" % (相对, str(异常)[:60]))
    return 坏


def 主程序():
    模式 = sys.argv[1] if len(sys.argv) > 1 else "清单"
    新集, 新增, 改了, 删除, 没变 = 算清单()

    坏 = 核编译(新集)
    if 坏:
        print("去注释后有 %d 个 .py 编译不过，不生成、也不该推：" % len(坏))
        for 一条 in 坏:
            print("   " + 一条)
        return 1

    print("发布版共 %d 个文件（远端现有 %d 个，其中没变的 %d 个）"
          % (len(新集), len(改了) + len(没变), len(没变)))
    print("  新增 %d   修改 %d   删除 %d" % (len(新增), len(改了), len(删除)))
    print()
    if 新增:
        print("【新增】")
        for p in 新增:
            print("   + " + p)
    if 删除:
        print()
        print("【删除】")
        for p in 删除:
            print("   - " + p)
    if 改了:
        print()
        print("【修改】")
        for p in 改了:
            print("   ~ " + p)

    if 模式 == "落地":
        目标 = sys.argv[2]
        if os.path.isdir(目标):
            shutil.rmtree(目标)
        for 相对, 文 in 新集.items():
            全 = os.path.join(目标, 相对.replace("/", os.sep))
            os.makedirs(os.path.dirname(全) or 目标, exist_ok=True)
            with open(全, "wb") as 文件:
                文件.write(文)
        print()
        print("已落地到 " + 目标 + "（" + str(len(新集)) + " 个文件）")

    print()
    print("清单算完了：新增 %d、修改 %d、删除 %d，%d 个 .py 全部编译得过"
          % (len(新增), len(改了), len(删除),
             sum(1 for p in 新集 if p.endswith(".py"))))
    return 0


if __name__ == "__main__":
    sys.exit(主程序())
