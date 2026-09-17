
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 注册表, 工具箱, 配置

注册表.全部加载(os.path.join(配置.根目录, "能力"))

问题 = []


def 找真处理函数(处理函数):
    绑定 = getattr(处理函数, "__绑定能力__", None)
    if 绑定:
        return 注册表.取能力(绑定)["处理函数"]
    return 处理函数


def 查一处(种类, 名字, 处理函数, 声明的代号):
    处理函数 = 找真处理函数(处理函数)
    形参 = list(inspect.signature(处理函数).parameters)
    配对 = {}
    剩余 = list(形参)
    for 代号 in 声明的代号:
        if 代号 in 形参:
            配对[代号] = "按名字"
            剩余.remove(代号)
        elif 剩余:
            配对[代号] = "→ 实际是 " + 剩余.pop(0)
        else:
            配对[代号] = "← 函数根本没有这个参数"
    对不上的 = [代号 for 代号, 方式 in 配对.items() if 方式 != "按名字"]
    if 剩余:
        对不上的 += ["（形参 %s 没在声明里）" % 名 for 名 in 剩余]
    if 对不上的:
        问题.append((种类, 名字, 对不上的, 配对, 形参))


for 代号 in 注册表.全部名字():
    条目 = 注册表.已登记能力[代号]
    查一处("能力", 代号, 条目["处理函数"], [一项["代号"] for 一项 in 条目["参数"]])

for 工具名 in 工具箱.全部名字():
    条目 = 工具箱.已登记工具[工具名]
    查一处("工具", 工具名, 条目["处理函数"], [一项["代号"] for 一项 in 条目["参数"]])

if not 问题:
    print("  全部 %d 个能力和 %d 个工具的参数契约都对得上"
          % (len(注册表.全部名字()), len(工具箱.全部名字())))
    sys.exit(0)

print("  有 %d 处对不上：" % len(问题))
for 种类, 名字, 对不上的, 配对, 形参 in 问题:
    print("    [%s] %s" % (种类, 名字))
    print("        声明：%s" % [一项 for 一项 in 配对])
    print("        形参：%s" % 形参)
    print("        对不上的：%s" % 对不上的)
sys.exit(1)
