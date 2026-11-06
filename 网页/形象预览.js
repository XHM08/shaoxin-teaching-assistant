

const 形象目录 = '/网页/形象/';
const 剪辑 = {
  待机: { 轮数: 0, 时长: 2830 },
  说话: { 轮数: 0, 时长: 520 },
  挥手: { 轮数: 2, 时长: 1650 },
  举手: { 轮数: 2, 时长: 1660 },
  指向: { 轮数: 2, 时长: 1660 },
  微笑: { 轮数: 0, 时长: 2830 },
  开心: { 轮数: 0, 时长: 2400 },
  生气: { 轮数: 0, 时长: 2830 },
  难过: { 轮数: 0, 时长: 2830 },
  惊讶: { 轮数: 0, 时长: 2400 },
  思考: { 轮数: 0, 时长: 2400 },
};

const 表情们 = ['微笑', '开心', '生气', '难过', '惊讶', '思考'];
const 动作们 = ['挥手', '举手', '指向'];

let 覆盖 = null;
let 说话中 = false;
let 计时 = null;
const 已回落 = new Set();

function 写状态(词) {
  const 标 = document.getElementById('当前状态');
  if (标) 标.textContent = 词;
}

function 提示(词) {
  const 框 = document.getElementById('探测结果');
  if (框) 框.textContent = 词;
}

function 同步说话钮() {
  const 钮 = document.getElementById('说话钮');
  if (钮) 钮.textContent = 说话中 ? '停止说话' : '说话';
}

function 换图(名, 强制重播) {
  const 图 = document.getElementById('头像');
  if (!图 || !剪辑[名]) return;
  图.dataset.名 = 名;
  图.setAttribute('src', 形象目录 + 名 + '.webp' + (强制重播 ? '?r=' + Date.now() : ''));
  写状态(名);
}

function 回待机() {
  clearTimeout(计时);
  说话中 = false;
  同步说话钮();
  换图(覆盖 || '待机');
}

function 播动作(名) {
  const 记 = 剪辑[名];
  if (!记) return;
  clearTimeout(计时);
  说话中 = false;
  同步说话钮();
  换图(名, true);
  计时 = setTimeout(() => 回待机(), 记.时长 * Math.max(1, 记.轮数));
}

function 选表情(名) {
  if (名 === '无') {
    覆盖 = null;
    回待机();
    return;
  }
  覆盖 = 名;
  clearTimeout(计时);
  换图(名, true);
}

function 切说话() {
  说话中 = !说话中;
  同步说话钮();
  if (说话中) {
    clearTimeout(计时);
    换图('说话', true);
  } else {
    回待机();
  }
}

function 搭按钮() {
  const 行 = document.getElementById('按钮行');
  if (!行) return;
  const 加 = (字, 动作, 号) => {
    const 钮 = document.createElement('button');
    钮.textContent = 字;
    if (号) 钮.id = 号;
    钮.addEventListener('click', 动作);
    行.appendChild(钮);
    return 钮;
  };
  动作们.forEach(名 => 加(名, () => 播动作(名)));
  加('说话', 切说话, '说话钮');
  表情们.forEach(名 => 加(名, () => 选表情(名)));
  加('表情清空', () => 选表情('无'));
}

function 探(路) {
  return fetch(路, { method: 'HEAD' }).then(回 => 回.status).catch(() => 0);
}

function 探一次() {
  const 名们 = Object.keys(剪辑);
  提示('探测中…');
  Promise.all(名们.map(名 => Promise.all([
    探(形象目录 + 名 + '.webp'),
    探(形象目录 + 名 + '.gif'),
  ]).then(([网, 兜]) => ({ 名, 网, 兜 })))).then(列 => {
    const 缺网 = 列.filter(一 => 一.网 !== 200).map(一 => 一.名);
    const 缺兜 = 列.filter(一 => 一.兜 !== 200).map(一 => 一.名);
    提示('webp ' + (名们.length - 缺网.length) + '/' + 名们.length
      + '，gif ' + (名们.length - 缺兜.length) + '/' + 名们.length
      + (缺网.length ? '；缺 webp：' + 缺网.join('、') : '')
      + (缺兜.length ? '；缺 gif：' + 缺兜.join('、') : '')
      + (已回落.size ? '；这次用 gif 兜过：' + Array.from(已回落).join('、') : ''));
  });
}

document.addEventListener('DOMContentLoaded', () => {
  const 图 = document.getElementById('头像');
  if (图) {
    图.addEventListener('error', () => {
      const 名 = 图.dataset.名 || '待机';
      if (已回落.has(名)) {
        提示('连 gif 都取不到：' + 名);
        return;
      }
      已回落.add(名);
      提示('webp 取不到，已回落 gif：' + 名);
      图.setAttribute('src', 形象目录 + 名 + '.gif');
    });
    图.addEventListener('load', () => {
      const 名 = 图.dataset.名;
      if (名 && 图.getAttribute('src').indexOf('.webp') > 0) 已回落.delete(名);
    });
  }
  const 底 = document.getElementById('底色');
  if (底) {
    底.addEventListener('click', () => {
      const 框 = document.getElementById('画框');
      框.classList.toggle('深色');
      底.textContent = 框.classList.contains('深色') ? '切白底' : '切深色底';
    });
  }
  const 探钮 = document.getElementById('探测');
  if (探钮) 探钮.addEventListener('click', 探一次);
  搭按钮();
  同步说话钮();
  换图('待机');
  探一次();
});
