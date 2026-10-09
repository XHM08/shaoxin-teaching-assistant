
import glob
import html as html模块
import json
import os
import re
import subprocess
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 配置, 课件

可能的Edge = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
临时页名 = "_配音播放真数据自检_%d.html" % os.getpid()
标记 = "自检结果标记"
结果 = []


def 检查(名字, 通过, 说明=""):
    结果.append((名字, bool(通过), 说明))


def 找Edge():
    for 路径 in 可能的Edge:
        if os.path.isfile(路径):
            return 路径
    return None


def 挑课件():
    输出 = 配置.取目录("课件输出")
    课 = sorted(glob.glob(os.path.join(输出, "*.pptx")), key=os.path.getmtime)
    for 路径 in reversed(课):
        主干 = os.path.splitext(os.path.basename(路径))[0]
        if os.path.isdir(os.path.join(输出, 主干 + "_配音")) and \
           os.path.isdir(os.path.join(输出, 主干 + "_页图")):
            return 路径, 主干
    return None


测试脚本 = """
<script>
(async () => {
  const 结果 = [];
  const 记 = (名, 过, 说) => 结果.push({名前: 名, 过: !!过, 说: String(说 || '')});
  const 调用 = [];
  HTMLMediaElement.prototype.play = function () { 调用.push('play'); this.__假播 = true; return Promise.resolve(); };
  HTMLMediaElement.prototype.pause = function () { 调用.push('pause'); this.__假播 = false; };
  Object.defineProperty(HTMLMediaElement.prototype, 'paused', {
    get() { return !this.__假播; }, configurable: true
  });
  // 页面末尾那个初始化 IIFE 是异步的：不等它落定就测，会看到"设了 auto 又被清掉"的假象
  await new Promise(r => setTimeout(r, 2500));

  const 条目 = __条目__;
  const 期音1 = __期音1__, 期图1 = __期图1__, 期音末 = __期音末__, 期图末 = __期图末__;
  const 音频 = $('lecAudio'), 图 = $('lecShot'), 盒 = $('lecVoiceBox');

  LEC.items = 条目; LEC.index = 0; LEC.auto = false;
  lecRender();
  const 源1 = 音频.getAttribute('src') || '', 图源1 = 图.getAttribute('src') || '';
  记('① 真课件第 1 页：音频源正确（中文逐段编码）', 源1 === 期音1 && !盒.classList.contains('hide'), 源1);

  LEC.index = 条目.length - 1; lecRender();
  const 源末 = 音频.getAttribute('src') || '', 图源末 = 图.getAttribute('src') || '';
  记('② 翻到最后一页：音频源跟着换（不是还在念上一页）', 源末 === 期音末, 源末);
  记('③ 页图源也跟着换（每页是自己的那张）', 图源1 === 期图1 && 图源末 === 期图末,
     图源1 + ' → ' + 图源末);

  // 真服务上真取一次（浏览器真的会发的那个请求）
  let 音码 = 0, 音长 = 0, 音错 = '';
  try {
    const r = await fetch(条目[0].音频);
    音码 = r.status; 音长 = (await r.arrayBuffer()).byteLength;
  } catch (e) { 音错 = e.message; }
  记('④ 真服务上音频取得到（200 且不是空文件）', 音码 === 200 && 音长 > 50000,
     '码=' + 音码 + ' 字节=' + 音长 + ' ' + 音错);

  // 页图真的能解码：不是"有个 src 就算过"
  const 宽 = await new Promise(r => {
    const i = new Image();
    i.onload = () => r(i.naturalWidth); i.onerror = () => r(0);
    i.src = 期图1;
  });
  记('⑤ 页图真的解码成功（浏览器自己认这张图）', 宽 > 200, '像素宽=' + 宽);

  LEC.items = 条目; LEC.auto = false;
  const 音源们 = [], 图源们 = [];
  for (let i = 0; i < 条目.length; i++) {
    LEC.index = i; lecRender();
    音源们.push(音频.getAttribute('src') || '');
    图源们.push(图.getAttribute('src') || '');
  }
  const 音有 = 音源们.filter(Boolean), 图有 = 图源们.filter(Boolean);
  记('⑥ 每页的音频源都不同（没有复制粘贴同一条）',
     new Set(音有).size === 音有.length, 音源们.join(' | '));
  记('⑦ 每页的页图源都不同', new Set(图有).size === 图有.length, 图源们.join(' | '));

  调用.length = 0;
  lecReset();
  记('⑧ 结束上课 → 停声 + 清源', 调用.includes('pause') && !音频.getAttribute('src'), 调用.join(','));

  const 盒2 = document.createElement('div');
  盒2.id = '__标记__';
  盒2.textContent = JSON.stringify(结果);
  盒2.style.display = 'none';
  document.body.appendChild(盒2);
})();
</script>
"""


def main():
    edge = 找Edge()
    if not edge:
        print("  找不到 Edge，这个自检跑不了。找过这些位置：" + "、".join(可能的Edge))
        return 1
    选中 = 挑课件()
    if not 选中:
        print("  跳过：课件输出/ 里没有同时带配音与页图的课件，这一条这次没验")
        print("  （等生成过一份带配音的课件再跑，或先说清：不要把这个跳过当成通过）")
        return 0
    课件路径, 主干 = 选中
    输出 = 配置.取目录("课件输出")
    页们 = 课件.读各页(课件路径)
    print("  用这份真课件：%s（%d 页）" % (os.path.basename(课件路径), len(页们)))
    条目 = []
    有音 = 0
    for 一页 in 页们:
        号 = 一页["页"]
        文件名 = "第%d页.wav" % 号
        存在 = os.path.isfile(os.path.join(输出, 主干 + "_配音", 文件名))
        有音 += 1 if 存在 else 0
        条目.append({"页": 号, "标题": 一页["标题"], "要点": 一页["要点"],
                   "讲稿": 一页["备注"],
                   "音频": ("/配音/%s_配音/%s" % (主干, 文件名)) if 存在 else "",
                   "页图": "/课件图/%s_页图/page%d.png" % (主干, 号)})
    检查("这份真课件挑得出来：%d 页里 %d 页有配音、每页都有页图" % (len(条目), 有音),
        有音 == len(条目) and len(条目) > 1, os.path.basename(课件路径))
    if 有音 != len(条目):
        print("  跳过：这份课件有的页没有配音，换了另一份再说，这一条这次没验")
        return 0

    期音1 = "/配音/" + urllib.parse.quote(主干 + "_配音") + "/" + urllib.parse.quote("第1页.wav")
    期图1 = "/课件图/" + urllib.parse.quote(主干 + "_页图") + "/" + urllib.parse.quote("page1.png")
    末页 = 条目[-1]["页"]
    期音末 = "/配音/" + urllib.parse.quote(主干 + "_配音") + "/" + urllib.parse.quote("第%d页.wav" % 末页)
    期图末 = "/课件图/" + urllib.parse.quote(主干 + "_页图") + "/" + urllib.parse.quote("page%d.png" % 末页)

    网页目录 = os.path.join(配置.根目录, "网页")
    原页 = os.path.join(网页目录, "首页.html")
    临时页 = os.path.join(网页目录, 临时页名)
    端口 = 配置.取端口()

    import socket
    探 = socket.socket()
    探.settimeout(3)
    try:
        探.connect(("127.0.0.1", 端口))
    except Exception:
        print("  服务没起（127.0.0.1:%d 连不上）。先启动服务再跑这个检查。" % 端口)
        return 1
    finally:
        探.close()

    with open(原页, "r", encoding="utf-8") as 文件:
        页面 = 文件.read()
    if "</body>" not in 页面:
        print("  首页.html 里找不到 </body>，没法接测试脚本")
        return 1
    脚本 = (测试脚本.replace("__条目__", json.dumps(条目, ensure_ascii=False))
                  .replace("__期音1__", json.dumps(期音1))
                  .replace("__期图1__", json.dumps(期图1))
                  .replace("__期音末__", json.dumps(期音末))
                  .replace("__期图末__", json.dumps(期图末))
                  .replace("__标记__", 标记))
    with open(临时页, "w", encoding="utf-8") as 文件:
        文件.write(页面.replace("</body>", 脚本 + "</body>", 1))

    地址 = "http://127.0.0.1:%d%s" % (端口, urllib.parse.quote("/网页/" + 临时页名))
    try:
        跑 = subprocess.run([edge, "--headless=new", "--disable-gpu", "--no-first-run",
                           "--disable-extensions", "--virtual-time-budget=9000",
                           "--dump-dom", 地址],
                          capture_output=True, text=True, encoding="utf-8", timeout=150)
        dom = 跑.stdout or ""
        if len(dom) < 5000:
            检查("整页渲染出来了", False, "DOM 只有 %d 字符，Edge 可能没真渲染" % len(dom))
        else:
            检查("整页渲染出来了", True, "%d 字符" % len(dom))
        找 = re.search(r'id="' + 标记 + r'"[^>]*>(.*?)</div>', dom, re.S)
        if not 找:
            检查("测试脚本跑到了结尾", False, "没找到结果标记：脚本可能中途抛错了")
        else:
            for 一 in json.loads(html模块.unescape(找.group(1))):
                检查(一["名前"], 一["过"], 一["说"])
    except subprocess.TimeoutExpired:
        检查("Edge 跑完", False, "超时（150 秒）")
    except Exception as 异常:
        检查("Edge 跑完", False, type(异常).__name__ + "：" + str(异常)[:90])
    finally:
        try:
            os.remove(临时页)
        except OSError:
            pass

    print()
    坏 = 0
    for 名字, 过, 说明 in 结果:
        print(("  通过  " if 过 else "  失败  ") + 名字 + ("　→　" + 说明 if 说明 else ""))
        坏 += 0 if 过 else 1
    print("全部 %d 项通过" % len(结果) if not 坏 else "%d 项失败" % 坏)
    return 0 if not 坏 else 1


if __name__ == "__main__":
    sys.exit(main())
