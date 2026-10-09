
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import MCP, 工具箱

本目录 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
自检服务器 = os.path.join(本目录, "脚本", "_自检MCP服务器.py")

结果 = []
没拿到 = object()


def 检查(名字, 通过, 说明=""):
    结果.append((名字, bool(通过), 说明))


def 试(动作):
    try:
        return True, 动作()
    except Exception as 异常:
        return False, 异常


def 简述(异常):
    return type(异常).__name__ + "：" + str(异常).splitlines()[0][:110]


def 查(名字, 动作, 判据=None, 抓=None):
    if 抓 is None:
        好, 东西 = 试(动作)
        if not 好:
            检查(名字, False, 简述(东西))
            return 没拿到
    else:
        好, 东西 = 试(动作)
        if 好:
            检查(名字, False, "居然没抛异常，拿到：" + str(东西)[:60])
            return 没拿到
        if not isinstance(东西, 抓):
            检查(名字, False, "抛的不是 " + 抓.__name__ + "，而是 " + type(东西).__name__)
            return 没拿到
    if 判据 is None:
        检查(名字, True)
    else:
        通过, 说明 = 判据(东西)
        检查(名字, 通过, 说明)
    return 东西


def 起服务器(超时=20):
    return MCP.服务器("自检", sys.executable, [自检服务器], 超时=超时).启动()


def 写文件(路径, 内容):
    with open(路径, "w", encoding="utf-8") as 文件:
        文件.write(内容)


def 转义(路径):
    return 路径.replace("\\", "\\\\")


def 进程还在吗(进程号):
    if not 进程号:
        return False
    任务表 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                        "System32", "tasklist.exe")
    try:
        跑完 = subprocess.run([任务表, "/FI", "PID eq " + str(进程号), "/NH"],
                            capture_output=True, text=True, timeout=15)
    except Exception:
        return False
    return str(进程号) in (跑完.stdout or "")


服 = None
起着的 = None
临时目录 = tempfile.mkdtemp(prefix="MCP自检_")
try:
    服 = 查("01 握手成功（含协商版本）", 起服务器,
           lambda 个: (bool(个.服务器信息) and bool(个.协商版本),
                      "对方自称「%s」，版本 %s"
                      % (个.服务器信息.get("name"), 个.协商版本)))

    if 服 is not 没拿到:
        工具们 = 查("02 列得出六个工具", 服.列工具,
                  lambda 们: (len(们) == 6, "拿到：" + "、".join(一["名字"] for 一 in 们)))
        if 工具们 is not 没拿到:
            回声 = [一 for 一 in 工具们 if 一["名字"] == "回声"]
            检查("03 参数的 JSON Schema 带过来了",
                bool(回声) and "话" in (回声[0]["参数格式"].get("properties") or {}),
                str(回声[0]["参数格式"])[:100] if 回声 else "没找到「回声」")
        else:
            检查("03 参数的 JSON Schema 带过来了", False, "上一步没列出工具，无从核对")

        查("04 正常调用拿得到原文", lambda: 服.调工具("回声", {"话": "你好"}),
          lambda 答: (答[0] == "你说的是：你好" and 答[1] is False,
                     "实际：" + str(答[0])[:60]))

        查("05 认得服务器自报的 isError（且不把它当成功）",
          lambda: 服.调工具("报错", {}),
          lambda 答: ("服务器说这次工具执行出错" in 答[0] and "故意失败" in 答[0]
                     and 答[1] is True,
                     "实际：%s ｜ 自报出错=%s" % (str(答[0])[:50], 答[1])))

        开始 = time.monotonic()
        查("06 对方写两万行 stderr 也不卡死", lambda: 服.调工具("写日志", {}),
          lambda 答: ("写了两万行日志" in 答[0] and 答[1] is False,
                     "用了 %.1f 秒" % (time.monotonic() - 开始)))

        try:
            服.超时 = 2.0
            开始 = time.monotonic()
            好, 东西 = 试(lambda: 服.调工具("卡住", {}))
            用时 = time.monotonic() - 开始
            if 好:
                检查("07 不回话时会超时（不是一直挂着）", False, "居然没超时")
            elif isinstance(东西, MCP.出错):
                检查("07 不回话时会超时（不是一直挂着）",
                    "超时" in str(东西) and 用时 < 10,
                    "等了 %.1f 秒后报：%s" % (用时, str(东西)[:80]))
            else:
                检查("07 不回话时会超时（不是一直挂着）", False,
                    "抛的不是 MCP.出错，而是 " + type(东西).__name__)
        finally:
            服.超时 = 20

        查("08 超时后会发取消通知", lambda: 服.调工具("查取消", {}),
          lambda 答: ("收到过的取消：[]" not in 答[0],
                     "对方说：" + str(答[0])[:80]))

        查("09 服务器回 JSON-RPC 错误时会报错",
          lambda: 服.调工具("根本没有这个工具", {}),
          判据=lambda 答: ("没有这个工具" in str(答), str(答)[:80]),
          抓=MCP.出错)

        替身 = None
        try:
            替身 = 起服务器()
        except Exception as 异常:
            检查("10 服务器半路退出时给得出看得懂的说明", False, 简述(异常))
        if 替身 is not None:
            try:
                好, 东西 = 试(lambda: 替身.调工具("退出", {}))
                if 好:
                    检查("10 服务器半路退出时给得出看得懂的说明", False,
                        "它没退出，拿到了：" + str(东西)[:50])
                elif isinstance(东西, MCP.出错):
                    检查("10 服务器半路退出时给得出看得懂的说明",
                        "退出" in str(东西), str(东西)[:100])
                else:
                    检查("10 服务器半路退出时给得出看得懂的说明", False,
                        "抛的不是 MCP.出错，而是 " + type(东西).__name__)
            finally:
                试(替身.关闭)

        早就关掉的 = 服
        进程对象 = 服.进程
        服 = None
        关成功 = True
        try:
            早就关掉的.关闭()
        except Exception as 异常:
            关成功 = False
            检查("11 关闭之后子进程真的退出了", False, 简述(异常))
        if 关成功 and 进程对象 is not None:
            检查("11 关闭之后子进程真的退出了", 进程对象.poll() is not None,
                "子进程还活着" if 进程对象.poll() is None else "已退出")

        查("12 关闭后再调用会明确报错",
          lambda: 早就关掉的.调工具("回声", {"话": "x"}), 判据=None, 抓=MCP.出错)

    读回来 = 查("13 没有配置文件时 = 不挂任何服务器",
               lambda: MCP.读配置(os.path.join(临时目录, "根本没有这个文件.json")),
               lambda 表: (表["启用"] is False and 表["服务器们"] == [], str(表)))

    关着 = os.path.join(临时目录, "关着.json")
    写文件(关着, '{"启用": false, "服务器们": [{"名字":"随便","命令":"'
           + 转义(sys.executable) + '"}]}')
    查("14 配置里「启用: false」时一个都不起",
       lambda: MCP.起全部(MCP.读配置(关着)),
       lambda 起的: (起的 == [], "起了 %d 个" % len(起的)))

    坏的配置 = os.path.join(临时目录, "坏的.json")
    写文件(坏的配置, '{"启用": true, "服务器们": ['
           '{"名字":"不存在的命令","命令":"绝对没有这个程序xyz"},'
           '{"名字":"正常的","命令":"' + 转义(sys.executable) + '",'
           '"参数":["' + 转义(自检服务器) + '"]}]}')
    日志 = []
    起着的 = 查("15 坏服务器被跳过、好服务器照起",
               lambda: MCP.起全部(MCP.读配置(坏的配置), 记录=日志.append),
               lambda 起的: (len(起的) == 1 and any("没起来" in 一条 for 一条 in 日志),
                            "起了一个；日志：" + " ｜ ".join(日志)[:130]))
    if 起着的 is not 没拿到:
        for 一个 in 起着的:
            试(一个.关闭)
        起着的 = None

    坏json = os.path.join(临时目录, "坏json.json")
    写文件(坏json, '{"启用": true,,}')
    查("16 配置文件写坏时明确报错，不静默当没有",
       lambda: MCP.读配置(坏json), 判据=None, 抓=MCP.出错)

    pid文件 = os.path.join(临时目录, "哑巴.pid")
    哑巴脚本 = ("import os,time,sys;"
              "open(sys.argv[1],'w').write(str(os.getpid()));"
              "time.sleep(60)")
    哑巴 = MCP.服务器("哑巴", sys.executable, ["-c", 哑巴脚本, pid文件], 超时=1.0)
    好, 东西 = 试(哑巴.启动)
    子进程号 = ""
    for 次 in range(20):
        if os.path.isfile(pid文件):
            子进程号 = open(pid文件, "r", encoding="utf-8").read().strip()
            if 子进程号:
                break
        time.sleep(0.1)
    time.sleep(1.5)
    还活着 = 进程还在吗(子进程号)
    检查("17 握手失败不会把子进程留在本机上",
       (not 好) and isinstance(东西, MCP.出错) and bool(子进程号) and not 还活着,
       "子进程 %s；现在 %s" % (子进程号 or "（没拿到 pid）",
                             "还活着 ✗" if 还活着 else "已收掉 ✓"))

    接不上的 = os.path.join(临时目录, "接不上.json")
    写文件(接不上的, '{"启用": true,,}')
    第一次说话 = []
    第一回 = 工具箱.接上MCP(记录=第一次说话.append, 配置路径=接不上的)
    写文件(接不上的, '{"启用": true, "服务器们": [{"名字":"自检二号","命令":"'
           + 转义(sys.executable) + '","参数":["' + 转义(自检服务器) + '"]}]}')
    第二次说话 = []
    第二回 = 工具箱.接上MCP(记录=第二次说话.append, 配置路径=接不上的)
    检查("18 读配置失败不算「做过了」，改好之后同一次运行里还能再试",
       (第一回 == [] and any("读不了" in 一条 for 一条 in 第一次说话)
        and len(第二回) == 1 and any("已连上" in 一条 for 一条 in 第二次说话)),
       "第一次：%s ｜ 第二次：%s"
       % (" ｜ ".join(第一次说话)[:40],
          " ｜ ".join(第二次说话)[:60] or "（一个字都没说 —— 它没去读）"))
    for 一个 in 第二回:
        试(一个.关闭)
except Exception as 异常:
    检查("自检半路出错", False, 简述(异常))
finally:
    if 服 is not None:
        试(服.关闭)
    for 一个 in (起着的 or []):
        试(一个.关闭)
    shutil.rmtree(临时目录, ignore_errors=True)

坏的 = 0
print()
for 名字, 通过, 说明 in 结果:
    print(("  通过  " if 通过 else "  失败  ") + 名字 + ("　→　" + 说明 if 说明 else ""))
    坏的 += 0 if 通过 else 1
_跑命令类 = next((x for x in 工具箱.全部名字() if "命令" in x), None)
if _跑命令类 is None:
    检查("补齐参数：认对的按名字留下、不认的按序补到空位上（不顶掉）", False,
       "工具箱里找不到跟命令有关的工具 —— 这条没验成")
else:
    _补 = 工具箱._补齐参数(_跑命令类, {"命令": "echo 甲", "why": "看看"})
    检查("补齐参数：认对的按名字留下、不认的按序补到空位上（不顶掉）",
       _补.get("命令") == "echo 甲" and len(_补) == 2, str(_补))

print("全部 %d 项通过" % len(结果) if not 坏的 else "%d 项失败" % 坏的)
sys.exit(0 if not 坏的 else 1)
