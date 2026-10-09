
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 配置, 注册表

注册表.全部加载(os.path.join(配置.根目录, "能力"))

from 能力 import _档案

端口 = 配置.取端口()
接口 = "http://127.0.0.1:" + str(端口) + "/api/run"
首页 = "http://127.0.0.1:" + str(端口) + "/"

试编号 = "_自检生"
试姓名 = "测试名字甲"
学生目录 = _档案.学生目录(试编号)
名册路径 = _档案.名册路径()
配置路径 = os.path.join(配置.根目录, "配置.json")
对照表路径 = _档案.对照表路径()


def 读文本(路径):
    if not os.path.isfile(路径):
        return ""
    with open(路径, "r", encoding="utf-8") as 文件:
        return 文件.read()

要写盘 = "--确认" in sys.argv
结果 = []


def 检查(名字, 通过):
    结果.append((名字, bool(通过)))


def 调用(能力, 参数=None, 超时=240):
    请求 = urllib.request.Request(
        接口,
        data=json.dumps({"能力": 能力, "参数": 参数 or {}},
                        ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Origin": "http://127.0.0.1:" + str(端口)},
        method="POST")
    try:
        with urllib.request.urlopen(请求, timeout=超时) as 响应:
            return 响应.status, json.loads(响应.read().decode("utf-8"))
    except urllib.error.HTTPError as 异常:
        正文 = 异常.read().decode("utf-8", "replace")
        try:
            正文 = json.loads(正文)
        except ValueError:
            pass
        return 异常.code, 正文
    except urllib.error.URLError as 异常:
        return 0, {"错误": "服务中途掉线：" + str(异常.reason)}


def 被拒(状态码, 正文):
    return 状态码 == 400 and isinstance(正文, dict) and bool(正文.get("错误"))


print("探活 " + 首页)
try:
    with urllib.request.urlopen(首页, timeout=5) as 响应:
        活的 = 响应.status == 200
except Exception as 异常:
    活的 = False
    print("  连不上：" + type(异常).__name__ + ": " + str(异常))
检查("服务活着（首页 200）", 活的)

if not 活的:
    print("\n服务没起。先跑 启动.bat，或者：python 本地服务.py")
    sys.exit(1)

能力接口 = "http://127.0.0.1:" + str(端口) + urllib.parse.quote("/api/能力")
with urllib.request.urlopen(能力接口, timeout=10) as 响应:
    已加载 = {一条["代号"] for 一条 in json.loads(响应.read().decode("utf-8"))["条目"]}
要新能力 = {"学生注册", "学生问答", "学生档案馆", "查看学生档案", "录入学生记录", "学生名册"}
缺的 = 要新能力 - 已加载
检查("服务是当前代码（6 个新能力都在）", not 缺的)
if 缺的:
    print("\n跑着的服务是旧进程，缺这几个能力：" + ", ".join(sorted(缺的)))
    print("重启服务再跑这个自检。")
    sys.exit(1)

if not 要写盘:
    print("\n只读探测到此为止。要跑完整链路（会临时改配置、建一个自检学生）请加 --确认：")
    print("  python 脚本/检查_学生链路_会写盘.py --确认")
    sys.exit(0 if all(通过 for _, 通过 in 结果) else 1)

备份 = tempfile.mkdtemp(prefix="邵新自检_")
备配置 = os.path.join(备份, "配置.json")
备名册 = os.path.join(备份, "名册.json")
备对照表 = os.path.join(备份, "姓名对照表.json")
有配置 = os.path.isfile(配置路径)
有名册 = os.path.isfile(名册路径)
有对照表 = os.path.isfile(对照表路径)
对照表原文 = 读文本(对照表路径)
名册原文 = 读文本(名册路径)
if 有配置:
    shutil.copy2(配置路径, 备配置)
if 有名册:
    shutil.copy2(名册路径, 备名册)
if 有对照表:
    shutil.copy2(对照表路径, 备对照表)
print("\n已备份：配置.json " + ("有" if 有配置 else "无")
      + " / 名册.json " + ("有" if 有名册 else "无")
      + " / 姓名对照表.json " + ("有" if 有对照表 else "无") + " → " + 备份)


def 还原():
    if 有配置:
        shutil.copy2(备配置, 配置路径)
    elif os.path.isfile(配置路径):
        os.remove(配置路径)
    if 有名册:
        shutil.copy2(备名册, 名册路径)
    elif os.path.isfile(名册路径):
        os.remove(名册路径)
    if 有对照表:
        os.makedirs(os.path.dirname(对照表路径), exist_ok=True)
        shutil.copy2(备对照表, 对照表路径)
    elif os.path.isfile(对照表路径):
        os.remove(对照表路径)
    shutil.rmtree(学生目录, ignore_errors=True)
    shutil.rmtree(备份, ignore_errors=True)
    print("已还原：配置.json / 名册.json / 姓名对照表.json 放回原样，"
          + 试编号 + " 已删除")


try:
    if os.path.isfile(配置路径):
        os.remove(配置路径)
    os.makedirs(os.path.dirname(名册路径), exist_ok=True)
    if os.path.isdir(学生目录):
        shutil.rmtree(学生目录, ignore_errors=True)
    with open(名册路径, "w", encoding="utf-8") as 文件:
        文件.write("[]")

    带码, 正文 = 调用("学生注册", {"编号": 试编号})
    检查("① 没签同意书时「注册」被拒（400 + 错误字段）", 被拒(带码, 正文))
    检查("① 被拒后没建出学生文件夹", not os.path.isdir(学生目录))

    带码, 正文 = 调用("学生问答", {"编号": 试编号, "技能包": "demo-real", "问题": "没签同意书能不能提问？"})
    检查("② 没签同意书时「提问」被拒", 被拒(带码, 正文))

    自定义 = {}
    if 有配置:
        with open(备配置, "r", encoding="utf-8") as 文件:
            自定义 = json.load(文件)
    自定义.setdefault("合规", {})["同意书已签"] = True
    with open(配置路径, "w", encoding="utf-8") as 文件:
        json.dump(自定义, 文件, ensure_ascii=False, indent=2)

    带码, 正文 = 调用("学生注册", {"编号": 试编号, "姓名": 试姓名, "学号": "2026001",
                                  "年级": "八年级", "班级": "3 班"})
    检查("③ 注册返回 200 且带提示", 带码 == 200 and bool(正文.get("提示")))
    检查("③ 注册后建出了该生文件夹", os.path.isdir(学生目录))
    with open(名册路径, "r", encoding="utf-8") as 文件:
        名册 = json.load(文件)
    检查("③ 名册里出现了这个编号", any(一条.get("编号") == 试编号 for 一条 in 名册))
    检查("③ 名册里没有姓名（姓名只进对照表）", 试姓名 not in 读文本(名册路径))
    检查("③ 对照表里存下了姓名", _档案.学生信息(试编号).get("姓名") == 试姓名)

    带码, 正文 = 调用("学生注册", {"编号": 试编号, "姓名": "测试名字乙", "年级": "九年级"})
    检查("④ 重复编号走「更新资料」而不是报错",
        带码 == 200 and "更新" in str(正文.get("提示", "")))
    检查("④ 更新后姓名真的改了", _档案.学生信息(试编号).get("姓名") == "测试名字乙")
    检查("④ 更新没有新建第二个文件夹、也没动记录", len(_档案.读记录(试编号)) == 0)
    带码, 正文 = 调用("学生注册", {"编号": 试编号, "姓名": ""})
    检查("④ 姓名为空仍然被拒（不许把已有姓名抹掉）", 被拒(带码, 正文))
    检查("④ 被拒后姓名还在", _档案.学生信息(试编号).get("姓名") == "测试名字乙")
    带码, 正文 = 调用("学生注册", {"编号": 试编号, "姓名": "测试名字甲", "年级": "八年级"})

    带码, 正文 = 调用("学生问答", {"编号": 试编号, "技能包": "demo-real",
                                  "问题": "分数的除法为什么可以变成乘以倒数？"})
    检查("⑤ 提问返回 200", 带码 == 200)
    回答 = str(正文.get("正文", "")) if isinstance(正文, dict) else ""
    检查("⑤ 返回了非空回答（说明真调到了模型）", len(回答.strip()) >= 10)
    if 带码 == 200 and len(回答.strip()) >= 10:
        print("     模型回答前 80 字：" + 回答.strip()[:80].replace("\n", " "))
    else:
        print("     ‼ 这一步是要联网、要花钱调模型的那一步。失败原文：")
        print("        带码=" + str(带码) + " 正文=" + json.dumps(正文, ensure_ascii=False)[:200])
        print("        这类失败先重跑一次：单次抖动很常见；连着红再看代码。")

    记录路径 = _档案.记录路径(试编号)
    检查("⑥ 记录.jsonl 落在该生文件夹", os.path.isfile(记录路径))
    记录 = _档案.读记录(试编号) if os.path.isfile(记录路径) else []
    检查("⑥ 记录里有且只有这一条", len(记录) == 1 and 记录[0].get("类别") == "问答")
    检查("⑥ 问题原样存下", 记录 and 记录[0].get("问题", "").startswith("分数的除法"))
    清单允许的键 = {"类别", "技能包", "问题", "时间"}
    多出来的 = (set(记录[0]) - 清单允许的键) if 记录 else {"（记录为空）"}
    检查("⑥ 记录只含采集清单允许的字段（AI 回答不入库）", not 多出来的)
    if 多出来的:
        print("     多出来的字段：" + "、".join(sorted(多出来的)))

    带码, 正文 = 调用("查看学生档案", {"编号": 试编号})
    条目 = 正文.get("条目", []) if isinstance(正文, dict) else []
    检查("⑦ 查看学生档案返回 200 且有 1 条", 带码 == 200 and len(条目) == 1)
    检查("⑦ 那条是「问答」类型且含所提问题",
        条目 and 条目[0].get("类型") == "问答" and "分数的除法" in str(条目[0].get("内容", "")))

    带码, 正文 = 调用("学生档案馆")
    一览 = {一条["编号"]: 一条 for 一条 in 正文.get("条目", [])}
    检查("⑧ 一览里能看到该生且条数为 1",
        带码 == 200 and 一览.get(试编号, {}).get("记录条数") == 1)

    带码, 正文 = 调用("录入学生记录", {"编号": 试编号, "学科": "数学",
                                     "题目": "3/4 ÷ 1/2 = ?", "作答": "3/2",
                                     "对错": "对", "错误类型": "计算失误"})
    if 带码 != 200:
        print("     录入被拒：" + str(正文.get("错误") if isinstance(正文, dict) else 正文)[:120])
    检查("⑨ 录入作答返回 200", 带码 == 200)
    带码, 正文 = 调用("查看学生档案", {"编号": 试编号})
    条目 = 正文.get("条目", []) if isinstance(正文, dict) else []
    检查("⑨ 档案变成 2 条，且出现「作答」类型",
        len(条目) == 2 and any(一条.get("类型") == "作答" for 一条 in 条目))

    带码, 正文 = 调用("学生问答", {"编号": "S99", "技能包": "demo-real", "问题": "我没注册能问吗？"})
    检查("⑩ 没注册的编号提问被拒", 被拒(带码, 正文))

    带码, 正文 = 调用("学生注册", {"编号": "../../坏蛋"})
    检查("⑪ 带路径的编号被拒", 被拒(带码, 正文))
    检查("⑪ 没在上一级建出目录",
        not os.path.exists(os.path.join(配置.根目录, "坏蛋")))
finally:
    try:
        还原()
    except OSError as 异常:
        结果.append(("收尾还原出问题：" + str(异常), False))

检查("⑫ 收尾后名册原样",
    (读文本(名册路径) == 名册原文) if 有名册 else (not os.path.isfile(名册路径)))
检查("⑬ 收尾后姓名对照表原样：自检没删到既有条目",
    (读文本(对照表路径) == 对照表原文) if 有对照表 else (not os.path.isfile(对照表路径)))
检查("⑭ 自检生的文件夹已删掉", not os.path.isdir(学生目录))

坏的 = 0
print()
for 名字, 通过 in 结果:
    print(("  通过  " if 通过 else "  失败  ") + 名字)
    坏的 += 0 if 通过 else 1
print("全部 %d 项通过" % len(结果) if not 坏的 else "%d 项失败" % 坏的)
sys.exit(0 if not 坏的 else 1)
