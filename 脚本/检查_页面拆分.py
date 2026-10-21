
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

失败 = []
条数 = 0


def 记(名, 通过, 说明=""):
    global 条数
    条数 += 1
    print(("  ✓ " if 通过 else "  ✗ ") + 名 + ("" if 通过 else "　→　" + str(说明)))
    if not 通过:
        失败.append(名)


def 跑检查():
    import _页面文本 as 页文

    标记 = 页文.读标记()
    脚本 = 页文.读脚本()

    记("① 首页.html 用 <script src> 指向 首页.js（接线）", 页文.引用了脚本(标记),
       "找不到指向 /网页/首页.js 的 script 标签")
    记("② 首页.js 存在且不是空的（拆分没拆空）",
       len(脚本.splitlines()) > 1000, "%d 行" % len(脚本.splitlines()))
    记("③ 标记里没有残留的内联脚本（拆完就该是 0 个）",
       页文.内联脚本数(标记) == 0, "还有 %d 个" % 页文.内联脚本数(标记))
    记("④ 引用的 <script> 没写成 type=\"module\"",
       'type="module"' not in 标记 and "type='module'" not in 标记,
       "写成模块会改变脚本语义（顶层 await、严格模式）")

    全文 = 页文.读页面()
    记("⑤ 读页面 = 标记 + 分隔 + 脚本",
       页文.拼接分隔 in 全文 and 标记.strip()[:40] in 全文 and 脚本.strip()[-40:] in 全文,
       "拼接顺序或分隔不对")

    打包 = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "脚本", "打包.py"), encoding="utf-8").read()
    记("⑩ 打包清单里包含 网页/首页.js（少了它，包里会白屏）",
       '"网页", "首页.js"' in 打包, "打包.py 的 必须有 清单里没有它")

    临时 = tempfile.mkdtemp(prefix="页面拆分-")
    try:
        假标记 = os.path.join(临时, "假.html")
        假脚本 = os.path.join(临时, "假.js")
        io.open(假标记, "w", encoding="utf-8").write('<html><script src="/网页/首页.js"></script></html>')
        io.open(假脚本, "w", encoding="utf-8").write("var 甲 = 1;\n")
        记("⑥ 临时文件：读标记与读脚本各取各的",
           页文.读标记(假标记).startswith("<html>") and 页文.读脚本(假脚本).strip() == "var 甲 = 1;")
        os.remove(假脚本)
        try:
            页文.读脚本(假脚本)
            抛了 = False
        except 页文.页面缺文件:
            抛了 = True
        记("⑦ 脚本文件不在时抛 页面缺文件，不静默降级", 抛了, "没抛，会给出假绿")

        记("⑧ 反向验：改文件名、加 defer 两种写法都要判对",
           (not 页文.引用了脚本('<script src="/网页/别的.js"></script>'))
           and 页文.引用了脚本('<script defer src="/网页/首页.js"></script>')
           and 页文.引用了脚本("<script src='/网页/首页.js'></script>"),
           "正则没同时接受 defer 与单引号")
        记("⑨ 反向验：中间夹一段内联脚本时，内联计数要能数出来",
           页文.内联脚本数("<script>var a=1;</script>") == 1)
    finally:
        import shutil
        shutil.rmtree(临时, ignore_errors=True)


def 主():
    try:
        跑检查()
    except Exception as 错:
        记("检查本身跑完了", False, "%s: %s" % (type(错).__name__, 错))
    print()
    print("全部 %d 项通过" % 条数 if not 失败 else "通过 %d / 共 %d" % (条数 - len(失败), 条数))
    return 0 if not 失败 else 1


if __name__ == "__main__":
    sys.exit(主())
