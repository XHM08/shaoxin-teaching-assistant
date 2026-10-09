
import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 配置
from 地基 import 材料

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

结果 = []
跳过 = []


def 记(名字, 通过, 说明):
    结果.append((名字, bool(通过), 说明))


def 跳过一项(名字, 原因):
    跳过.append((名字, 原因))


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
            return False, "拒是拒了，但话不对：" + str(异常)[:50]
        return True, "拒了：" + str(异常)[:50]
    return False, "居然放行了，拿到：" + str(值)[:50]



def 写docx(路径, 段落表):
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    段 = "".join("<w:p><w:r><w:t>" + 文 + "</w:t></w:r></w:p>" for 文 in 段落表)
    with zipfile.ZipFile(路径, "w") as 包:
        包.writestr("[Content_Types].xml", "<Types/>")
        包.writestr("word/document.xml",
                  "<w:document xmlns:w=\"" + W + "\"><w:body>" + 段 + "</w:body></w:document>")


def 写pptx(路径, 页表):
    A = "http://schemas.openxmlformats.org/drawingml/2006/main"
    with zipfile.ZipFile(路径, "w") as 包:
        包.writestr("[Content_Types].xml", "<Types/>")
        for 序号, 文 in enumerate(页表, 1):
            包.writestr("ppt/slides/slide%d.xml" % 序号,
                      "<root xmlns:a=\"" + A + "\"><a:p><a:r><a:t>" + 文 + "</a:t></a:r></a:p></root>")


def 写xlsxinline(路径, 格表):
    表 = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    行 = ""
    for 一行 in 格表:
        格 = "".join("<c t=\"inlineStr\"><is><t>" + str(文) + "</t></is></c>" for 文 in 一行)
        行 += "<row>" + 格 + "</row>"
    with zipfile.ZipFile(路径, "w") as 包:
        包.writestr("[Content_Types].xml", "<Types/>")
        包.writestr("xl/workbook.xml",
                  "<workbook xmlns=\"" + 表 + "\"><sheets><sheet name=\"花名册\"/></sheets></workbook>")
        包.writestr("xl/worksheets/sheet1.xml",
                  "<worksheet xmlns=\"" + 表 + "\"><sheetData>" + 行 + "</sheetData></worksheet>")


def 写xlsx共享(路径):
    表 = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    with zipfile.ZipFile(路径, "w") as 包:
        包.writestr("[Content_Types].xml", "<Types/>")
        包.writestr("xl/workbook.xml",
                  "<workbook xmlns=\"" + 表 + "\"><sheets><sheet name=\"成绩\"/></sheets></workbook>")
        包.writestr("xl/sharedStrings.xml",
                  "<sst xmlns=\"" + 表 + "\"><si><t>张三</t></si>"
                  "<si><r><t>李</t></r><r><t>四</t></r></si></sst>")
        包.writestr("xl/worksheets/sheet1.xml",
                  "<worksheet xmlns=\"" + 表 + "\"><sheetData><row><c t=\"s\"><v>0</v></c>"
                  "<c t=\"s\"><v>1</v></c><c><v>95</v></c></row></sheetData></worksheet>")


def _一格(表, 文):
    return ("<worksheet xmlns=\"" + 表 + "\"><sheetData><row>"
            "<c t=\"inlineStr\"><is><t>" + 文 + "</t></is></c>"
            "</row></sheetData></worksheet>")


def 写xlsx错序(路径):
    表 = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    关系 = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    包件 = "http://schemas.openxmlformats.org/package/2006/relationships"
    with zipfile.ZipFile(路径, "w") as 包:
        包.writestr("[Content_Types].xml", "<Types/>")
        包.writestr("xl/workbook.xml",
                  "<workbook xmlns=\"" + 表 + "\" xmlns:r=\"" + 关系 + "\"><sheets>"
                  "<sheet name=\"成绩表\" r:id=\"rId2\"/>"
                  "<sheet name=\"花名册\" r:id=\"rId1\"/></sheets></workbook>")
        包.writestr("xl/_rels/workbook.xml.rels",
                  "<Relationships xmlns=\"" + 包件 + "\">"
                  "<Relationship Id=\"rId1\" Target=\"worksheets/sheet1.xml\"/>"
                  "<Relationship Id=\"rId2\" Target=\"worksheets/sheet2.xml\"/>"
                  "</Relationships>")
        包.writestr("xl/worksheets/sheet1.xml", _一格(表, "甲"))
        包.writestr("xl/worksheets/sheet2.xml", _一格(表, "乙"))


def 写xlsx空列(路径):
    表 = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    with zipfile.ZipFile(路径, "w") as 包:
        包.writestr("[Content_Types].xml", "<Types/>")
        包.writestr("xl/worksheets/sheet1.xml",
                  "<worksheet xmlns=\"" + 表 + "\"><sheetData><row>"
                  "<c r=\"A1\" t=\"inlineStr\"><is><t>甲</t></is></c>"
                  "<c r=\"C1\" t=\"inlineStr\"><is><t>一班</t></is></c>"
                  "</row></sheetData></worksheet>")


一号PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080200000090"
    "7753de0000000c4944415408d763f8cfc0000003010100b5e2f2b6000000"
    "0049454e44ae426082")


def 路径(name):
    return 材料.材料路径(name)


def 读(name):
    return 材料.读材料(路径(name))


def 取提示块(页面文本, 起点):
    头 = 页面文本.find(起点)
    if 头 < 0:
        return None
    尾 = 页面文本.find("</div>", 头)
    return 页面文本[头:(尾 if 尾 > 0 else 头 + 400)]


临时 = tempfile.mkdtemp(prefix="邵新材料自检_")
参考临时 = tempfile.mkdtemp(prefix="邵新参考自检_")
原取目录 = 配置.取目录


def 假取目录(目录名, 配置表=None):
    if 目录名 == "材料":
        return 临时
    if 目录名 == "参考资料":
        return 参考临时
    return 原取目录(目录名, 配置表)


try:
    配置.取目录 = 假取目录

    该能读 = [".docx", ".pptx", ".xlsx", ".pdf", ".txt", ".md", ".csv", ".json", ".html", ".htm"]
    错 = [e for e in 该能读 if not 材料.能读("x" + e)[0]]
    记("格式表：常见的这十来种都算能读", not 错, "不能读的：" + str(错) if 错 else "十种全部判为能读")

    越权 = ["../x.txt", "a/../../b.txt", "/etc/passwd", "C:/Windows/win.ini", "C:x.txt",
           "..", "a//b.txt", "a/./b.txt", ""]
    没拦住 = [名 for 名 in 越权 if not 拒了吗(lambda 名=名: 材料.校验材料名(名))[0]]
    记("越权/畸形的材料名一律拦下", not 没拦住,
      "放行的：" + str(没拦住) if 没拦住 else str(len(越权)) + " 种全被拒")
    记("一级子目录的相对名是合法的（口径统一成子目录也算之后）",
     材料.校验材料名("a/b.txt") == "a/b.txt", repr(材料.校验材料名("a/b.txt")))

    with open(os.path.join(临时, "GBK的.txt"), "wb") as 文件:
        文件.write("中文编码测试".encode("gbk"))
    读出来的 = 读("GBK的.txt")
    记("GBK 的 .txt 能读（旧写法在这里会崩）", 读出来的 == "中文编码测试", "读到：" + repr(读出来的))

    with open(os.path.join(临时, "带BOM.md"), "wb") as 文件:
        文件.write(b"\xef\xbb\xbf" + "带BOM的正文".encode("utf-8"))
    读出来的 = 读("带BOM.md")
    记("带 BOM 的 .md 能读", 读出来的 == "带BOM的正文", "读到：" + repr(读出来的))

    with open(os.path.join(临时, "没后缀的稿子"), "wb") as 文件:
        文件.write("这是一份没有后缀的纯文本".encode("utf-8"))
    读出来的 = 读("没后缀的稿子")
    记("没有后缀的文件按文本读（不因缺后缀就拒）",
      读出来的 == "这是一份没有后缀的纯文本", "读到：" + repr(读出来的))

    写docx(os.path.join(临时, "教案.docx"), ["第一段正文", "Second para"])
    读出来的 = 读("教案.docx")
    记(".docx 抽出段落文字", "第一段正文" in 读出来的 and "Second para" in 读出来的,
      "读到：" + repr(读出来的[:60]))

    写pptx(os.path.join(临时, "课件.pptx"), ["第一页的话", "第二页的话"])
    读出来的 = 读("课件.pptx")
    记(".pptx 按页抽文字且页序对",
      读出来的.find("第一页的话") >= 0 and 读出来的.find("第一页的话") < 读出来的.find("第二页的话"),
      "读到：" + repr(读出来的[:80]))

    写xlsxinline(os.path.join(临时, "花名册.xlsx"), [["张三", "李四"], ["王五", 95]])
    读出来的 = 读("花名册.xlsx")
    记(".xlsx（inlineStr 那种，openpyxl 存的就是这种）",
      "张三" in 读出来的 and "李四" in 读出来的 and "王五" in 读出来的 and "95" in 读出来的,
      "读到：" + repr(读出来的[:80]))

    写xlsx共享(os.path.join(临时, "成绩.xlsx"))
    读出来的 = 读("成绩.xlsx")
    记(".xlsx（sharedStrings 那种，且一格里的富文本拼得起来）",
      "张三" in 读出来的 and "李四" in 读出来的 and "95" in 读出来的,
      "读到：" + repr(读出来的[:80]))

    with open(os.path.join(临时, "网页.html"), "w", encoding="utf-8") as 文件:
        文件.write("<html><head><style>p{color:red}</style></head><body>"
                  "<script>var 不该出现=1;</script><p>正文一</p><p>正文 &amp; 二</p></body></html>")
    读出来的 = 读("网页.html")
    记("网页：留下正文、去掉脚本与样式、还原实体",
      "正文一" in 读出来的 and "正文 & 二" in 读出来的 and "不该出现" not in 读出来的
      and "color:red" not in 读出来的,
      "读到：" + repr(读出来的[:80]))

    with open(os.path.join(临时, "成绩.csv"), "w", encoding="utf-8") as 文件:
        文件.write("姓名,分数\n张三,95\n")
    读出来的 = 读("成绩.csv")
    记("csv 能读", "张三" in 读出来的 and "95" in 读出来的, "读到：" + repr(读出来的[:40]))

    造PDF的库 = None
    for 名字 in ("pymupdf", "fitz"):
        try:
            造PDF的库 = __import__(名字)
            break
        except ImportError:
            continue

    if 造PDF的库 is None:
        跳过一项("PDF：有文字层那种能抽出正文", "本机没有 pypdf / PyMuPDF，PDF 那一类读不了")
        跳过一项("PDF：没有文字层那种走扫描件分支", "同上")
    else:
        有字 = os.path.join(临时, "有字.pdf")
        with 造PDF的库.open() as 文档:
            页 = 文档.new_page()
            页.insert_text((72, 72), "This PDF has a real text layer, long enough to pass the threshold.")
            文档.save(有字)
        读出来的 = 读("有字.pdf")
        记("PDF：有文字层那种走的是文字层（不是被当成扫描件去 OCR）",
          "text layer" in 读出来的 and "可能有错字" not in 读出来的,
          "读到：" + repr(读出来的[:60]))

        空格 = os.path.join(临时, "没有字.pdf")
        with 造PDF的库.open() as 文档:
            文档.new_page()
            文档.save(空格)
        好, 值 = 试(lambda: 读("没有字.pdf"))
        if 材料.OCR可用():
            记("PDF：没有文字层那种 → 交给本机 OCR，给的是能看懂的话",
              (not 好) and isinstance(值, ValueError) and "没认出文字" in str(值),
              "拿到：" + type(值).__name__ + "：" + str(值)[:60])
        else:
            记("PDF：没有文字层 + 本机没有 OCR → 报清楚而不是崩栈",
              (not 好) and isinstance(值, ValueError) and "没有文字层" in str(值),
              "拿到：" + type(值).__name__ + "：" + str(值)[:60])

    with open(os.path.join(临时, "一张图.png"), "wb") as 文件:
        文件.write(一号PNG)

    if 材料.OCR可用():
        造得出图 = True
        英文图 = os.path.join(临时, "英文图.png")
        中文图 = os.path.join(临时, "中文图.png")
        try:
            from PIL import Image, ImageDraw, ImageFont
            try:
                小字库 = ImageFont.load_default(size=64)
            except TypeError:
                小字库 = ImageFont.load_default()
            图 = Image.new("RGB", (760, 140), "white")
            ImageDraw.Draw(图).text((20, 30), "HELLO WORLD AGAIN", fill="black", font=小字库)
            图.save(英文图)
        except Exception:
            造得出图 = False

        中文字库 = None
        for 字体 in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
                   "C:/Windows/Fonts/simsun.ttc"):
            if os.path.isfile(字体):
                中文字库 = 字体
                break
        if 造得出图 and 中文字库:
            try:
                from PIL import Image, ImageDraw, ImageFont
                图 = Image.new("RGB", (760, 140), "white")
                ImageDraw.Draw(图).text((20, 30), "合理利用网络", fill="black",
                                    font=ImageFont.truetype(中文字库, 56))
                图.save(中文图)
            except Exception:
                中文字库 = None

        if 造得出图:
            好, 值 = 试(lambda: 读("英文图.png"))
            记("图片：本机 OCR 认得出图上的字", 好 and "HELLO" in str(值).upper(),
              "拿到：" + (repr(str(值)[:50]) if 好 else type(值).__name__ + "：" + str(值)[:60]))
            记("图片：英文单词间的空格保住了（否则会粘成 HELLOWORLD）",
              好 and "HELLO WORLD" in str(值).upper(),
              "拿到：" + (repr(str(值)[:50]) if 好 else "读都没读成"))
            记("OCR 转出来的文字带「可能有错字」的标注", 好 and "可能有错字" in str(值),
              "开头：" + (repr(str(值)[:24]) if 好 else "读都没读成"))
        else:
            跳过一项("图片：本机 OCR 认得出图上的字", "本机没有 Pillow，造不出一张测试图")
        if 中文字库:
            好, 值 = 试(lambda: 读("中文图.png"))
            记("图片：汉字之间没有被塞进空格", 好 and "合理利用网络" in str(值),
              "拿到：" + (repr(str(值)[:50]) if 好 else type(值).__name__ + "：" + str(值)[:60]))
        else:
            跳过一项("图片：汉字之间没有被塞进空格", "找不到中文字库，造不出中文测试图")
    else:
        好, 值 = 试(lambda: 读("一张图.png"))
        记("图片：没有 OCR 时给的是能照着做的提示（拿真存在的图去试）",
          (not 好) and isinstance(值, ValueError) and "转成文字" in str(值),
          "拿到：" + type(值).__name__ + "：" + str(值)[:60])
        跳过一项("图片：本机 OCR 认得出图上的字", "这台机器没有可用的本机 OCR")

    可读, 说明 = 材料.能读("老教案.doc")
    记("旧版 .doc：判为不能读，且让人「另存为」", (not 可读) and "另存为" in 说明,
      "提示：" + 说明[:50])

    with open(os.path.join(临时, "太大.txt"), "wb") as 文件:
        文件.truncate(材料.单文件上限 + 1024)
    好, 值 = 试(lambda: 读("太大.txt"))
    记("超过单文件上限就拒，且提示里带上实际大小",
      (not 好) and isinstance(值, ValueError) and "MB" in str(值),
      "拿到：" + type(值).__name__ + "：" + str(值)[:60])

    with open(os.path.join(临时, "假的.docx"), "wb") as 文件:
        文件.write(b"this is plain text pretending to be a docx")
    好, 值 = 试(lambda: 读("假的.docx"))
    记("伪 .docx 不崩栈，给的是可读的错", (not 好) and isinstance(值, ValueError),
      "拿到：" + str(值)[:60])

    with zipfile.ZipFile(os.path.join(临时, "很多条.docx"), "w") as 包:
        包.writestr("word/document.xml", "<w:document/>")
        for 序号 in range(材料.包条目上限 + 1):
            包.writestr("e%04d.txt" % 序号, "x")
    好, 值 = 试(lambda: 读("很多条.docx"))
    记("包里的条目数超上限就拒", (not 好) and isinstance(值, ValueError) and "超过上限" in str(值),
      "拿到：" + str(值)[:60])

    with open(os.path.join(临时, "很长.txt"), "w", encoding="utf-8") as 文件:
        文件.write("啊" * (材料.抽取字上限 + 500))
    读出来的 = 读("很长.txt")
    记("超长正文被截断，且末尾留了标记（不静默）",
      材料.抽取字上限 <= len(读出来的) <= 材料.抽取字上限 + 80 and "已截断" in 读出来的,
      "长度 " + str(len(读出来的)) + "（上限 " + str(材料.抽取字上限) + "），末尾："
      + repr(读出来的[-24:]))

    with open(os.path.join(临时, "说明.md"), "w", encoding="utf-8") as 文件:
        文件.write("说明不该算材料")
    清单 = 材料.材料清单()
    名字集 = [条["文件名"] for 条 in 清单]
    字段齐 = all(("格式" in 条 and "能不能读" in 条 and "说明" in 条) for 条 in 清单)
    记("材料清单：排除 说明.md、带格式与能不能读",
      "说明.md" not in 名字集 and 字段齐 and ("教案.docx" in 名字集),
      "共 " + str(len(清单)) + " 条，字段齐=" + str(字段齐) + "，含 教案.docx=" + str("教案.docx" in 名字集))

    with open(os.path.join(临时, "UTF16的.txt"), "wb") as 文件:
        文件.write("记事本存出来的Unicode文本".encode("utf-16"))
    读出来的 = 读("UTF16的.txt")
    记("记事本「Unicode」存的 .txt 能读（不认它就是满屏乱码）",
      "记事本存出来的Unicode文本" in 读出来的, "读到：" + repr(读出来的[:30]))

    with open(os.path.join(临时, "假的.txt"), "wb") as 文件:
        文件.write(bytes(range(256)) * 40)
    好, 值 = 试(lambda: 读("假的.txt"))
    记("二进制文件改名成 .txt → 拒（以前会把半屏乱码当“读成功”送进蒸馏）",
      (not 好) and isinstance(值, ValueError) and "乱码" in str(值),
      "拿到：" + type(值).__name__ + "：" + str(值)[:40])

    with open(os.path.join(临时, "加密的.docx"), "wb") as 文件:
        文件.write(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64)
    好, 值 = 试(lambda: 读("加密的.docx"))
    记("加了密码的 Office（OLE 外壳）→ 说出「加了密码」，不能只说「坏了」",
      (not 好) and isinstance(值, ValueError) and "密码" in str(值),
      "拿到：" + str(值)[:50])

    with zipfile.ZipFile(os.path.join(临时, "只有图的.docx"), "w") as 包:
        包.writestr("[Content_Types].xml", "<Types/>")
        包.writestr("word/document.xml",
                  "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
                  "<w:body/></w:document>")
        包.writestr("word/media/image1.png", b"\x89PNG\r\n\x1a\n")
    好, 值 = 试(lambda: 读("只有图的.docx"))
    记("整页是图的 .docx → 明确报错（以前静默给空材料，模型只能自己编）",
      (not 好) and isinstance(值, ValueError) and "只有图片" in str(值),
      "拿到：" + str(值)[:50])

    好, 值 = 试(lambda: 读("这里没有这份材料.docx"))
    记("材料不存在 → 可读的「找不到」，且不回传完整本地路径",
      (not 好) and isinstance(值, ValueError) and "找不到" in str(值) and ":\\" not in str(值),
      "拿到：" + str(值)[:60])

    写xlsx错序(os.path.join(临时, "错序.xlsx"))
    读出来的 = 读("错序.xlsx").replace("\r", "")
    记("xlsx 表名按 rels 对得上（拖过页签后不能靠位置猜）",
      "【花名册】\n甲" in 读出来的 and "【成绩表】\n乙" in 读出来的,
      "读到：" + repr(读出来的[:60]))

    写xlsx空列(os.path.join(临时, "空列.xlsx"))
    读出来的 = 读("空列.xlsx").replace("\r", "")
    记("xlsx 空单元格也占位（后面的列不串到前面）",
      "甲\t\t一班" in 读出来的, "读到：" + repr(读出来的[:60]))

    os.makedirs(os.path.join(参考临时, "政策文件"), exist_ok=True)
    with open(os.path.join(临时, "老师自己的教案.txt"), "w", encoding="utf-8") as 文件:
        文件.write("这位老师的讲法")
    with open(os.path.join(参考临时, "别人公开的教案.txt"), "w", encoding="utf-8") as 文件:
        文件.write("公开参考")
    with open(os.path.join(参考临时, "政策文件", "省文件.docx"), "wb") as 文件:
        文件.write(b"x")
    with open(os.path.join(参考临时, "说明.md"), "w", encoding="utf-8") as 文件:
        文件.write("说明不算参考资料")

    参考条 = 材料.参考资料清单()
    参考名 = [条["文件名"] for 条 in 参考条]
    记("参考资料：递归列出子目录里的文件，且排除 说明.md",
      "政策文件/省文件.docx" in 参考名 and "别人公开的教案.txt" in 参考名
      and "说明.md" not in 参考名,
      "列出 " + str(len(参考条)) + " 条：" + str(参考名))

    材料名 = [条["文件名"] for 条 in 材料.材料清单()]
    记("两边不混：教师材料里看不到参考资料，反过来也一样",
      "别人公开的教案.txt" not in 材料名 and "政策文件/省文件.docx" not in 材料名
      and "老师自己的教案.txt" not in 参考名,
      "材料侧 " + str(len(材料名)) + " 条，参考侧 " + str(len(参考名)) + " 条")

    子 = os.path.join(临时, "水循环")
    os.makedirs(子, exist_ok=True)
    with open(os.path.join(子, "子目录教案.txt"), "w", encoding="utf-8") as 文件:
        文件.write("子目录里的材料：蒸发、凝结、降水。")
    with open(os.path.join(子, "说明.md"), "w", encoding="utf-8") as 文件:
        文件.write("子目录里的说明也不该算材料")
    with open(os.path.join(子, "示意图.png"), "wb") as 文件:
        文件.write(一号PNG)

    子清单 = 材料.材料清单()
    子名 = [条["文件名"] for 条 in 子清单]
    记("教师材料：子目录里的也列出来（名字是相对路径，用 / 分隔）",
      "水循环/子目录教案.txt" in 子名 and "水循环/示意图.png" in 子名,
      "共 " + str(len(子名)) + " 条，子目录里这几条：" + str([x for x in 子名 if x.startswith("水循环/")]))
    记("子目录里的 说明.md 同样不算材料",
      not any(x.endswith("说明.md") for x in 子名), str([x for x in 子名 if "说明" in x]))
    记("子目录里的材料真读得出来（下拉里选得到 ≠ 真读得到）",
      "蒸发" in 读("水循环/子目录教案.txt"), 读("水循环/子目录教案.txt")[:20])

    from 能力 import _课件
    可配图们, _图说明 = _课件.可配图()
    记("口径一致：可配图() 列出来的图，材料清单() 里都得有（这次修的根因，钉住别漂回去）",
      any(g.startswith("水循环/") for g in 可配图们) and all(g in 子名 for g in 可配图们),
      "可配图 " + str(可配图们))

    越界 = []
    for 坏名 in ("../密钥/x.txt", "/绝对路径.txt", "水循环/../../x.txt", "C:/Windows/x.txt",
              "水循环//x.txt", "..", "水循环/./x.txt"):
        try:
            材料.校验材料名(坏名)
            越界.append(坏名)
        except ValueError:
            pass
    记("越权/畸形的材料名全拦住（放开子目录之后这条更要紧）", not 越界, "漏了：" + str(越界))
    记("正常的相对名照收：'水循环/教案.docx' 与反斜杠写法都规范成 /",
     材料.校验材料名("水循环/教案.docx") == "水循环/教案.docx"
     and 材料.校验材料名("水循环\\教案.docx") == "水循环/教案.docx",
     repr(材料.校验材料名("水循环\\教案.docx")))

    def 指到不存在的目录(目录名, 配置表=None):
        if 目录名 == "参考资料":
            return os.path.join(临时, "根本没有这个目录")
        return 原取目录(目录名, 配置表)

    配置.取目录 = 指到不存在的目录
    try:
        空的 = 材料.参考资料清单()
        记("参考资料目录不存在时返回空表，不崩", 空的 == [], "拿到：" + repr(空的))
    finally:
        配置.取目录 = 假取目录

    try:
        缓冲 = io.StringIO()
        with contextlib.redirect_stdout(缓冲):
            import 本地服务
        选项 = 本地服务.取选项("材料")
        记("下拉框能列出新格式的材料", "教案.docx" in 选项 and "课件.pptx" in 选项,
          "共 " + str(len(选项)) + " 项，含新格式=" + str("教案.docx" in 选项))
        进了 = [名 for 名 in ("别人公开的教案.txt", "政策文件/省文件.docx") if 名 in 选项]
        记("公开参考资料不进蒸馏下拉", not 进了,
          "下拉 " + str(len(选项)) + " 项" + ("，混进去的：" + str(进了) if 进了 else "，一个都没混进去"))
    except Exception as 异常:
        跳过一项("下拉框能列出新格式的材料", "没法安全导入本地服务：" + type(异常).__name__)
        跳过一项("公开参考资料不进蒸馏下拉", "同上")

    脚本字节 = open(os.path.join(根, "地基", "本机OCR.ps1"), "rb").read()
    非ASCII = [b for b in 脚本字节 if b > 127]
    记("OCR 脚本是纯 ASCII（那条硬规则有测试守着，不靠注释自律）",
      not 非ASCII,
      ("非 ASCII 字节 " + str(len(非ASCII)) + " 个") if 非ASCII
      else ("全部 " + str(len(脚本字节)) + " 字节都在 0-127"))

    def 在仓库里():
        try:
            看 = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                             cwd=根, capture_output=True, text=True)
            return 看.stdout.strip() == "true"
        except Exception:
            return False

    if not 在仓库里():
        跳过一项("参考资料默认不进版本库（有版权的教材不能推上公开仓库）", "当前目录不是 git 仓库")
    else:
        def 被忽略吗(相对路径):
            return subprocess.run(["git", "check-ignore", "-q", 相对路径],
                                  cwd=根).returncode == 0

        教材被挡 = 被忽略吗("参考资料/某教材.pdf")
        说明能进 = not 被忽略吗("参考资料/说明.md")
        记("参考资料默认不进版本库，但 说明.md 能进",
          教材被挡 and 说明能进,
          "某教材.pdf 被忽略=" + str(教材被挡) + "，说明.md 可提交=" + str(说明能进))

    页面 = open(os.path.join(根, "网页", "首页.html"), encoding="utf-8").read()
    蒸馏块 = 取提示块(页面, "材料放在 <code>材料/</code>")
    知识库块 = 取提示块(页面, "id=\"matNotice\"")
    后缀字面量 = re.compile(r"\.(docx|pptx|xlsx|pdf|txt|md|csv)\b")
    记("蒸馏页的材料提示里不再列具体后缀",
      蒸馏块 is not None and not 后缀字面量.search(蒸馏块),
      "那一块：" + repr((蒸馏块 or "")[:60]))
    记("知识库页的格式说明由接口填，不写死在页面里",
      知识库块 is not None and "d.提示" in 页面 and "$('matNotice')" in 页面
      and not 后缀字面量.search(知识库块),
      "那一块：" + repr((知识库块 or "")[:60]))

    说明 = open(os.path.join(根, "材料", "说明.md"), encoding="utf-8").read()
    记("材料/说明.md 的旧规矩已改掉，且写清了图片这条",
      "只放 `.txt` / `.md`" not in 说明 and "图片" in 说明 and "OCR" in 说明,
      "还写着「只放 .txt / .md」=" + str("只放 `.txt` / `.md`" in 说明))

finally:
    配置.取目录 = 原取目录
    shutil.rmtree(临时, ignore_errors=True)
    shutil.rmtree(参考临时, ignore_errors=True)

for 序号, (名字, 通过, 说明) in enumerate(结果, 1):
    print("  %2d. %s %s：%s" % (序号, "通过" if 通过 else "不过", 名字, 说明))
for 名字, 原因 in 跳过:
    print("     跳过 %s：%s" % (名字, 原因))

通过数 = sum(1 for _名, 通, _说 in 结果 if 通)
尾巴 = ("，" + str(len(跳过)) + " 项跳过") if 跳过 else ""
print("\n%d/%d%s" % (通过数, len(结果), 尾巴))
if 通过数 < len(结果):
    sys.exit(1)
sys.exit(3 if 跳过 else 0)
