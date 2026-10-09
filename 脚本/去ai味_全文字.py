import io
import json
import os
import re
import shutil
import sys
import time

表情正则 = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]")
要处理 = {".md", ".txt", ".html", ".bat", ".json"}


def 只列不动():
    return () if "--含提示词" in sys.argv else ("提示词",)


def 该跳过(名):
    return 名.startswith(("_备份", "_跳过", "_不是原始副本")) or 名 in {
        ".git", "__pycache__", "build", "dist", "node_modules", "_页面截图"}


def 换破折号(文):
    文 = re.sub(r"^([ \t>\-]*[ \t]*)——[ \t]*", r"\1", 文, flags=re.M)
    文 = re.sub(r"[ \t\r]*——[ \t\r]*(\r?\n)", r"：\1", 文)
    文 = re.sub(r"[ \t]*——[ \t]*(?=\r?\n|\Z)", "：", 文)

    def 换(m):
        前, 后 = m.group(1), m.group(2)
        头 = 前.rstrip()
        if 头.endswith(("：", "，", "。", "；", "、")):
            return 前 + 后
        if "：" in 前.split("\n")[-1][-12:] or "，" in 前.split("\n")[-1][-6:]:
            return 前 + "，" + 后
        if len(头.split("。")[-1]) <= 16:
            return 前 + "：" + 后
        return 前 + "。" + 后
    return re.sub(r"(\S[^\n]{0,140}?)[ \t]*——[ \t]*([^\n\s])", 换, 文)


def 收加粗(文):
    保 = []

    def 存(m):
        保.append(m.group(0))
        return "\x00%d\x00" % (len(保) - 1)

    文 = re.sub(r"(?m)^([ \t>]*[-*]?[ \t]*)\*\*[^*\n]{1,30}\*\*(?=[：:])", 存, 文)
    文 = 文.replace("**", "")
    for i, s in enumerate(保):
        文 = 文.replace("\x00%d\x00" % i, s)
    return 文


def 处理一段(文):
    return 收加粗(换破折号(表情正则.sub("", 文)))


def 处理md(原):
    出 = []
    缓 = []

    def 冲():
        if not 缓:
            return
        段 = re.split(r"(```.*?```)", "".join(缓), flags=re.S)
        出.append("".join(s if i % 2 else 处理一段(s) for i, s in enumerate(段)))
        缓.clear()

    在块 = False
    for l in 原.splitlines(True):
        if l.lstrip().startswith("```"):
            在块 = not 在块
            缓.append(l)
            continue
        if not 在块 and l.lstrip().startswith("|"):
            冲()
            出.append(收加粗(表情正则.sub("", l)))
            continue
        缓.append(l)
    冲()
    return "".join(出)


def 扫js(段):
    出 = []
    i, n = 0, len(段)
    while i < n:
        字 = 段[i]
        if 段.startswith("//", i):
            j = 段.find("\n", i)
            j = n if j < 0 else j
            出.append(处理一段(段[i:j])); i = j
        elif 段.startswith("/*", i):
            j = 段.find("*/", i + 2)
            j = n if j < 0 else j + 2
            出.append(处理一段(段[i:j])); i = j
        elif 字 in "'\"":
            引, j = 字, i + 1
            while j < n:
                if 段[j] == "\\":
                    j += 2; continue
                if 段[j] == 引:
                    j += 1; break
                j += 1
            出.append(处理一段(段[i:j])); i = j
        else:
            j = i
            while (j < n and 段[j] not in "'\""
                   and not 段.startswith("//", j) and not 段.startswith("/*", j)):
                j += 1
            出.append(段[i:j]); i = j
    return "".join(出)


def 处理代码段(段, 注释开头):
    if 段.lstrip().lower().startswith("<style"):
        出 = []
        for l in 段.splitlines(True):
            出.append(处理一段(l) if l.lstrip().startswith(注释开头) else l)
        return "".join(出)
    return 扫js(段)


def 处理html(原):
    段 = re.split(r"(<(?:script|style)\b.*?</(?:script|style)>)", 原, flags=re.S | re.I)
    出 = []
    for i, s in enumerate(段):
        if i % 2:
            注释开头 = ("/*",) if s.lstrip().lower().startswith("<style") else ("//", "/*", "*")
            出.append(处理代码段(s, 注释开头))
        else:
            出.append(处理一段(s))
    return "".join(出)


def 处理bat(原):
    出 = []
    for l in 原.splitlines(True):
        s = l.strip().lower()
        if s.startswith("rem") or s.startswith("echo"):
            出.append(处理一段(l))
        else:
            出.append(l)
    return "".join(出)


def 处理json(原):
    段 = re.split(r'("(?:[^"\\]|\\.)*")', 原)
    return "".join(s if i % 2 else 处理一段(s) for i, s in enumerate(段))


处理表 = {".md": 处理md, ".txt": 处理md, ".html": 处理html, ".bat": 处理bat, ".json": 处理json}


def 校验(原, 新, 后):
    if 原.count("\n") != 新.count("\n"):
        return "行数变了（%d → %d）" % (原.count("\n"), 新.count("\n"))
    if 后 in (".md", ".txt", ".html", ".json"):
        if 原.count("```") != 新.count("```"):
            return "代码围栏数变了"
    if 后 == ".json":
        try:
            json.loads(新)
        except ValueError as e:
            return "JSON 解析不过：" + str(e)[:50]
    if 原.count("\r\n") * 2 > 原.count("\n"):
        独 = 新.count("\n") - 新.count("\r\n")
        if 独 > 0:
            return "混进了 %d 行独行 LF（原文件是 CRLF）" % 独
    return ""


def 主程序():
    干 = "--写" in sys.argv
    根们 = [r"C:/Users/25768/Desktop/样本", r"C:/Users/25768/Desktop/科赛"]
    备份根 = None
    if 干:
        备份根 = r"C:/Users/25768/Desktop/科赛/_备份_去ai味_%s" % time.strftime("%Y%m%d-%H%M%S")
        os.makedirs(备份根, exist_ok=True)

    动的 = []
    跳提示词 = []
    总计 = {"文件": 0, "破折号": 0, "加粗": 0, "表情": 0}
    坏 = []

    for 根 in 根们:
        for 父, 目录们, 文件们 in os.walk(根):
            目录们[:] = [d for d in 目录们 if not 该跳过(d)]
            for 名 in sorted(文件们):
                后 = os.path.splitext(名)[1].lower()
                if 后 not in 要处理:
                    continue
                全 = os.path.join(父, 名)
                相对 = os.path.relpath(全, 根)
                if any(x in 相对 for x in 只列不动()):
                    跳提示词.append(相对)
                    continue
                try:
                    原 = io.open(全, encoding="utf-8", newline="").read()
                except (OSError, UnicodeDecodeError):
                    continue
                新 = 处理表[后](原)
                if 新 == 原:
                    continue
                问题 = 校验(原, 新, 后)
                if 问题:
                    坏.append("%s：%s" % (相对, 问题))
                    continue
                动的.append((相对, 原.count("——") - 新.count("——")
                           + 原.count("**") - 新.count("**")
                           + len(表情正则.findall(原)) - len(表情正则.findall(新))))
                总计["文件"] += 1
                总计["破折号"] += 原.count("——") - 新.count("——")
                总计["加粗"] += 原.count("**") - 新.count("**")
                总计["表情"] += len(表情正则.findall(原)) - len(表情正则.findall(新))
                if 干:
                    到 = os.path.join(备份根, os.path.basename(根), 相对)
                    os.makedirs(os.path.dirname(到), exist_ok=True)
                    shutil.copy2(全, 到)
                    io.open(全, "w", encoding="utf-8", newline="").write(新)

    动的.sort(key=lambda x: -x[1])
    print("动了 %d 个文件：破折号 -%d，加粗 -%d，表情 -%d"
          % (总计["文件"], 总计["破折号"], 总计["加粗"], 总计["表情"]))
    print("逐文件校验（行数守恒 / 围栏成对 / JSON 可解析）：%s"
          % ("全过" if not 坏 else "**%d 个没过，已跳过不动**" % len(坏)))
    for x in 坏:
        print("   " + x)
    print()
    print("改动量最大的 12 个：")
    for 路, n in 动的[:12]:
        print("   %6d  %s" % (n, 路[:70]))
    if 跳提示词:
        print()
        print("**没动**提示词（模型读的，改措辞会影响它的行为，留给人定）：%d 个" % len(跳提示词))
    if 干:
        print()
        print("改前的副本在：" + 备份根)
    else:
        print()
        print("（试跑，没写盘；加 --写 才落盘）")
    return 0


if __name__ == "__main__":
    sys.exit(主程序())
