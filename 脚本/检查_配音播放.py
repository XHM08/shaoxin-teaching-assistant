
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 配置

可能的Edge = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
临时页名 = "_配音播放自检_%d.html" % os.getpid()
标记 = "自检结果标记"


def 找Edge():
    for 路径 in 可能的Edge:
        if os.path.isfile(路径):
            return 路径
    return None


测试脚本 = """
<script>
(async () => {
  const 结果 = [];
  const 记 = (名, 过, 说) => 结果.push({名前: 名, 过: !!过, 说: String(说 || '')});

  // play/pause 换成替身：无头里真播会被自动播放策略拦，靠它判不出对错。
  const 调用 = [];
  HTMLMediaElement.prototype.play = function () { 调用.push('play'); this.__假播 = true; return Promise.resolve(); };
  HTMLMediaElement.prototype.pause = function () { 调用.push('pause'); this.__假播 = false; };
  // paused 是只读 getter：不模拟它，lecPause 里那句 !播放器.paused 永远是 false，
  // "刚才在播吗"就永远记不下来，恢复时也不会接着念。那是测试假象，不是代码对错
  Object.defineProperty(HTMLMediaElement.prototype, 'paused', {
    get() { return !this.__假播; }, configurable: true
  });

  // 页面末尾那个初始化 IIFE 是异步的：它会（在几千毫秒内）调 lecReset()，
  // 把 LEC.items/index/auto 一起清掉。不等它落定就开始测，会看到"明明设了 auto=true
  // 却在事件里读到 false"这种假象，白查半天代码。
  await new Promise(r => setTimeout(r, 2500));

  const 音频 = $('lecAudio');
  const 盒 = $('lecVoiceBox');
  const 两页 = [
    {页: 1, 标题: '第一页', 要点: '甲', 讲稿: '这一页有配音', 音频: '/配音/自检课件_配音/第1页.wav',
     页图: '/课件图/自检课件_页图/page1.png'},
    {页: 2, 标题: '第二页', 要点: '乙', 讲稿: '这一页没有配音', 音频: ''}
  ];

  // ① 有配音的页：音频条要露出来，源要换成这一页的（中文路径逐段编码）
  LEC.items = 两页; LEC.index = 0; LEC.auto = false;
  调用.length = 0;
  lecRender();
  const 期望源 = '/配音/' + encodeURIComponent('自检课件_配音') + '/' + encodeURIComponent('第1页.wav');
  const 实际源 = 音频.getAttribute('src') || '';
  记('① 有配音的页：音频条露出来 + 源换成这一页的（中文已编码）',
      !盒.classList.contains('hide') && 实际源 === 期望源, 实际源);

  // ② 勾着「翻页自动播放」时，换页要真的去播
  $('lecAudioAuto').checked = true;
  调用.length = 0;
  LEC.index = 0; lecRender();
  记('② 勾了自动播 → 换页时会去 play()', 调用.includes('play'), 调用.join(','));

  // ③ 音频说完 → 自动翻到下一页（有音频时就是这么推的，不按字数估）
  LEC.items = 两页; LEC.index = 0; LEC.auto = true;
  lecRender();
  let 收到 = false;
  音频.addEventListener('ended', () => { 收到 = true; });
  let 报错 = '';
  try { 音频.dispatchEvent(new Event('ended')); } catch (e) { 报错 = e.message; }
  await new Promise(r => setTimeout(r, 80));
  记('③ 配音说完 → 自动翻到下一页', LEC.index === 1,
     '翻到第 ' + (LEC.index + 1) + ' 页；事件收到=' + 收到 + '；typeof lecNextPage=' + typeof lecNextPage
     + '；auto=' + LEC.auto + '；报错=' + 报错);

  // ④ 翻到没配音的那页：音频条收起来、源清掉（别让老师对着空播放器猜）
  记('④ 没配音的页：音频条收起 + 源清掉',
      LEC.index === 1 && 盒.classList.contains('hide') && !音频.getAttribute('src'),
      '隐藏=' + 盒.classList.contains('hide') + ' 源=' + (音频.getAttribute('src') || '（已清）'));

  // ⑤ 暂停自动播放时，音频说话不算数（不该自己翻页）
  LEC.items = 两页; LEC.index = 0; LEC.auto = false;
  lecRender();
  音频.dispatchEvent(new Event('ended'));
  await new Promise(r => setTimeout(r, 60));
  记('⑤ 没在自动播放时，音频说完也不翻页', LEC.index === 0, '还在第 ' + (LEC.index + 1) + ' 页');

  // ⑩ 有页图 → 显示真实页面（中文路径逐段编码）
  LEC.items = 两页; LEC.index = 0; LEC.auto = false;
  lecRender();
  const 期望图 = '/课件图/' + encodeURIComponent('自检课件_页图') + '/' + encodeURIComponent('page1.png');
  const 图 = $('lecShot');
  记('⑩ 有页图 → 显示真实页面（编码对、不隐藏）',
     !图.classList.contains('hide') && (图.getAttribute('src') || '') === 期望图,
     (图.getAttribute('src') || '（无）'));
  LEC.index = 1; lecRender();
  记('⑪ 没页图的那页 → 收起且清源（不留个破图占地方）',
     图.classList.contains('hide') && !图.getAttribute('src'),
     '隐藏=' + 图.classList.contains('hide') + ' 源=' + (图.getAttribute('src') || '（已清）'));

  // ⑥ 学生按「我有问题」：配音要停（界面上写着"暂停中"，喇叭里不能还在念）
  LEC.items = 两页; LEC.index = 0; LEC.auto = true;
  lecRender();
  调用.length = 0;
  lecPause();
  记('⑥ 「我有问题」→ 配音停掉', 调用.includes('pause'), 调用.join(','));
  记('⑦ 暂停时记下了"刚才在播"，供恢复时接着念', LEC.audioWasPlaying === true,
      'audioWasPlaying=' + LEC.audioWasPlaying);

  // ⑧ 答完继续：按勾选接着念
  调用.length = 0;
  $('lecAudioAuto').checked = true;
  doResume();
  记('⑧ 答完继续 → 配音接着念', 调用.includes('play'), 调用.join(','));

  // ⑨ 结束上课：停声清源，别在后台接着念
  LEC.items = 两页; LEC.index = 0;
  lecRender();
  调用.length = 0;
  lecReset();
  记('⑨ 结束上课 → 停声 + 清源 + 页面图收起',
     调用.includes('pause') && !音频.getAttribute('src') && $('lecShot').classList.contains('hide'),
     '调用=' + 调用.join(',') + ' 源=' + (音频.getAttribute('src') || '（已清）'));

  const 盒2 = document.createElement('div');
  盒2.id = '自检结果标记';
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
    页面 = 页面.replace("</body>", 测试脚本 + "</body>", 1)
    with open(临时页, "w", encoding="utf-8") as 文件:
        文件.write(页面)

    地址 = "http://127.0.0.1:%d%s" % (端口, urllib.parse.quote("/网页/" + 临时页名))
    结果 = []
    try:
        跑 = subprocess.run([edge, "--headless=new", "--disable-gpu", "--no-first-run",
                            "--disable-extensions", "--virtual-time-budget=8000",
                            "--dump-dom", 地址],
                           capture_output=True, text=True, encoding="utf-8", timeout=120)
        dom = 跑.stdout or ""
        if len(dom) < 5000:
            结果.append(("整页渲染出来了", False, "DOM 只有 %d 字符，Edge 可能没真渲染" % len(dom)))
        else:
            结果.append(("整页渲染出来了", True, "%d 字符" % len(dom)))
        找 = re.search(r'id="' + 标记 + r'"[^>]*>(.*?)</div>', dom, re.S)
        if not 找:
            结果.append(("测试脚本跑到了结尾", False, "没找到结果标记：脚本可能中途抛错了"))
        else:
            import html as html模块
            条 = json.loads(html模块.unescape(找.group(1)))
            for 一 in 条:
                结果.append((一["名前"], 一["过"], 一["说"]))
    except subprocess.TimeoutExpired:
        结果.append(("Edge 跑完", False, "超时（120 秒）"))
    except Exception as 异常:
        结果.append(("Edge 跑完", False, type(异常).__name__ + "：" + str(异常)[:90]))
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
