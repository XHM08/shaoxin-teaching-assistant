
import io
import os
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 配置

结果 = []


def 检查(名字, 通过, 说明=""):
    结果.append((名字, bool(通过), 说明))


def _试试(模块, 角色):
    try:
        模块.子进程命令(角色, 冻结=False)
        return False
    except ValueError:
        return True
    except Exception:
        return False


def _空端口():
    套 = socket.socket()
    try:
        套.bind(("127.0.0.1", 0))
        return 套.getsockname()[1]
    finally:
        套.close()


def main():
    根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    检查("源码模式下 取根目录() 指向 样本/",
        配置.取根目录(冻结=False) == 根,
        "得到 " + 配置.取根目录(冻结=False))

    检查("冻结模式下 取根目录(True) 指向 exe 所在目录",
        配置.取根目录(冻结=True) == os.path.dirname(os.path.abspath(sys.executable)),
        "得到 " + 配置.取根目录(冻结=True))

    检查("模块级 根目录 是字符串且存在",
        isinstance(配置.根目录, str) and os.path.isdir(配置.根目录),
        配置.根目录)

    import 主程序 as 入口
    可分发 = getattr(入口, "认识这个命令", None)
    检查("主程序 暴露了 认识这个命令()", callable(可分发))
    if callable(可分发):
        检查("认 客户端", 可分发("客户端"))
        检查("认 服务", 可分发("服务"))
        检查("认 悬浮窗", 可分发("悬浮窗"))
        检查("认原有的 列出 / 运行 / 工具 / 起服务",
            all(可分发(x) for x in ("列出", "运行", "工具", "起服务")))
        检查("不认乱写的命令", not 可分发("随便写点什么"))

    from 地基 import WebView2
    检查("注册表有 → 算装了，版本取注册表的",
        WebView2.判定("154.0.4258.62", "") == (True, "154.0.4258.62", "注册表"))
    检查("只有目录有 → 也算装了",
        WebView2.判定("", "154.0.4258.53") == (True, "154.0.4258.53", "安装目录"))
    检查("两处都没有 → 没装", WebView2.判定("", "")[0] is False)
    检查("两处都有 → 以注册表为准（那是权威版本号）",
        WebView2.判定("154.0.4258.62", "154.0.4258.53")[1] == "154.0.4258.62")

    假边 = os.path.abspath(__file__)
    不存在的边 = os.path.join(os.path.dirname(假边), "这个文件不存在-用来验回退.exe")
    命令 = WebView2.回退命令("http://127.0.0.1:8765", 候选=[假边])
    检查("有 Edge 时回退命令是 msedge --app=<地址>",
        命令 is not None and 命令[0] == 假边 and 命令[1] == "--app=http://127.0.0.1:8765",
        str(命令))
    检查("回退命令带窗口尺寸",
        命令 is not None and any(x.startswith("--window-size=") for x in 命令), str(命令))
    检查("连 Edge 也找不到时回退命令是 None（不编一个假命令）",
        WebView2.回退命令("http://127.0.0.1:8765", 候选=[不存在的边]) is None)

    import inspect

    import 桌面客户端

    冻结命令 = 桌面客户端.子进程命令("服务", 冻结=True)
    检查("冻结时用 exe 自身 + 角色参数",
        冻结命令[0] == sys.executable and 冻结命令[-1] == "服务", str(冻结命令))
    检查("源码时 服务 指向 本地服务.py（不是 服务.py）",
        桌面客户端.子进程命令("服务", 冻结=False)[-1].endswith("本地服务.py"),
        str(桌面客户端.子进程命令("服务", 冻结=False)))
    源码命令 = 桌面客户端.子进程命令("悬浮窗", 冻结=False)
    检查("源码时用 python + 脚本路径，且那个脚本真的在",
        源码命令[0] == sys.executable and os.path.isfile(源码命令[-1]), str(源码命令))
    检查("不认识的角色会抛 ValueError（不静默拼一个假路径）",
        _试试(桌面客户端, "乱写") is True)

    空口 = _空端口()
    检查("没人听的端口 → 有人听吗() 是假", 桌面客户端.有人听吗(空口) is False)

    起 = time.time()
    成了 = 桌面客户端.等端口(空口, 超时秒=2)
    用了 = time.time() - 起
    检查("等一个没人听的端口 → 返回假（不假装成功）", 成了 is False)
    检查("等端口真的等满了超时（不是立刻返回）", 用了 >= 1.8, "用了 %.1f 秒" % 用了)

    假 = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    强杀数 = None
    try:
        强杀数 = 桌面客户端.收队([假], 超时秒=1)
    except Exception as 异常:
        强杀数 = "抛异常：" + type(异常).__name__
    finally:
        if 假.poll() is None:
            假.kill()
    检查("收队之后那个进程真的没了", 假.poll() is not None, "poll=" + str(假.poll()))
    检查("收队报告了强杀个数（0 或 1 都合理）", 强杀数 in (0, 1), str(强杀数))

    检查("提示() 存在", callable(getattr(桌面客户端, "提示", None)))

    原_stderr = sys.stderr
    sys.stderr = io.StringIO()
    try:
        桌面客户端.提示("自检探针：这条不该真的弹窗")
        出了 = sys.stderr.getvalue()
    finally:
        sys.stderr = 原_stderr
    检查("提示() 真的写到了 stderr（源码模式）", "自检探针" in 出了, 出了.strip()[:40])

    检查("【静态】主程序() 的源码里没有裸 print",
        "print(" not in inspect.getsource(桌面客户端.主程序))

    日志文件 = os.path.join(配置.根目录, "日志", "客户端-悬浮窗.log")
    原来就有日志 = os.path.isfile(日志文件)
    原_命令 = 桌面客户端.子进程命令
    桌面客户端.子进程命令 = lambda 角色, 冻结=None: [
        sys.executable, "-c", "import time; time.sleep(60)"]
    甲 = 乙 = None
    起了几个 = 0
    说明起不来 = ""
    try:
        桌面客户端.角色进程.pop("悬浮窗", None)
        甲 = 桌面客户端.起悬浮窗()
        乙 = 桌面客户端.起悬浮窗()
        起了几个 = len([p for p in 桌面客户端.子进程们 if p.poll() is None])
    except Exception as 异常:
        起了几个 = -1
        甲 = 乙 = None
        说明起不来 = type(异常).__name__ + "：" + str(异常)[:50]
    finally:
        桌面客户端.子进程命令 = 原_命令
        桌面客户端.收队(list(桌面客户端.子进程们), 超时秒=1)
        桌面客户端.子进程们[:] = []
        桌面客户端.角色进程.pop("悬浮窗", None)
        if not 原来就有日志 and os.path.isfile(日志文件):
            try:
                os.remove(日志文件)
            except OSError:
                pass

    检查("悬浮窗：连点两次只起了一个进程",
        起了几个 == 1,
        "起了 %d 个%s" % (起了几个, ("　" + 说明起不来) if 说明起不来 else ""))
    检查("悬浮窗：连点两次拿到同一个对象", 甲 is not None and 甲 is 乙,
        "甲有=%s 乙有=%s 同一个=%s" % (甲 is not None, 乙 is not None, 甲 is 乙))

    print()
    坏 = 0
    for 名字, 过, 说明 in 结果:
        print(("  通过  " if 过 else "  失败  ") + 名字 + ("　→　" + 说明 if 说明 else ""))
        坏 += 0 if 过 else 1
    print("全部 %d 项通过" % len(结果) if not 坏 else "%d 项失败" % 坏)
    return 0 if not 坏 else 1


if __name__ == "__main__":
    sys.exit(main())
