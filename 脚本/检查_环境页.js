const fs = require('fs');
const path = require('path');

const root = path.dirname(__dirname);
const html = fs.readFileSync(path.join(root, '网页', '首页.html'), 'utf8');

function sliceScript(text) {
  const a = text.indexOf('<script>');
  const b = text.indexOf('</script>');
  if (a < 0 || b < 0) throw new Error('首页.html 里找不到 <script> 块');
  return text.slice(a + 8, b);
}

const js = sliceScript(html);
const els = {};

function makeEl(id) {
  const cls = new Set();
  return {
    id, textContent: '', innerHTML: '', className: '', value: '',
    classList: {
      add: c => cls.add(c),
      remove: c => cls.delete(c),
      toggle: (c, f) => {
        if (f === undefined) { cls.has(c) ? cls.delete(c) : cls.add(c); }
        else if (f) { cls.add(c); } else { cls.delete(c); }
      },
      contains: c => cls.has(c)
    },
    addEventListener() {}, focus() {}, querySelector: () => null
  };
}

global.document = {
  getElementById: id => (els[id] || (els[id] = makeEl(id))),
  querySelectorAll: () => [],
  querySelector: () => null
};
global.window = { scrollTo() {} };
global.fetch = () => Promise.reject(new Error('自测环境没有 fetch'));

const TESTS = `
;(function () {
  if (typeof envShow !== 'function') { throw new Error('抽出来的脚本里没有 envShow'); }

  var scan = { 提示: 'n', 条目: [
    { '代号': 'python', '环境': 'Python', '状态': '已就绪', '版本 / 说明': '3.12',
      '怎么装': '—', '补充提示': '' },
    { '代号': 'wsl', '环境': 'WSL', '状态': '未配齐', '版本 / 说明': '没有发行版',
      '怎么装': '需管理员权限', '补充提示': 'wsl --install -d Ubuntu' }
  ]};
  envShow(scan);
  checks.push(['① 扫描后总表有安装按钮', els['envTable'].innerHTML.indexOf('data-env="wsl"') >= 0]);
  checks.push(['② 扫描后提醒出现', els['envAlert'].innerHTML.indexOf('还没配齐') >= 0]);
  checks.push(['③ 首页角标变成"有 1 项未配齐"', els['envState'].textContent.indexOf('未配齐') >= 0]);

  var before = els['envTable'].innerHTML;
  var plan = { 提示: 'n', 环境项: 'wsl', 需要确认: false, 条目: [
    { '环境': 'WSL', '当前状态': '未配齐', '现在': '功能已启用，但没有发行版',
      '安装方式': '手动（需管理员）' } ]};
  envShow(plan);
  checks.push(['④ 单项结果没冲掉总表', els['envTable'].innerHTML === before]);
  checks.push(['⑤ 单项结果写进 envPlan', els['envPlan'].innerHTML.indexOf('WSL') >= 0]);
  checks.push(['⑥ 单项结果里没有空按钮', els['envPlan'].innerHTML.indexOf('data-env') < 0]);
})();
`;

const checks = [];
eval(js + '\n' + TESTS);

let bad = 0;
for (const pair of checks) {
  console.log((pair[1] ? '  通过  ' : '  失败  ') + pair[0]);
  if (!pair[1]) bad += 1;
}
console.log(bad === 0 ? '全部 ' + checks.length + ' 项通过' : bad + ' 项失败');
process.exit(bad === 0 ? 0 : 1);
