
import base64
import html
import os
import re
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile

from 地基 import 配置

单文件上限 = 64 * 1024 * 1024
抽取字上限 = 200000
包条目上限 = 2000
包单条上限 = 20 * 1024 * 1024
包总量上限 = 80 * 1024 * 1024
OCR最多页 = 50
OCR单次超时 = 180

文本后缀 = (".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".jsonl",
           ".log", ".ini", ".cfg", ".conf", ".yml", ".yaml", ".srt", ".vtt")
标记后缀 = (".html", ".htm", ".xhtml", ".xml")
文档后缀 = (".docx", ".pptx", ".xlsx")
PDF后缀 = (".pdf",)
图片后缀 = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff", ".heic")
旧版后缀 = (".doc", ".ppt", ".xls", ".wps", ".et", ".dps", ".rtf")

能读后缀 = 文本后缀 + 标记后缀 + 文档后缀 + PDF后缀
参考资料条数上限 = 5000
材料条数上限 = 5000

PDF至少几个字才算有文字层 = 50

本目录 = os.path.dirname(os.path.abspath(__file__))
OCR脚本路径 = os.path.join(本目录, "本机OCR.ps1")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
表 = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

_OCR可用 = None
_OCR原因 = ""
_OCR探针时刻 = 0.0
OCR失败缓存秒 = 300

OCR探针图 = (
    "iVBORw0KGgoAAAANSUhEUgAAAHgAAAAwCAIAAABVDSmEAAAAyUlEQVR4nO3awQqEMAwA0Ub8/1+u"
    "oAieWg91LM28qwsrQzYW1qi1Fn1vA75DhuY40RBDQwwN2duXI4K6kxU0jnBO9BwTffGs3dX96TvR"
    "kN9CR7Lt/2p1DBHJynKhu2Xj/kCGZ4A7GmLoFUPXU0np24dh2qzoRFv5yR0NMTTE0BBDQwwNMTTE"
    "0BBDQwwNMTTE0BBDQwwNMTTE0BBDQwwNMTTE0Mu9qZT8v0QnGmJoiKFn2tHJXwQdwomGRM4zAM+J"
    "hhgaYmiIoQvjAMfvHmRpVGv3AAAAAElFTkSuQmCC")


def 清洗文字(原文):
    文字 = 原文.strip()
    while "\n\n\n" in 文字:
        文字 = 文字.replace("\n\n\n", "\n\n")
    return 文字


def _封顶(文字):
    if len(文字) <= 抽取字上限:
        return 文字
    return 文字[:抽取字上限] + "\n\n（已截断：全文 " + str(len(文字)) + " 字，只取了前 " + str(抽取字上限) + " 字）"


def _读原始文字(路径):
    with open(路径, "rb") as 文件:
        数据 = 文件.read()
    if 数据[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return 数据.decode("utf-16", errors="replace")
    for 编码 in ("utf-8-sig", "gb18030"):
        try:
            return 数据.decode(编码)
        except UnicodeDecodeError:
            continue
    文字 = 数据.decode("utf-8", errors="replace")
    if 文字.count("\ufffd") * 20 > len(文字):
        raise ValueError("这份文件看着不是文本（解出来一半是乱码）。"
                         "它可能是图片、压缩包或别的程序的数据，请换成文本或图片再来。")
    return 文字


def _去标签(原文):
    原文 = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1>", " ", 原文)
    原文 = re.sub(r"(?i)<br\s*/?>", "\n", 原文)
    原文 = re.sub(r"(?i)</(p|div|li|tr|h[1-6]|td|th|section)>", "\n", 原文)
    原文 = re.sub(r"(?s)<[^>]*>", "", 原文)
    return html.unescape(原文)


def _像加密件吗(路径):
    try:
        with open(路径, "rb") as 文件:
            头 = 文件.read(8)
    except OSError:
        return "这个文件打不开。"
    if 头[:4] == b"\xd0\xcf\x11\xe0":
        return ("这份文件加了密码（或是 Office 2003 的老格式），程序读不了。"
                "请先用 WPS / Word 去掉密码，或「另存为」.docx / .xlsx / .pptx 再放进来。")
    return "这不是有效的 Office 文档（内部压缩包是坏的或空的）"


def _读压缩包(路径, 挑名字):
    try:
        包 = zipfile.ZipFile(路径)
    except (zipfile.BadZipFile, OSError) as 异常:
        raise ValueError(_像加密件吗(路径)) from 异常
    try:
        条目表 = 包.infolist()
        if len(条目表) > 包条目上限:
            raise ValueError("这个文件内部装了 " + str(len(条目表)) + " 个东西，超过上限，没敢读")
        for 条目 in 条目表:
            if 条目.file_size > 包单条上限:
                raise ValueError("内部有一条就超过 20 MB，没敢读：" + 条目.filename)
        if sum(条目.file_size for 条目 in 条目表) > 包总量上限:
            raise ValueError("解开后总量超过 80 MB，没敢读")
        名字表 = 包.namelist()
        结果 = {}
        try:
            for 名字 in 挑名字(名字表):
                if 名字 in 名字表:
                    结果[名字] = 包.read(名字)
        except Exception as 异常:
            raise ValueError("这个 Office 文档内部有损坏或加了密码，读不出来（"
                             + type(异常).__name__ + "）") from 异常
        return 结果
    finally:
        包.close()


def _解析(字节):
    try:
        return ET.fromstring(字节)
    except ET.ParseError as 异常:
        raise ValueError("文档内部格式不对，读不下去") from 异常


def _页号(名字):
    return int(re.search(r"(\d+)", 名字).group(1))


def _列号(字母):
    数 = 0
    for 字 in str(字母).upper():
        if "A" <= 字 <= "Z":
            数 = 数 * 26 + (ord(字) - ord("A") + 1)
    return 数


def _抽docx(路径):
    看到 = {"有图": False}

    def 挑(名字表):
        看到["有图"] = any(n.startswith("word/media/") for n in 名字表)
        return [n for n in 名字表 if n == "word/document.xml"]

    件 = _读压缩包(路径, 挑)
    if "word/document.xml" not in 件:
        raise ValueError("这个 .docx 里没有正文，可能是个空壳或已损坏")
    根 = _解析(件["word/document.xml"])
    段表 = []
    for 段 in 根.iter(W + "p"):
        一行 = ""
        for 节点 in 段.iter():
            if 节点.tag == W + "t":
                一行 += 节点.text or ""
            elif 节点.tag == W + "tab":
                一行 += "\t"
            elif 节点.tag in (W + "br", W + "cr"):
                一行 += "\n"
        if 一行.strip() and 段表 and 一行.strip() in 段表[-1]:
            continue
        段表.append(一行)
    文字 = "\n".join(段表)
    if not 文字.strip() and 看到["有图"]:
        raise ValueError("这份 .docx 里只有图片、没有文字。照片上的字读不出来。"
                         "请把文字打出来，或把图片单独拿出来（图片能走本机 OCR）。")
    return 文字


def _抽pptx(路径):
    def 挑(名字表):
        页表 = [n for n in 名字表 if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
        return sorted(页表, key=_页号)

    件 = _读压缩包(路径, 挑)
    if not 件:
        raise ValueError("这个 .pptx 里没有幻灯片，可能是个空壳或已损坏")
    块表 = []
    for 序号, 名字 in enumerate(sorted(件, key=_页号), 1):
        根 = _解析(件[名字])
        段表 = []
        for 段 in 根.iter(A + "p"):
            一行 = "".join(节点.text or "" for 节点 in 段.iter(A + "t"))
            if 一行.strip():
                段表.append(一行)
        块表.append("【第 " + str(序号) + " 页】\n" + "\n".join(段表))
    return "\n\n".join(块表)


def _抽xlsx(路径):
    def 挑(名字表):
        表页 = [n for n in 名字表 if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)]
        要的 = [n for n in ("xl/sharedStrings.xml", "xl/workbook.xml",
                          "xl/_rels/workbook.xml.rels") if n in 名字表]
        return 要的 + sorted(表页, key=_页号)

    件 = _读压缩包(路径, 挑)
    共享 = []
    if "xl/sharedStrings.xml" in 件:
        for 条 in _解析(件["xl/sharedStrings.xml"]).iter(表 + "si"):
            共享.append("".join(节点.text or "" for 节点 in 条.iter(表 + "t")))

    名字 = {}
    if "xl/workbook.xml" in 件 and "xl/_rels/workbook.xml.rels" in 件:
        目标 = {}
        for 关系 in _解析(件["xl/_rels/workbook.xml.rels"]).iter():
            if 关系.tag.endswith("Relationship") and 关系.get("Id"):
                目标[关系.get("Id")] = (关系.get("Target") or "").lstrip("/")
        关系号 = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        for 张 in _解析(件["xl/workbook.xml"]).iter(表 + "sheet"):
            路径 = 目标.get(张.get(关系号) or 张.get("id") or "", "")
            路径 = 路径 if 路径.startswith("xl/") else "xl/" + 路径.lstrip("/")
            名字[路径] = 张.get("name") or ""

    表页 = sorted([n for n in 件 if n.startswith("xl/worksheets/sheet")], key=_页号)
    if not 表页:
        raise ValueError("这个 .xlsx 里没有工作表，可能是个空壳或已损坏")
    块表 = []
    for 序号, 名字键 in enumerate(表页):
        标题 = 名字.get(名字键) or ("工作表" + str(序号 + 1))
        行表 = []
        for 行 in _解析(件[名字键]).iter(表 + "row"):
            格表 = []
            for 格 in 行.iter(表 + "c"):
                类 = 格.get("t") or ""
                if 类 == "inlineStr":
                    原文 = "".join(节点.text or "" for 节点 in 格.iter(表 + "t"))
                else:
                    值 = 格.find(表 + "v")
                    原文 = "" if 值 is None else (值.text or "")
                    if 类 == "s":
                        原文 = 共享[int(原文)] if 原文.isdigit() and int(原文) < len(共享) else ""
                列号 = _列号(re.sub(r"[^A-Za-z]", "", 格.get("r") or "")) or (len(格表) + 1)
                while len(格表) < 列号 - 1:
                    格表.append("")
                if len(格表) >= 列号:
                    格表[列号 - 1] = 原文
                else:
                    格表.append(原文)
            行表.append("\t".join(格表).rstrip("\t"))
        块表.append("【" + 标题 + "】\n" + "\n".join(行表))
    return "\n\n".join(块表)


def _用pypdf读(路径):
    读 = None
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        读 = PdfReader(路径)
        return "\n".join((页.extract_text() or "") for 页 in 读.pages)
    except Exception:
        return ""


def _有fitz():
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        pass
    try:
        import fitz
        return fitz
    except ImportError:
        return None


def _用fitz读(路径):
    库 = _有fitz()
    if 库 is None:
        return None
    try:
        with 库.open(路径) as 读:
            return "\n".join(页.get_text() for 页 in 读)
    except Exception:
        return ""


def _有PDF库():
    try:
        import pypdf
        return True
    except ImportError:
        pass
    return _有fitz() is not None


def _PDF文字层(路径):
    候选 = []
    for 读一份 in (_用pypdf读, _用fitz读):
        文字 = 读一份(路径)
        if 文字 is not None:
            候选.append(文字)
    if not 候选:
        raise ValueError(
            "读 PDF 需要一个可选的库，这台电脑上没找到。装上就能用：pip install pypdf"
            "（不装也不影响别的格式，只是 PDF 读不了。）"
        )
    return max(候选, key=lambda 文字: len(文字.strip()))


def 找powershell():
    for 名字 in ("powershell.exe", "powershell"):
        路径 = shutil.which(名字)
        if 路径:
            return 路径
    return None


def OCR可用():
    global _OCR可用, _OCR原因, _OCR探针时刻
    if _OCR可用:
        return True
    if _OCR原因 and (time.time() - _OCR探针时刻) < OCR失败缓存秒:
        return False
    if os.name != "nt" or not os.path.isfile(OCR脚本路径):
        return False
    if 找powershell() is None:
        return False
    好了, 原因 = _跑OCR探针()
    _OCR探针时刻 = time.time()
    if 好了:
        _OCR可用 = True
        _OCR原因 = ""
        return True
    _OCR原因 = 原因
    return False


def OCR不可用的原因():
    return _OCR原因


def _跑OCR探针():
    目录 = tempfile.mkdtemp(prefix="ocr探针_")
    try:
        图路径 = os.path.join(目录, "探针.png")
        出路径 = os.path.join(目录, "探针.txt")
        with open(图路径, "wb") as 文件:
            文件.write(base64.b64decode(OCR探针图))
        结果 = _跑OCR(图路径, 出路径)
        if 结果.returncode == 0:
            return True, ""
        文本 = ((结果.stderr or "") + "\n" + (结果.stdout or "")).strip()
        行表 = [行.strip() for 行 in 文本.splitlines() if 行.strip()]
        return False, (行表[-1][:120] if 行表 else "退出码 " + str(结果.returncode))
    except Exception as 异常:
        return False, type(异常).__name__ + "：" + str(异常)[:80]
    finally:
        shutil.rmtree(目录, ignore_errors=True)


def _跑OCR(图片路径, 输出路径):
    命令 = [找powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", OCR脚本路径, "-In", 图片路径, "-Out", 输出路径]
    return subprocess.run(命令, capture_output=True, text=True, timeout=OCR单次超时)


def _缩小图(图路径, 目标路径):
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(图路径) as 图:
            长边 = max(图.size)
            if 长边 <= 3000:
                return None
            比例 = 3000.0 / 长边
            小图 = 图.convert("RGB").resize((max(1, int(图.size[0] * 比例)),
                                          max(1, int(图.size[1] * 比例))))
        小图.save(目标路径)
        return 目标路径
    except Exception:
        return None


def _OCR一张(图片路径):
    if not OCR可用():
        raise ValueError("这台电脑上没有可用的本机 OCR（要 Windows 自带的那种），"
                         "读不了图片里的字。请先把图转成文字，存成 .txt 再放进来。")
    with tempfile.TemporaryDirectory(prefix="邵新OCR_") as 临时:
        输出 = os.path.join(临时, "文字.txt")
        try:
            运行 = _跑OCR(图片路径, 输出)
        except subprocess.TimeoutExpired:
            raise ValueError("本机 OCR 超过 " + str(OCR单次超时) + " 秒还没完，已放弃这张图。") from None
        if 运行.returncode == 3:
            小的 = _缩小图(图片路径, os.path.join(临时, "缩.png"))
            if 小的 is None:
                raise ValueError("这张图太大，超过了本机 OCR 能处理的上限。请先缩小或裁切再放进来。")
            try:
                运行 = _跑OCR(小的, 输出)
            except subprocess.TimeoutExpired:
                raise ValueError("本机 OCR 超过 " + str(OCR单次超时) + " 秒还没完，已放弃这张图。") from None
        if 运行.returncode == 2:
            raise ValueError("这台电脑上的 Windows OCR 没有可用的识别包（中文包没装），读不了图。")
        if 运行.returncode != 0:
            行表 = [行.strip() for 行 in (运行.stderr or 运行.stdout or "").splitlines()
                  if 行.strip()]
            有用的 = [行 for 行 in 行表
                    if "FullyQualifiedErrorId" not in 行 and not 行.startswith("+")]
            raise ValueError("本机 OCR 没能读这张图："
                             + ((有用的 or 行表 or ["没有更多信息"])[0])[:160])
        if not os.path.isfile(输出):
            return ""
        with open(输出, "r", encoding="utf-8-sig") as 文件:
            return 文件.read().strip()


def _抽图片(路径):
    文字 = _OCR一张(路径)
    if not 文字:
        raise ValueError("这张图里没认出文字（可能是纯图、太模糊，或字是竖排/倒了）。"
                         "请换一张清楚的，或先手工把字打出来。")
    return "（本机 OCR 转写，可能有错字）\n" + 文字


def _抽扫描PDF(路径):
    库 = _有fitz()
    if 库 is None:
        raise ValueError("这份 PDF 里没有文字层（是扫描件或图片版），要读它得先装上一个库：\n"
                         "    pip install pymupdf")
    块表 = []
    坏页 = []
    with tempfile.TemporaryDirectory(prefix="邵新OCR_") as 临时:
        with 库.open(路径) as 文档:
            总页 = len(文档)
            要读 = min(总页, OCR最多页)
            for 序号 in range(要读):
                try:
                    图路径 = os.path.join(临时, "第%03d页.png" % (序号 + 1))
                    文档[序号].get_pixmap(dpi=200).save(图路径)
                    文字 = _OCR一张(图路径).strip()
                except Exception as 异常:
                    坏页.append("第 " + str(序号 + 1) + " 页（" + str(异常)[:20] + "）")
                    continue
                if 文字:
                    块表.append("【第 " + str(序号 + 1) + " 页】\n" + 文字)
    if not 块表:
        raise ValueError("这份 PDF 每一页都没认出文字。请确认它是清楚的扫描件或照片。"
                         + ("（失败页：" + "、".join(坏页[:3]) + "）" if 坏页 else ""))
    尾巴 = ""
    if 总页 > 要读:
        尾巴 = "\n\n（这份 PDF 共 " + str(总页) + " 页，只转了前 " + str(要读) + " 页）"
    if 坏页:
        尾巴 += "\n（有 " + str(len(坏页)) + " 页没转成：" + "、".join(坏页[:5]) + "）"
    return "（本机 OCR 转写，可能有错字）\n" + "\n\n".join(块表) + 尾巴


def _抽pdf(路径):
    文字 = _PDF文字层(路径)
    if len(文字.strip()) >= PDF至少几个字才算有文字层:
        return 文字
    if not OCR可用():
        raise ValueError("这份 PDF 里没有文字层（多半是扫描件或图片版），而本机 OCR 也用不了，"
                         "所以读不出内容。请先把它转成文字再放进来。")
    return _抽扫描PDF(路径)


def _抽正文(路径, 后缀):
    if 后缀 in 文本后缀:
        return _读原始文字(路径)
    if 后缀 in 标记后缀:
        return _去标签(_读原始文字(路径))
    if 后缀 == ".docx":
        return _抽docx(路径)
    if 后缀 == ".pptx":
        return _抽pptx(路径)
    if 后缀 == ".xlsx":
        return _抽xlsx(路径)
    if 后缀 in PDF后缀:
        return _抽pdf(路径)
    if 后缀 in 图片后缀:
        return _抽图片(路径)
    return _读原始文字(路径)


def 能读(文件名):
    后缀 = os.path.splitext(文件名)[1].lower()
    if 后缀 in 文档后缀 or 后缀 in 文本后缀 or 后缀 in 标记后缀:
        return True, "直接读"
    if 后缀 in PDF后缀:
        if not _有PDF库():
            return False, "这台电脑上没装读 PDF 的库（pypdf 或 pymupdf），PDF 暂时读不了。"
        return True, "直接读；扫描件会自动转文字"
    if 后缀 in 图片后缀:
        if OCR可用():
            return True, "本机 OCR 转文字（可能有错字）"
        为什么 = OCR不可用的原因()
        return False, ("这是图片，但这台电脑上的本机 OCR 现在跑不起来"
                    + ("（" + 为什么 + "）" if 为什么 else "")
                    + "。请先把图里的字转成文字（存成 .txt）再放进来。")
    if 后缀 in 旧版后缀:
        return False, "这是 Office 2003 的老格式，程序读不了。请用 WPS 或 Word 打开后「另存为」.docx / .xlsx / .pptx 再放进来。"
    if not 后缀:
        return True, "没有后缀，按文本试读"
    return False, "认不出这个格式。请先转成常见格式（PDF / .docx / .pptx / .xlsx / .txt / 图片）再放进来。"


def 支持格式说明():
    图话 = ("照片和扫描图由本机 OCR 转成文字（不联网、不外发，可能有错字）；扫描版 PDF 会逐页转。"
            if OCR可用() else
            "这台电脑上没有可用的本机 OCR，所以照片和扫描图读不出文字。请先把图上的字打出来。")
    PDF话 = "" if _有PDF库() else "（这台电脑还没装读 PDF 的库，PDF 暂时读不了）"
    return ("常见格式都能直接读：Word / PPT / Excel（.docx / .pptx / .xlsx）、PDF" + PDF话
            + "、文本与表格（.txt / .md / .csv / .json …）、网页（.html）。"
            + 图话 + "Office 2003 老格式（.doc / .xls / .ppt）请先另存为新格式。")


def 读材料(路径):
    try:
        大小 = os.path.getsize(路径)
    except OSError:
        raise ValueError("找不到这份材料：" + os.path.basename(str(路径))) from None
    if 大小 > 单文件上限:
        raise ValueError("这份材料有 " + str(round(大小 / 1048576, 1)) + " MB，超过了 "
                         + str(单文件上限 // 1048576) + " MB 的上限。请先拆开或转小一点。")
    可读, 说明 = 能读(os.path.basename(路径))
    if not 可读:
        raise ValueError(说明)
    正文 = _封顶(清洗文字(_抽正文(路径, os.path.splitext(路径)[1].lower())))
    if not 正文.strip():
        raise ValueError("这份材料里一个字都没读到（空文件，或者格式不对）："
                         + 说明_empty_hint(路径))
    return 正文


def 说明_empty_hint(路径):
    后缀 = os.path.splitext(str(路径))[1].lower()
    if 后缀 == ".pdf":
        return "扫描件 PDF 没有文字层，要先用 OCR 转成文字（把图导出来放进 材料/ 也行）"
    if 后缀 in (".doc", ".ppt", ".xls"):
        return "这是老版 Office 格式，请另存为 .docx / .pptx / .xlsx 再放进来"
    if 后缀 in 图片后缀:
        return "图片要能读出字得有本机 OCR（在「环境配置」里能看到能不能用）"
    return "打开看看是不是空的；有些文件只存了图片、没有文字"


def 校验材料名(文件名):
    名字 = str(文件名 or "").strip().replace("\\", "/")
    if not 名字:
        raise ValueError("材料文件名不能为空")
    if 名字.startswith("/") or ":" in 名字:
        raise ValueError("材料名不能是绝对路径或带盘符：" + repr(文件名))
    for 一段 in 名字.split("/"):
        if 一段 in ("", ".", ".."):
            raise ValueError("材料名里不能有空路径段或上跳段（`.` / `..`）：" + repr(文件名))
    return 名字


def 材料路径(文件名):
    相对 = 校验材料名(文件名)
    根 = 配置.取目录("材料")
    完整 = os.path.join(根, *相对.split("/"))
    根真身 = os.path.realpath(根)
    真身 = os.path.realpath(完整)
    if 真身 != 根真身 and not 真身.startswith(根真身 + os.sep):
        raise ValueError("这个材料名指到 材料/ 外面去了：" + repr(文件名))
    if os.path.isdir(完整):
        raise ValueError("这是个文件夹、不是文件：" + repr(文件名) + "，请选里面的某个文件")
    return 完整


def 材料清单():
    根 = 配置.取目录("材料")
    if not os.path.isdir(根):
        return []

    条目表 = []
    根真身 = os.path.realpath(根)
    去过的真身 = {根真身}
    for 当前目录, 子目录表, 文件表 in os.walk(根):
        留住 = []
        for 名 in 子目录表:
            if 名.startswith("."):
                continue
            真身 = os.path.realpath(os.path.join(当前目录, 名))
            if 真身 in 去过的真身:
                continue
            if not 真身.startswith(根真身 + os.sep):
                continue
            去过的真身.add(真身)
            留住.append(名)
        子目录表[:] = sorted(留住)
        for 文件名 in sorted(文件表):
            if 文件名.startswith(".") or 文件名 == "说明.md":
                continue
            if len(条目表) >= 材料条数上限:
                break
            完整路径 = os.path.join(当前目录, 文件名)
            可读, 说明 = 能读(文件名)
            条目表.append({
                "文件名": os.path.relpath(完整路径, 根).replace(os.sep, "/"),
                "大小(字节)": os.path.getsize(完整路径),
                "格式": (os.path.splitext(文件名)[1].lower() or "无后缀"),
                "能不能读": "能" if 可读 else "不能",
                "说明": 说明,
            })
    return sorted(条目表, key=lambda 条: 条["文件名"])


def 参考资料清单():
    目录 = 配置.取目录("参考资料")
    if not os.path.isdir(目录):
        return []

    条目表 = []
    去过的真身 = {os.path.realpath(目录)}
    for 当前目录, 子目录表, 文件表 in os.walk(目录):
        留住 = []
        for 名 in 子目录表:
            if 名.startswith("."):
                continue
            真身 = os.path.realpath(os.path.join(当前目录, 名))
            if 真身 in 去过的真身:
                continue
            去过的真身.add(真身)
            留住.append(名)
        子目录表[:] = 留住
        for 文件名 in sorted(文件表):
            if 文件名.startswith(".") or 文件名 == "说明.md":
                continue
            if len(条目表) >= 参考资料条数上限:
                break
            完整路径 = os.path.join(当前目录, 文件名)
            可读, 说明 = 能读(文件名)
            条目表.append({
                "文件名": os.path.relpath(完整路径, 目录).replace(os.sep, "/"),
                "大小(字节)": os.path.getsize(完整路径),
                "格式": (os.path.splitext(文件名)[1].lower() or "无后缀"),
                "能不能读": "能" if 可读 else "不能",
                "说明": 说明,
            })
    return sorted(条目表, key=lambda 条: 条["文件名"])
