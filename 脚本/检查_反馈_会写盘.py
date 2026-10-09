
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 注册表

注册表.全部加载(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "能力"))

from 能力 import _反馈 as 后
from 能力 import _教师数据
import 能力.反馈 as F

if "--确认" not in sys.argv:
    print("  这个自检会真的写盘（教师数据/）。")
    print("  它跑之前先备份、跑完无条件还原；确认要跑就加上 --确认。")
    sys.exit(2)

结果 = []


def 记(名字, 通过, 说明):
    结果.append((名字, bool(通过), 说明))


def 试(动作):
    try:
        return True, 动作()
    except Exception as 异常:
        return False, 异常


def 拒了吗(动作, 关键词=""):
    try:
        值 = 动作()
    except ValueError as 异常:
        if 关键词 and 关键词 not in str(异常):
            return False, "拒是拒了，但话不对：" + str(异常)[:40]
        return True, "拒了：" + str(异常)[:40]
    return False, "居然放行了，拿到：" + str(值)[:40]


def 快照(目录):
    if not os.path.isdir(目录):
        return []
    们 = []
    for 名 in sorted(os.listdir(目录)):
        全 = os.path.join(目录, 名)
        if os.path.isfile(全):
            状 = os.stat(全)
            们.append((名, 状.st_size, 状.st_mtime_ns))
    return 们


教师数据 = _教师数据.数据目录()
根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
备份根 = tempfile.mkdtemp(prefix="反馈自检备份_")
原来就有 = os.path.isdir(教师数据)
if 原来就有:
    shutil.copytree(教师数据, os.path.join(备份根, "教师数据"))
    shutil.rmtree(教师数据, ignore_errors=True)

真问 = F.大模型.问
真审计 = F.审计.记一笔
审计们 = []
F.大模型.问 = lambda *a, **k: "定位：x\n建议改动：y\n要动哪几个文件：z\n怎么验证：w\n风险：v"
F.审计.记一笔 = lambda *a, **k: 审计们.append((a, k))

try:
    甲 = F.处理记反馈("不好用", "手机版按回车不提交")
    乙 = F.处理记反馈("想要新功能", "希望有班级错因热力图", "手机版")
    记("① 空池里第一条的号是 1", 甲["反馈编号"] == 1, "实际：" + str(甲["反馈编号"]))
    记("② 第二条的号接着涨", 乙["反馈编号"] == 2, "实际：" + str(乙["反馈编号"]))

    清单 = F.处理清单("全部")
    记("③ 清单里两条都在、都是「未处理」",
       len(清单["条目"]) == 2 and all(一["状态"] == "未处理" for 一 in 清单["条目"]),
       "拿到 " + str(len(清单["条目"])) + " 条")

    好, 说明 = 拒了吗(lambda: F.处理记反馈("很好用", "x"), "反馈类型只能是")
    记("④ 自造的反馈类型被拒", 好, 说明)
    好, 说明 = 拒了吗(lambda: F.处理记反馈("不好用", "   "), "不能为空")
    记("⑤ 空内容被拒", 好, 说明)
    好, 说明 = 拒了吗(lambda: F.处理记反馈处理(1, "搞定"), "处理结果只能是")
    记("⑥ 自造的处理结果被拒（要按结果统计就不能自由填）", 好, 说明)

    好1, 说1 = 拒了吗(lambda: F.处理记反馈处理(99, "已修"), "没有编号 99")
    好2, 说2 = 拒了吗(lambda: F.处理诊断(99), "没有编号 99")
    好3, 说3 = 拒了吗(lambda: F.处理诊断("x"), "要写数字")
    记("⑦ 不存在的编号、不是数字的编号都被拒", 好1 and 好2 and 好3,
       "｜".join([说1[:16], 说2[:16], 说3[:16]]))

    F.处理记反馈处理(1, "已修", "abc1234", "顺手加了回车提交")
    已处 = F.处理清单("已处理")["条目"]
    未处 = F.处理清单("未处理")["条目"]
    记("⑧ 记完处理：已处理 1 条、未处理 1 条，提交号与用时都带出来了",
       len(已处) == 1 and len(未处) == 1 and 已处[0]["提交号"] == "abc1234"
       and 已处[0]["处理用时小时"] is not None,
       "已处理 %d／未处理 %d，提交号 %s，用时 %s"
       % (len(已处), len(未处), 已处[0]["提交号"], 已处[0]["处理用时小时"]))

    允许 = {"反馈编号", "状态", "类型", "内容", "影响面", "结果", "提交号",
           "处理说明", "时间", "处理时间", "处理用时小时"}
    多出来 = set()
    for 一 in F.处理清单("全部")["条目"]:
        多出来 |= set(一) - 允许
    记("⑨ 清单里没有多余字段（反馈是教师侧材料，不该夹带学生信息）",
       not 多出来, "多出来：" + "、".join(sorted(多出来)))

    坏 = os.path.join(教师数据, "_自检坏行.jsonl")
    with open(坏, "w", encoding="utf-8") as 文件:
        文件.write('{"反馈编号": 1, "内容": "半截')
    好, 说 = 拒了吗(lambda: _教师数据.读JSONL(坏, "反馈.jsonl"), "不会覆盖")
    记("⑩ 半截 JSON 读不出来时**报错**，不是返回空", 好, 说)
    if os.path.isfile(坏):
        os.remove(坏)

    守 = [
        ("跳出项目目录", ["../密钥/服务商.json"], ".."),
        ("绝对路径", ["C:/Windows/win.ini"], "绝对路径"),
        ("密钥/ 里的东西", ["密钥/服务商.json"], "密钥"),
        ("学生数据/ 里的东西", ["学生数据/名册.json"], "学生数据"),
        ("教师数据/ 里的东西", ["教师数据/反馈.jsonl"], "教师数据"),
        ("点斜杠前缀绕密钥禁区", ["./密钥/服务商.json"], "密钥"),
        ("点斜杠前缀绕学生数据禁区", ["./学生数据/名册.json"], "学生数据"),
    ]
    漏的 = []
    for 说明文字, 路径们, 关键词 in 守:
        try:
            F.读代码(路径们)
            漏的.append(说明文字)
        except ValueError as 异常:
            if 关键词 not in str(异常):
                pass
    记("⑪ 路径守卫：五类越界路径全拒（读出来的代码是要发到外部的）", not 漏的,
       "漏了：" + "、".join(漏的) if 漏的 else "五类全拒")

    正常片段, 读过的 = F.读代码(["地基/版本.py"])
    记("⑫ 项目内的正常文件读得到（守卫不是把路全堵死）",
       bool(正常片段) and 读过的 == ["地基/版本.py"],
       "读到 " + str(读过的) + "，共 " + str(sum(len(x) for x in 正常片段)) + " 字")

    前 = 快照(教师数据)
    出 = F.处理诊断(1, "地基/版本.py")
    后快 = 快照(教师数据)
    记("⑬ 反馈诊断一个字都不改（教师数据目录的大小与修改时间都没变）",
       前 == 后快 and "没有写任何文件" in 出["提示"] and bool(出["正文"]),
       "目录快照变化：" + str(len(set(前) ^ set(后快))) + " 处")
    好, 说 = 拒了吗(lambda: F.处理诊断(1, "学生数据/名册.json"), "学生数据")
    记("⑭ 诊断时点到禁区也拒（不能借诊断把学生数据发出去）", 好, 说)

    诊断审计 = [a[1] for a, _k in 审计们
              if a and a[0] == "反馈诊断" and len(a) > 1]
    处理审计 = [a[1] for a, _k in 审计们
              if a and a[0] == "记反馈处理" and len(a) > 1]
    记("⑮ 审计里带上了反馈编号与提交号（「反馈→提交」这条链接得上）",
       bool(诊断审计) and "反馈编号" in 诊断审计[0]
       and bool(处理审计) and 处理审计[0].get("提交号") == "abc1234",
       "诊断：" + str(诊断审计[0] if 诊断审计 else "无")
       + " ｜ 处理：" + str(处理审计[0] if 处理审计 else "无"))

    学生侧 = []
    for 名字 in ("学生问答.py", "学生注册.py"):
        路径 = os.path.join(根, "能力", 名字)
        if os.path.isfile(路径):
            with open(路径, "r", encoding="utf-8", errors="replace") as 文件:
                学生侧.append((名字, 文件.read()))
    越界的 = [名字 for 名字, 正文 in 学生侧
            if "记反馈" in 正文 or "_反馈" in 正文 or "反馈.jsonl" in 正文]
    记("⑯ 学生侧的能力实现里没有反馈入口（反馈不属采集三项，存了就越界）",
      bool(学生侧) and not 越界的,
      "查了 " + str(len(学生侧)) + " 个学生侧能力文件；越界调用：" + (str(越界的) if 越界的 else "无"))
except Exception as 异常:
    记("自检半路出错", False, type(异常).__name__ + "：" + str(异常)[:70])
finally:
    F.大模型.问 = 真问
    F.审计.记一笔 = 真审计
    shutil.rmtree(教师数据, ignore_errors=True)
    if 原来就有:
        shutil.copytree(os.path.join(备份根, "教师数据"), 教师数据)
    shutil.rmtree(备份根, ignore_errors=True)

坏的 = 0
print()
for 名字, 通过, 说明 in 结果:
    print(("  通过  " if 通过 else "  失败  ") + 名字 + ("　→　" + 说明 if 说明 else ""))
    坏的 += 0 if 通过 else 1
print("全部 %d 项通过" % len(结果) if not 坏的 else "%d 项失败" % 坏的)
sys.exit(0 if not 坏的 else 1)
