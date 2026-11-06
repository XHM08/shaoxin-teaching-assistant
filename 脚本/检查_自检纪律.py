
import os
import re
import sys

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
脚本目录 = os.path.join(根, "脚本")

裸吞 = re.compile(r"except\s*:\s*$", re.M)
吞了不说 = re.compile(r"except[^\n:]+:\s*$", re.M)
子串当计数 = re.compile(r'"\s*\d+\s*/\s*\d+\s*"\s+in\s')
用户绝对路径 = re.compile(r"[A-Za-z]:[\\/]Users[\\/][^\\/\s\"']+")
收尾写法 = ("项通过", "通过数", "%d/%d", "都对得上", "都画得出来", "正常。", "个能力和", "对了",
         "与现场一致", "处对不上", "%d/%d", "%02d/%02d")
结果 = []


def 记(名, 过, 说=""):
    结果.append((名, bool(过), str(说)))


def main():
    脚本 = sorted(x for x in os.listdir(脚本目录)
                if x.startswith("检查_") and x.endswith(".py") and x != "检查_自检纪律.py")
    记("找到自检脚本", len(脚本) > 0, "%d 条" % len(脚本))

    吞的, 子串的, 写死的, 没退出码的, 没收尾的 = [], [], [], [], []
    for 名 in 脚本:
        源 = open(os.path.join(脚本目录, 名), encoding="utf-8").read()
        行们 = 源.splitlines()
        for i, 行 in enumerate(行们[:-1]):
            if 行们[i + 1].strip() != "pass":
                continue
            if 裸吞.search(行):
                吞的.append("%s:%d 裸 except: pass" % (名, i + 1))
            elif 吞了不说.search(行):
                邻 = (行们[i] or "") + (行们[i + 1] or "") + (行们[i - 1] if i else "")
                if not any(词 in 邻 for 词 in ("为什么", "忽略", "可忽略", "故意", "预期", "不忽略")):
                    吞的.append("%s:%d except…pass 没写为什么" % (名, i + 1))
        for 找 in 子串当计数.finditer(源):
            子串的.append("%s：%s" % (名, 找.group(0).strip()[:40]))
        for 找 in 用户绝对路径.finditer(源):
            写死的.append("%s：%s" % (名, 找.group(0)))
        if "sys.exit(" not in 源:
            没退出码的.append(名)
        if not any(写法 in 源 for 写法 in 收尾写法):
            没收尾的.append(名)

    记("① 没有裸 `except: pass`；有类型的 except…pass 必须就地写为什么", not 吞的, "、".join(吞的[:4]))
    记("② 没有拿字符串当计数证据（`\"N/M\" in …` 会误命中别处）", not 子串的, "；".join(子串的[:4]))
    记("③ 没有写死用户目录绝对路径（发给别人也要跑得起来）", not 写死的, "；".join(写死的[:4]))
    记("④ 每条自检都有自己的退出码（跑全量靠它分四态）", not 没退出码的, "、".join(没退出码的[:6]))
    记("⑤ 每条自检都有能解析的收尾行（否则跑全量分不出跳过与通过）", not 没收尾的,
      "、".join(没收尾的[:6]) or "全部认得出来")

    报错 = [x for x in 结果 if not x[1]]
    print()
    for 名, 过, 说 in 结果:
        print(("  通过  " if 过 else "  失败  ") + 名 + ("　→　" + 说 if 说 else ""))
    print("全部 %d 项通过" % len(结果) if not 报错 else "%d 项失败" % len(报错))
    return 0 if not 报错 else 1


if __name__ == "__main__":
    sys.exit(main())
