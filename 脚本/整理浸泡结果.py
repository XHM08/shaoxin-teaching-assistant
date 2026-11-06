import io
import os
import re
import sys

出目录 = r"C:/tmp/浸泡4"
期望轮数 = 20

记号不绿 = {"✗": "失败", "…": "超时", "?": "无计数", "·": "跳过"}


def 解析一轮(文本):
    m = re.search(r"共\s*(\d+)\s*条自检，用了\s*(\d+)\s*秒", 文本)
    if not m:
        return None
    后 = 文本[m.end():]
    汇总 = ""
    for 行 in 后.splitlines():
        if 行.strip():
            汇总 = 行.strip()
            break
    if not re.fullmatch(r"(?:(?:通过|失败|跳过|超时|无计数)\s*\d+\s*)+", 汇总):
        return None
    计 = {"通过": 0, "失败": 0, "跳过": 0, "超时": 0, "无计数": 0}
    for k, v in re.findall(r"(通过|失败|跳过|超时|无计数)\s*(\d+)", 汇总):
        计[k] = int(v)
    不绿 = []
    for 行 in 后.splitlines():
        t = 行.strip()
        if t and t[0] in 记号不绿 and "检查_" in t:
            不绿.append(t.split()[1])
    return {"共": int(m.group(1)), "用了": int(m.group(2)), "不绿": 不绿, **计}


def 读一轮(路):
    文本 = io.open(路, encoding="utf-8", errors="replace").read()
    果 = 解析一轮(文本)
    if 果 is None:
        return None
    if "原来没服务，跑法自己起了一个" in 文本:
        果["服务"] = "自己起"
    elif "已经有一个服务" in 文本:
        果["服务"] = "用现成的"
    else:
        果["服务"] = "**没起成**"
    return 果


def 自测():
    好 = ("（8765 上原来没服务，跑法自己起了一个，跑完会关掉）\n"
        "共 32 条自检，用了 277 秒\n  通过 31  失败 1\n\n"
        "  ✓ 检查_MCP.py                    通过   全部 19 项通过\n"
        "  ✗ 检查_配音路由.py                 失败   14/14\n")
    果 = 解析一轮(好)
    assert 果 is not None, "有汇总行却解析不出"
    assert (果["共"], 果["用了"], 果["通过"], 果["失败"]) == (32, 277, 31, 1), 果
    assert 果["不绿"] == ["检查_配音路由.py"], 果["不绿"]

    空 = "（8765 上原来没服务）\n"
    assert 解析一轮(空) is None, "**空日志被当成了能解析**"

    崩了 = "共 32 条自检，用了 10 秒\n  ✓ 检查_MCP.py   通过   全部 19 项通过\n"
    assert 解析一轮(崩了) is None, "**没有汇总行却被当成了能解析**"

    骗 = ("共 32 条自检，用了 10 秒\n"
         "  检查_某条.py 说：通过 3\n")
    assert 解析一轮(骗) is None, "**拿字符串当计数证据了**"

    print("自测 4 条全过：能解析真汇总、空日志不算通过、缺汇总不算通过、不拿别人的数字当汇总")
    return 0


def 主程序():
    global 出目录
    if "--自测" in sys.argv:
        return 自测()
    参数 = [一 for 一 in sys.argv[1:] if not 一.startswith("--")]
    if 参数:
        出目录 = 参数[0]

    若 = sorted(f for f in os.listdir(出目录) if re.match(r"^第\d+轮\.log$", f))
    if not 若:
        print("还没有任何一轮日志：" + 出目录)
        return 1

    行 = ["| 轮次 | 共 | 通过 | 失败 | 跳过 | 超时 | 无计数 | 用了秒 | 服务 | 不绿的那几条 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    总 = {"通过": 0, "失败": 0, "跳过": 0, "超时": 0, "无计数": 0}
    非绿轮 = []
    解析不出 = []
    没起服务 = []
    for 名 in 若:
        n = 名.replace("第", "").replace("轮.log", "").lstrip("0") or "0"
        果 = 读一轮(os.path.join(出目录, 名))
        if 果 is None:
            解析不出.append(n)
            行.append("| %s | **解析不出** | | | | | | | | 这一轮日志没有可解析的汇总行，**不能算通过** |" % n)
            continue
        for k in 总:
            总[k] += 果[k]
        if 果["服务"] == "**没起成**":
            没起服务.append(n)
        if 果["失败"] or 果["超时"] or 果["无计数"] or 果["跳过"]:
            非绿轮.append(n)
        行.append("| %s | %d | %d | %d | %d | %d | %d | %d | %s | %s |" % (
            n, 果["共"], 果["通过"], 果["失败"], 果["跳过"], 果["超时"], 果["无计数"],
            果["用了"], 果["服务"], "、".join(果["不绿"]) or "无"))

    行.append("")
    行.append("共 %d 个日志文件（应有 %d 轮）" % (len(若), 期望轮数))
    行.append("四态合计：通过 %d，失败 %d，跳过 %d，超时 %d，无计数 %d"
            % (总["通过"], 总["失败"], 总["跳过"], 总["超时"], 总["无计数"]))
    行.append("解析不出的轮次：" + ("、".join(解析不出) if 解析不出 else "无"))
    行.append("非绿的轮次（含跳过）：" + ("、".join(非绿轮) if 非绿轮 else "无"))
    行.append("日志里看不出\"服务是谁起的\"的轮次：" + ("、".join(没起服务) if 没起服务 else "无"))
    if len(若) != 期望轮数:
        行.append("**轮数不是 %d，可能中途断了**" % 期望轮数)

    文 = "\n".join(行)
    print(文)
    写 = os.path.join(出目录, "结果表.md")
    io.open(写, "w", encoding="utf-8", newline="").write(文 + "\n")
    print()
    print("（也写到了 " + 写 + "）")
    if 解析不出 or len(若) != 期望轮数:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(主程序())
