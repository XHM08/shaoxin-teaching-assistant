
import importlib.util
import os
import re
import subprocess
import sys

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)

打包脚本 = os.path.join(根, "脚本", "打包.py")
exe路径 = os.path.join(根, "dist", "邵新", "邵新.exe")

失败 = []
条数 = 0


def 记(名, 通过, 说明=""):
    global 条数
    条数 += 1
    print(("  ✓ " if 通过 else "  ✗ ") + 名 + ("" if 通过 else "　→　" + str(说明)))
    if not 通过:
        失败.append(名)


def 载入打包():
    spec = importlib.util.spec_from_file_location("打包巡检", 打包脚本)
    模块 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(模块)
    return 模块


def 源版本号():
    文本 = open(os.path.join(根, "地基", "版本.py"), encoding="utf-8").read()
    匹配 = re.search(r'版本号\s*=\s*"([^"]+)"', 文本)
    return 匹配.group(1) if 匹配 else None


def exe属性(路径):
    脚本 = ("$v = (Get-Item -LiteralPath '" + 路径 + "').VersionInfo; Write-Output ($v.ProductName"
           " + [char]124 + $v.FileVersion + [char]124 + $v.ProductVersion + [char]124 + $v.OriginalFilename)")
    跑 = subprocess.run(['powershell.exe', '-NoProfile', '-Command', 脚本],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
    行 = [x for x in (跑.stdout or '').splitlines() if x.count(chr(124)) >= 3]
    if not 行:
        return {}
    段 = 行[-1].strip().split(chr(124))
    return {'产品名': 段[0], '文件版本': 段[1], '产品版本': 段[2], '原始文件名': 段[3]}


def 跑检查():
    号 = 源版本号()
    记("① 地基/版本.py 里的版本号读得到，且形如 x.y.z",
       bool(号) and bool(re.fullmatch(r"\d+\.\d+\.\d+", 号)), 号)

    打包 = 载入打包()
    路, 生成号 = 打包.生成版本信息()
    内容 = open(路, encoding='utf-8').read()
    记("② 生成的版本资源文件里，FileVersion 与 ProductName 都对",
       ("StringStruct('FileVersion', '%s')" % 号) in 内容 and 'ProductName' in 内容
       and '邵新 辅助教育系统' in 内容, 内容[:120])
    记("③ 生成函数用的版本号与源码里那个一致", 生成号 == 号, "%s vs %s" % (生成号, 号))

    四段 = re.search(r"filevers=\(([^)]*)\)", 内容)
    期望 = tuple(int(x) if x.isdigit() else 0 for x in (号 or "0.0.0").split(".")) + (0,)
    记("④ 版本四段元组与版本号对应",
       bool(四段) and "(" + 四段.group(1).replace(' ', '') + ")" == "(%d,%d,%d,%d)" % 期望[:4],
       四段.group(1) if 四段 else "找不到 filevers")

    记("⑤ spec 里确实挂上了版本资源文件",
       'version=os.path.join(SPEC, "脚本", "版本信息.txt")' in open(os.path.join(根, "邵新.spec"), encoding="utf-8").read(),
       "邵新.spec 里的 version= 那行没了")

    if not os.path.isfile(exe路径):
        print("  … exe 不存在（没构建过）：属性读取这一项未验证，按跳过处理")
        return 3

    属性 = exe属性(exe路径)
    记("⑥ 真 exe 的属性里产品名是「邵新 辅助教育系统」", 属性.get('产品名') == '邵新 辅助教育系统', 属性)
    记("⑦ 真 exe 的文件版本以源码版本号开头",
       (属性.get('文件版本') or '').startswith(号), 属性.get('文件版本'))
    记("⑧ 原始文件名是 邵新.exe", 属性.get('原始文件名') == '邵新.exe', 属性.get('原始文件名'))
    return 0


def 主():
    码 = 0
    try:
        码 = 跑检查()
    except Exception as 错:
        记("检查本身跑完了", False, "%s: %s" % (type(错).__name__, 错))
        码 = 1
    print()
    if 失败:
        print("通过 %d / 共 %d" % (条数 - len(失败), 条数))
        return 1
    print("全部 %d 项通过" % 条数)
    return 码


if __name__ == "__main__":
    sys.exit(主())
