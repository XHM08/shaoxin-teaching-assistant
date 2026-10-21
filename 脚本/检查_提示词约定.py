
import os
import re
import sys

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
提示词 = os.path.join(根, "提示词")
文件 = os.path.join(提示词, "创造模式.md")
课件提示 = os.path.join(提示词, "课件生成.md")

失败 = []
条数 = 0


def 记(名, 通过, 说明=""):
    global 条数
    条数 += 1
    print(("  ✓ " if 通过 else "  ✗ ") + 名 + ("" if 通过 else "　→　" + str(说明)))
    if not 通过:
        失败.append(名)


def 加载():
    原 = open(文件, encoding="utf-8").read()
    return 原


def 检查(原文, 文件名="创造模式.md"):
    问题 = []
    要有 = [
        ("尊重老师", "尊重老师"),
        ("不替老师判定怎么教", "别替她判定该怎么教"),
        ("测试阶段尽量照办", "测试阶段"),
        ("学生数据是硬底线", "硬底线"),
        ("A 只有开发团队能给", "只有开发团队能给"),
        ("XR 后跟字母", "后跟一个字母"),
        ("D 照术语表原文", "临时 / 不稳定文件"),
        ("没说清课题才问", "老师没说清这两样时才问一句"),
    ]
    for 名, 片段 in 要有:
        if 片段 not in 原文:
            问题.append("缺「%s」" % 名)


    xr条 = re.search(r"- 写文件[^\n]*(?:\n(?!- )[^\n]*)*", 原文)
    if not xr条:
        问题.append("找不到讲文件与 XR 的那条规则")
    else:
        for 要素 in ("文件", "XR", "程序"):
            if 要素 not in xr条.group(0):
                问题.append("XR 那条缺要素「%s」" % 要素)
    不许有 = [
        ("不许把示例技能包当拒绝理由", re.compile(r"技能包[^\n]{0,12}(不能|没法)[^\n]{0,6}(做|写)")),
        ("不许声称替课件标过 XR", re.compile(r"(我已|已经)[^\n]{0,10}(在|给)[^\n]{0,8}(HTML|课件)[^\n]{0,8}(标|写)[^\n]{0,6}XR")),
    ]
    for 名, 样式 in 不许有:
        if 样式.search(原文):
            问题.append("出现了「%s」" % 名)
    占位 = set(re.findall(r"\{([^{}]+)\}", 原文))
    多余 = 占位 - {"工具说明", "之前的对话", "老师这次说的"}
    if 多余:
        问题.append("多了没见过的占位符 %s（format 会炸）" % sorted(多余))
    try:
        原文.format(**{p: "x" for p in 占位})
    except Exception as 错:
        问题.append("format 失败：%s" % 错)
    return 问题


def 主():
    原文 = 加载()

    记("① 九条关键规则都在", not 检查(原文), "；".join(检查(原文)))
    记("② 占位符只有那三个且 format 能过",
       set(re.findall(r"\{([^{}]+)\}", 原文)) == {"工具说明", "之前的对话", "老师这次说的"},
       sorted(set(re.findall(r"\{([^{}]+)\}", 原文))))


    删掉尊重 = 原文.replace("尊重老师", "礼貌")
    记("③ 反向验：删掉「尊重老师」必须报红", bool(检查(删掉尊重)), "删了还全绿")
    删掉XR = re.sub(r"- 写文件[^\n]*(?:\n(?!- )[^\n]*)*", "", 原文)
    记("④ 反向验：整条 XR 规则删掉必须报红", bool(检查(删掉XR)), "删了还全绿")
    塞假话 = 原文 + "\n- 我已经在 HTML 里给课件标好 XR 了\n"
    记("⑤ 反向验：声称替课件标过 XR 必须报红", bool(检查(塞假话)), "塞了假话还全绿")
    塞花括号 = 原文 + "\n- 例子：{课题}\n"
    记("⑥ 反向验：多出没见过的占位符必须报红", bool(检查(塞花括号)), "塞了花括号还全绿")

    课件原 = open(课件提示, encoding="utf-8").read()
    记("⑦ 课件提示仍要求只输出 JSON", "只输出 JSON" in 课件原, "那句没了")

    print()
    print("全部 %d 项通过" % 条数 if not 失败 else "通过 %d / 共 %d" % (条数 - len(失败), 条数))
    return 0 if not 失败 else 1


if __name__ == "__main__":
    sys.exit(主())
