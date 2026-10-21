const $ = id => document.getElementById(id);
let ABILITIES = null;
const SETTINGS = { items: [] };
const LEC = { items: [], index: 0, skill: '', auto: false, timer: null };


function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}


function brief(s, n) {
  const t = String(s == null ? '' : s);
  return t.length > n ? t.slice(0, n) + '…' : t;
}

async function api(path, opts) {
  let r;
  try {
    r = await fetch(path, opts);
  } catch (e) {
    
    if (location.protocol === 'file:') {
      throw new Error('这个页面是用文件方式双击打开的（file://），连不上本地服务。'
        + '请双击「邵新.exe」；或在命令行运行 本地服务.py，按它打印的地址在浏览器里打开。');
    }
    throw new Error('连不上本地服务（网络层就失败了）。'
      + '检查：服务还开着吗？地址是不是 http://127.0.0.1:端口/ ');
  }
  const t = await r.text();
  let d;
  try { d = JSON.parse(t); } catch (e) { throw new Error('服务返回的不是 JSON：' + t.slice(0, 200)); }
  if (!r.ok) throw new Error(d.错误 || ('HTTP ' + r.status));
  return d;
}

async function 能力() {
  if (!ABILITIES) ABILITIES = (await api('/api/能力')).条目;
  return ABILITIES;
}

async function paramOptions(ability, param) {
  const list = await 能力();
  const ab = list.find(a => a.代号 === ability);
  if (!ab) return [];
  const p = ab.参数.find(x => x.代号 === param);
  return (p && p.可选项) || [];
}




const SID = Math.random().toString(36).slice(2) + Date.now().toString(36);

function run(ability, args) {
  return api('/api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 能力: ability, 参数: args || {}, 会话: SID })
  });
}

function say(el, text, cls) {
  el.className = 'notice ' + (cls || '');
  el.textContent = text;
}

function fillSelect(sel, list, emptyText, 默认值) {
  sel.innerHTML = list.length
    ? list.map(v => '<option value="' + esc(v) + '">' + esc(v) + '</option>').join('')
    : '<option value="">' + esc(emptyText) + '</option>';
  
  
  
  if (默认值 && list.indexOf(默认值) >= 0) sel.value = 默认值;
}

async function fillOptions(ability, param, selectId, emptyText) {
  const sel = $(selectId);
  try {
    fillSelect(sel, await paramOptions(ability, param), emptyText);
  } catch (e) {
    sel.innerHTML = '<option value="">读取失败：' + esc(e.message) + '</option>';
  }
}

const MSG_OUT = [
  ['distillMsg', 'distillOut'],
  ['pptMsg', 'pptOut'],
  ['arcMsg', null],
  ['skillMsg', null],
  ['lecMsg', null],
  ['setMsg', null],
  ['cacheMsg', null],
  ['chatMsg', null],
  ['pcMsg', 'pcOut'],
  ['envMsg', 'envOut'],
  ['cmdMsg', 'cmdOut'],
  ['qaStuMsg', 'qaStuOut'],
  ['netOut', null],
  ['regMsg', null],
  ['diagMsg', null],
  ['evalMsg', null],
  ['evalSaveMsg', null],
  ['skillEditMsg', null],
  ['fbMsg', null],
  ['fbMarkMsg', null],
  ['fbDiagMsg', 'fbDiagOut']
];


function clearResults() {
  MSG_OUT.forEach(pair => {
    const msg = $(pair[0]);
    msg.className = '';
    msg.textContent = '';
    if (pair[1]) {
      $(pair[1]).classList.add('hide');
      $(pair[1]).textContent = '';
    }
  });
  $('arcGate').className = 'notice';
  $('arcGate').textContent = '';
  if ($('envAlert')) {
    $('envAlert').classList.add('hide');
    $('envAlert').innerHTML = '';
  }
  if ($('envPlan')) {
    $('envPlan').classList.add('hide');
    $('envPlan').innerHTML = '';
  }
  if ($('arcViewCard')) $('arcViewCard').classList.add('hide');
  $('skillViewCard').classList.add('hide');
  $('skillView').textContent = '';
  $('pptOpen').classList.add('hide');
  $('cmdCard').classList.add('hide');
  $('cmdList').innerHTML = '';
  $('diagRows').innerHTML = '<tr><td colspan="3">还没有诊断过。</td></tr>';
  $('diagToArcWrap').classList.add('hide');
  $('skillEditCard').classList.add('hide');
  $('skillEditList').innerHTML = '';
  $('evalShowCard').classList.add('hide');
  $('evalShowA').textContent = '';
  $('evalRows').innerHTML = '<tr><td colspan="6">还没有条目。上面出第一题就有了。</td></tr>';
  $('fbRows').innerHTML = '<tr><td colspan="7">还没有反馈。</td></tr>';
  $('fbDiagOut').textContent = '';
}

function lecReset() {
  lecAuto(false);
  $('lecShot').classList.add('hide');      
  $('lecShot').removeAttribute('src');
  $('lecAudio').pause();               
  $('lecAudio').removeAttribute('src');
  $('lecVoiceBox').classList.add('hide');
  LEC.items = [];
  LEC.index = 0;
  LEC.skill = '';
  $('lecPlayer').classList.add('hide');
  $('lecSetup').classList.remove('hide');
  
  $('lecSource').value = '生成';
  lecSwapSource();
  $('askBox').classList.add('hide');
  $('askOut').classList.add('hide');
  $('askText').value = '';
  $('lecOutMsg').className = '';
  $('lecOutMsg').textContent = '';
  $('askMsg').className = '';
  $('askMsg').textContent = '';
}

const VIEWS = ['首页', '创造模式', '学生问答', '学生注册', '电脑服务', '环境配置', '教师蒸馏', '本地知识库', '学生档案馆', '课件生成', '错因诊断', '讲解评定', '反馈与优化', '联动教学', '设置'];

async function show(name) {
  VIEWS.forEach(v => $('view-' + v).classList.toggle('hide', v !== name));
  clearResults();
  if (name !== '联动教学') lecReset();
  if (name === '教师蒸馏') await fillOptions('蒸馏', '文件', 'fileSelect', '（材料/ 目录暂无材料）');
  if (name === '本地知识库') { loadMaterials(); loadSkills(); loadDecks(); }
  if (name === '学生档案馆') loadArchive();
  if (name === '学生问答') loadQaStu();
  if (name === '学生注册') loadReg();
  if (name === '课件生成') await fillOptions('课件生成', '技能包', 'pptSkill', '（还没有技能包，先去「教师蒸馏」生成）');
  if (name === '错因诊断') await fillOptions('错因诊断', '技能包', 'diagSkill', '（还没有技能包，先去「教师蒸馏」生成）');
  if (name === '讲解评定') {
    await fillOptions('讲解评定', '技能包', 'evalSkill', '（还没有技能包，先去「教师蒸馏」生成）');
    loadEvalLedger();
  }
  if (name === '反馈与优化') loadFeedback();
  if (name === '联动教学') {
    await fillOptions('联动教学', '技能包', 'lecSkill', '（还没有技能包，先去「教师蒸馏」生成）');
    lecSwapSource();                     
  }
  if (name === '创造模式') { chatRender(); 查授权状态(); 刷新记忆(); }
  if (name === '电脑服务') loadPcMenu();
  if (name === '环境配置') envScan();
  if (name === '设置') { loadSettings(); loadCacheUse(); }
  window.scrollTo(0, 0);
}

document.querySelectorAll('[data-go]').forEach(el => {
  el.onclick = ev => {
    if (el.tagName === 'A') ev.preventDefault();
    show(el.dataset.go);
  };
});



function matRow(m, i) {
  return '<tr><td>' + (i + 1) + '</td><td>' + esc(m['文件名']) + '</td><td>' + esc(m['格式']) + '</td>'
    + '<td title="' + esc(m['说明']) + '">' + esc(m['能不能读']) + '</td>'
    + '<td>' + esc(m['大小(字节)']) + '</td></tr>';
}

async function loadMaterials() {
  const tb = $('matRows');
  const rb = $('refRows');
  try {
    const d = await run('材料台账', {});
    $('matNotice').textContent = d.提示;
    tb.innerHTML = (d.条目 && d.条目.length)
      ? d.条目.map(matRow).join('')
      : '<tr><td colspan="5">暂无材料。把教案、课件、照片放进 材料/ 目录就行</td></tr>';
    $('refNotice').textContent = d.参考资料提示 || '公开的参考资料：可以当参照，不是蒸馏原料。';
    rb.innerHTML = (d.参考资料 && d.参考资料.length)
      ? d.参考资料.map(matRow).join('')
      : '<tr><td colspan="5">还没有参考资料。把公开的教案、教材、政策文件放进 参考资料/ 目录</td></tr>';
  } catch (e) {
    tb.innerHTML = '<tr><td colspan="5">读取失败：' + esc(e.message) + '</td></tr>';
    rb.innerHTML = '<tr><td colspan="5">读取失败：' + esc(e.message) + '</td></tr>';
  }
}

async function loadSkills() {
  const tb = $('skillRows');
  try {
    const d = await run('技能包管理', {});
    if (!d.条目 || !d.条目.length) {
      tb.innerHTML = '<tr><td colspan="4">暂无技能包。先去做一次蒸馏</td></tr>';
      return;
    }
    tb.innerHTML = d.条目.map((s, i) =>
      '<tr><td>' + (i + 1) + '</td>' +
      '<td><span class="tag">' + esc(s['技能包代号']) + '</span></td>' +
      '<td>' + (s['描述'] ? esc(brief(s['描述'], 40)) : '<span style="color:#999">（无描述）</span>') + '</td>' +
      '<td><button class="ghost" data-skill="' + esc(s['技能包代号']) + '">查看</button> ' +
      '<button class="ghost" data-skill-edit="' + esc(s['技能包代号']) + '">校订</button></td></tr>'
    ).join('');
  } catch (e) {
    tb.innerHTML = '<tr><td colspan="4">读取失败：' + esc(e.message) + '</td></tr>';
  }
}

async function loadDecks() {
  const tb = $('deckRows');
  try {
    const d = await run('课件台账', {});
    if (!d.条目 || !d.条目.length) {
      tb.innerHTML = '<tr><td colspan="5">还没有生成过课件。去「PPT 生成」或「联动教学」做一份（.pptx）</td></tr>';
      return;
    }
    tb.innerHTML = d.条目.map((k, i) =>
      '<tr><td>' + (i + 1) + '</td><td>' + esc(k['课件文件']) + '</td>' +
      '<td>' + esc(k['大小(字节)']) + '</td><td>' + esc(k['生成时间']) + '</td>' +
      '<td><a href="/课件/' + esc(encodeURIComponent(k['课件文件'])) + '">下载</a></td></tr>'
    ).join('');
  } catch (e) {
    tb.innerHTML = '<tr><td colspan="5">读取失败：' + esc(e.message) + '</td></tr>';
  }
}


$('btn接入查').onclick = 接入查;
$('接入清单').addEventListener('click', e => {
  const b = e.target.closest('button[data-接入]');
  if (!b || b.disabled) return;
  接入做(b.dataset.接入, b.dataset.动);
});

$('skillRows').addEventListener('click', e => {
  const 看 = e.target.closest('button[data-skill]');
  if (看) { viewSkill(看.dataset.skill); return; }
  const 改 = e.target.closest('button[data-skill-edit]');
  if (改) editSkill(改.dataset.skillEdit);
});

async function viewSkill(name) {
  try {
    const d = await run('查看技能包', { 技能包: name });
    $('skillView').textContent = d.正文;
    $('skillViewCard').classList.remove('hide');
  } catch (e) {
    say($('skillMsg'), '读取失败：' + e.message, 'err');
  }
}



let DIAG = { 学科: '', 题目: '', 作答: '', 错误类型: '' };

async function runDiag() {
  const tb = $('diagRows');
  try {
    const d = await run('错因诊断', {
      技能包: $('diagSkill').value,
      学科: $('diagSubject').value,
      题目: $('diagTopic').value,
      作答: $('diagAnswer').value
    });
    
    
    const 有问题 = (d.条目 || []).some(一 => 一['备注']);
    say($('diagMsg'), d.提示 || '诊断完成。', 有问题 ? 'err' : 'ok');
    tb.innerHTML = (d.条目 || []).map(一 =>
      '<tr><td><b>' + esc(一['字段']) + '</b></td><td>' + esc(一['内容'] || '（空）') +
      '</td><td style="color:#999">' + esc(一['备注'] || '') + '</td></tr>').join('')
      || '<tr><td colspan="3">模型没按格式给出三项，看提示里的告警。</td></tr>';
    DIAG = {
      学科: $('diagSubject').value,
      题目: $('diagTopic').value,
      作答: $('diagAnswer').value,
      错误类型: d['错误类型'] || ''
    };
    $('diagToArcWrap').classList.toggle('hide', !DIAG.错误类型);
  } catch (e) {
    say($('diagMsg'), '诊断失败：' + e.message, 'err');
    tb.innerHTML = '';
    $('diagToArcWrap').classList.add('hide');
  }
}


function 带去档案() {
  $('arcSubject').value = DIAG.学科;
  $('arcQuestion').value = DIAG.题目;
  $('arcAnswer').value = DIAG.作答;
  show('学生档案馆');
  if (!DIAG.错误类型) return;
  
  
  const 下拉 = $('arcError');
  下拉.value = DIAG.错误类型;
  if (下拉.value !== DIAG.错误类型) {
    say($('arcMsg'), '注意：下拉里没有「' + DIAG.错误类型 + '」这一项，请手动选一个再录入。', 'err');
  } else {
    say($('arcMsg'), '已把这条带到录入表，错误类型也填好了。核对后点「录入」。', 'ok');
  }
}

$('btnDiag').onclick = runDiag;
$('btnDiagToArc').onclick = 带去档案;
$('btnRefreshDiag').onclick = () =>
  fillOptions('错因诊断', '技能包', 'diagSkill', '（还没有技能包，先去「教师蒸馏」生成）');



async function doEvalGen() {
  const btn = $('btnEvalGen');
  btn.disabled = true;
  say($('evalMsg'), '正在按这位老师的讲法写讲解，可能要十几秒…');
  $('evalShowCard').classList.add('hide');
  try {
    const d = await run('讲解评定', {
      技能包: $('evalSkill').value,
      题目: $('evalTopic').value
    });
    $('evalNo').value = (d.条目号 == null ? '' : d.条目号);
    $('evalShowA').textContent = d.正文 || '';
    $('evalShowCard').classList.remove('hide');
    say($('evalMsg'), d.提示 || '已生成。', 'ok');
    loadEvalLedger();
  } catch (e) {
    say($('evalMsg'), '出题失败：' + e.message, 'err');
  } finally {
    btn.disabled = false;
  }
}

async function doEvalSave() {
  const 号 = $('evalNo').value.trim();
  if (!号) { say($('evalSaveMsg'), '先在上面出一题，或者手填一个条目号。', 'err'); return; }
  const btn = $('btnEvalSave');
  btn.disabled = true;
  say($('evalSaveMsg'), '正在存…');
  try {
    const d = await run('记讲解评定', {
      条目号: 号,
      判定: $('evalVerdict').value,
      改后讲解: $('evalFixed').value,
      老师原话: $('evalWords').value
    });
    say($('evalSaveMsg'), d.提示 || '已存下。', 'ok');
    
    $('evalFixed').value = '';
    $('evalWords').value = '';
    loadEvalLedger();
  } catch (e) {
    say($('evalSaveMsg'), '存不下：' + e.message, 'err');
  } finally {
    btn.disabled = false;
  }
}

async function loadEvalLedger() {
  const tb = $('evalRows');
  try {
    const d = await run('评定台账', { 只看: $('evalOnly').value || '全部' });
    if (!d.条目 || !d.条目.length) {
      tb.innerHTML = '<tr><td colspan="6">' + esc(d.提示 || '还没有条目。') + '</td></tr>';
      return;
    }
    tb.innerHTML = d.条目.map(r =>
      '<tr><td>' + esc(r['条目号']) + '</td><td>' + esc(r['状态']) + '</td>' +
      '<td>' + esc(r['判定'] || '—') + '</td><td>' + esc(brief(r['题目'], 30)) + '</td>' +
      '<td>' + (r['讲解B'] ? '改过' : '没改') + '</td>' +
      '<td>' + esc(brief(r['老师原话'], 30)) + '</td></tr>'
    ).join('');
  } catch (e) {
    tb.innerHTML = '<tr><td colspan="6">读取失败：' + esc(e.message) + '</td></tr>';
  }
}

$('btnEvalGen').onclick = doEvalGen;
$('btnEvalSave').onclick = doEvalSave;
$('btnEvalLedger').onclick = loadEvalLedger;
$('btnRefreshEval').onclick = () =>
  fillOptions('讲解评定', '技能包', 'evalSkill', '（还没有技能包，先去「教师蒸馏」生成）');
$('evalOnly').onchange = loadEvalLedger;



let 在改的包 = '';

async function editSkill(代号) {
  在改的包 = 代号;
  const 盒 = $('skillEditList');
  $('skillEditCard').classList.remove('hide');
  盒.innerHTML = '<div class="notice">正在读技能包…</div>';
  say($('skillEditMsg'), '');
  try {
    const d = await run('技能包校订', { 技能包: 代号 });
    say($('skillEditMsg'), d.提示 || '', '');
    盒.innerHTML = (d.条目 || []).map(一 =>
      '<div style="margin-top:18px">' +
      '<label>第 ' + esc(一['节号']) + ' 段 · ' + esc(一['标题']) + '</label>' +
      '<textarea rows="4" data-sec="' + esc(一['标题']) + '">' + esc(一['原文']) + '</textarea>' +
      '<input type="text" data-words="' + esc(一['标题']) +
      '" placeholder="老师为什么这么改（原话，不要润色）">' +
      '<div style="margin-top:8px"><button class="ghost" data-secsave="' +
      esc(一['标题']) + '">存回这一段</button></div></div>').join('');
  } catch (e) {
    盒.innerHTML = '';
    say($('skillEditMsg'), '读不出来：' + e.message, 'err');
  }
}

async function saveSection(节标题) {
  const 盒 = $('skillEditList');
  const 选择 = 盒.querySelector('textarea[data-sec="' + CSS.escape(节标题) + '"]');
  const 原话 = 盒.querySelector('input[data-words="' + CSS.escape(节标题) + '"]');
  if (!选择) return;
  
  if (!选择.value.trim()) {
    say($('skillEditMsg'), '「' + 节标题 + '」这段不能存空的。', 'err');
    return;
  }
  
  if (!confirm('确认把「' + 节标题 + '」这段改写回技能包？\n（改前那一版会自动备份到 _历史\\）')) return;
  say($('skillEditMsg'), '正在存…');
  try {
    const d = await run('存技能包节', {
      技能包: 在改的包, 节标题: 节标题,
      新内容: 选择.value, 老师原话: 原话 ? 原话.value : ''
    });
    say($('skillEditMsg'), d.提示 || '已存回。', 'ok');
  } catch (e) {
    say($('skillEditMsg'), '存不进去：' + e.message, 'err');
  }
}

$('skillEditList').addEventListener('click', e => {
  const 改 = e.target.closest('button[data-secsave]');
  if (改) saveSection(改.dataset.secsave);
});



async function sendFeedback() {
  const btn = $('btnFbSend');
  btn.disabled = true;
  say($('fbMsg'), '正在存…');
  try {
    const d = await run('记反馈', {
      类型: $('fbKind').value, 内容: $('fbText').value, 影响面: $('fbScope').value
    });
    say($('fbMsg'), d.提示 || '已存下。', 'ok');
    $('fbText').value = '';
    $('fbScope').value = '';
    loadFeedback();
  } catch (e) {
    say($('fbMsg'), '存不下：' + e.message, 'err');
  } finally {
    btn.disabled = false;
  }
}

async function loadFeedback() {
  const tb = $('fbRows');
  try {
    const d = await run('反馈清单', {
      只看: $('fbOnly').value || '全部', 类型: $('fbFilterKind').value || '全部'
    });
    if (!d.条目 || !d.条目.length) {
      tb.innerHTML = '<tr><td colspan="7">' + esc(d.提示 || '还没有反馈。') + '</td></tr>';
      return;
    }
    tb.innerHTML = d.条目.map(r =>
      '<tr><td>' + esc(r['反馈编号']) + '</td><td>' + esc(r['状态']) + '</td>' +
      '<td>' + esc(r['类型']) + '</td><td>' + esc(brief(r['内容'], 40)) + '</td>' +
      '<td>' + esc(r['结果'] || '—') + '</td><td>' + esc(r['提交号'] || '—') + '</td>' +
      '<td>' + (r['处理用时小时'] == null ? '—' : esc(r['处理用时小时']) + ' 小时') +
      '</td></tr>'
    ).join('');
  } catch (e) {
    tb.innerHTML = '<tr><td colspan="7">读取失败：' + esc(e.message) + '</td></tr>';
  }
}

async function markFeedback() {
  const 号 = $('fbHandleNo').value.trim();
  if (!号) { say($('fbMarkMsg'), '先填一下要处理哪一条（清单里的号）。', 'err'); return; }
  const btn = $('btnFbMark');
  btn.disabled = true;
  say($('fbMarkMsg'), '正在记…');
  try {
    const d = await run('记反馈处理', {
      反馈编号: 号, 结果: $('fbResult').value,
      提交号: $('fbCommit').value, 说明: $('fbNote').value
    });
    say($('fbMarkMsg'), d.提示 || '已记下。', 'ok');
    $('fbNote').value = '';
    loadFeedback();
  } catch (e) {
    say($('fbMarkMsg'), '记不下：' + e.message, 'err');
  } finally {
    btn.disabled = false;
  }
}

async function diagnoseFeedback() {
  const 号 = $('fbDiagNo').value.trim();
  if (!号) { say($('fbDiagMsg'), '先填一下诊断哪一条。', 'err'); return; }
  const btn = $('btnFbDiag');
  btn.disabled = true;
  $('fbDiagOut').classList.add('hide');
  say($('fbDiagMsg'), '正在读代码、让模型出草稿，可能要二三十秒…');
  try {
    const d = await run('反馈诊断', { 反馈编号: 号, 相关文件: $('fbDiagFiles').value });
    say($('fbDiagMsg'), d.提示 || '', 'ok');
    $('fbDiagOut').textContent = d.正文 || '';
    $('fbDiagOut').classList.remove('hide');
  } catch (e) {
    say($('fbDiagMsg'), '出不了草稿：' + e.message, 'err');
  } finally {
    btn.disabled = false;
  }
}

$('btnFbSend').onclick = sendFeedback;
$('btnFbMark').onclick = markFeedback;
$('btnFbDiag').onclick = diagnoseFeedback;
$('btnFbRefresh').onclick = loadFeedback;
$('fbOnly').onchange = loadFeedback;
$('fbFilterKind').onchange = loadFeedback;



async function loadArchive() {
  const tb = $('arcRows');
  $('arcViewCard').classList.add('hide');
  try {
    const d = await run('学生档案馆', {});
    if (d.正文) {
      $('arcGate').className = 'notice err';
      $('arcGate').textContent = d.正文;
    }
    if (!d.条目 || !d.条目.length) {
      tb.innerHTML = '<tr><td colspan="6">' + esc(d.提示 || '暂无学生') + '</td></tr>';
      return;
    }
    tb.innerHTML = d.条目.map((r, i) =>
      '<tr><td>' + (i + 1) + '</td><td>' + esc(r['编号']) + '</td><td>' + esc(r['姓名']) +
      '</td><td>' + esc(r['记录条数']) + '</td><td>' + esc(r['最近一条']) + '</td>' +
      '<td><button class="ghost" data-stu="' + esc(r['编号']) + '">查看</button></td></tr>'
    ).join('');
  } catch (e) {
    tb.innerHTML = '<tr><td colspan="6">读取失败：' + esc(e.message) + '</td></tr>';
  }
}


$('arcRows').addEventListener('click', e => {
  const btn = e.target.closest('button[data-stu]');
  if (btn) viewStudent(btn.dataset.stu);
});

async function viewStudent(编号) {
  try {
    const d = await run('查看学生档案', { 编号: 编号 });
    $('arcViewTitle').textContent = '学生档案 · ' + 编号 + '（' + (d.提示 || '') + '）';
    $('arcViewInfo').textContent = d.正文 || '';
    $('arcViewRows').innerHTML = (d.条目 && d.条目.length)
      ? d.条目.map(r => '<tr><td>' + esc(r['类型']) + '</td><td>' + esc(r['内容']) +
          '</td><td>' + esc(r['补充']) + '</td><td>' + esc(r['时间']) + '</td></tr>').join('')
      : '<tr><td colspan="4">这个学生还没有记录。</td></tr>';
    $('arcViewCard').classList.remove('hide');
  } catch (e) {
    say($('arcMsg'), '读取失败：' + e.message, 'err');
  }
}

async function doArchiveAdd() {
  const btn = $('btnArcAdd');
  const msg = $('arcMsg');
  btn.disabled = true;
  say(msg, '正在录入…');
  try {
    const d = await run('录入学生记录', {
      编号: $('arcSid').value.trim(),
      学科: $('arcSubject').value.trim(),
      题目: $('arcQuestion').value.trim(),
      作答: $('arcAnswer').value.trim(),
      对错: $('arcCorrect').value,
      错误类型: $('arcError').value
    });
    say(msg, d.提示 || '已录入', 'ok');
    $('arcQuestion').value = '';
    $('arcAnswer').value = '';
    loadArchive();
  } catch (e) {
    say(msg, '失败：' + e.message, 'err');
  } finally {
    btn.disabled = false;
  }
}



async function doPpt() {
  const btn = $('btnPpt');
  const msg = $('pptMsg');
  const out = $('pptOut');
  const topic = $('pptTopic').value.trim();

  if (!$('pptSkill').value) { say(msg, '请先选一位教师的技能包', 'err'); return; }
  if (!topic) { say(msg, '请填课题', 'err'); return; }

  btn.disabled = true;
  say(msg, '正在生成课件，可能要十几秒到一分钟…');
  out.classList.add('hide');
  $('pptOpen').classList.add('hide');
  try {
    const d = await run('课件生成', {
      技能包: $('pptSkill').value,
      课题: topic,
      页数: $('pptSlides').value.trim() || '8'
    });
    say(msg, d.提示 || '已生成', 'ok');
    if (d.课件文件) {
      $('pptLink').href = '/课件/' + encodeURIComponent(d.课件文件);
      $('pptOpen').classList.remove('hide');
    }
    out.textContent = d.正文 || '';
    out.classList.remove('hide');
  } catch (e) {
    say(msg, '失败：' + e.message, 'err');
  } finally {
    btn.disabled = false;
  }
}



function lecRender() {
  const it = LEC.items[LEC.index];
  if (!it) return;
  $('lecNo').textContent = '第 ' + (LEC.index + 1) + ' 页 / 共 ' + LEC.items.length + ' 页';
  $('lecSlideTitle').textContent = it['标题'] || '';
  const points = String(it['要点'] || '').split('\n').filter(x => x.trim());
  $('lecPoints').innerHTML = points.map(p => '<li>' + esc(p) + '</li>').join('');
  $('lecScript').textContent = it['讲稿'] || '';
  lecRenderShot(it);
  lecRenderVoice(it);
}


function lecRenderShot(it) {
  const 图地址 = String(it['页图'] || '');
  const 图 = $('lecShot');
  if (!图地址) {
    图.classList.add('hide');
    图.removeAttribute('src');
    return;
  }
  const url = '/课件图/' + 图地址.replace(/^\/课件图\//, '').split('/').map(encodeURIComponent).join('/');
  图.classList.remove('hide');
  if (图.getAttribute('src') !== url) {
    图.src = url;
  }
}


function lecRenderVoice(it) {
  const 音频 = String(it['音频'] || '');
  const 盒 = $('lecVoiceBox');
  const 播放器 = $('lecAudio');
  if (!音频) {
    盒.classList.add('hide');
    播放器.pause();
    播放器.removeAttribute('src');
    return;
  }
  const url = '/配音/' + 音频.replace(/^\/配音\//, '').split('/').map(encodeURIComponent).join('/');
  盒.classList.remove('hide');
  if (播放器.getAttribute('src') !== url) {
    播放器.src = url;                     
  }
  if ($('lecAudioAuto').checked) {
    
    const 试 = 播放器.play();
    if (试 && 试.catch) 试.catch(() => {});
  }
}


function lecNextPage() {
  if (LEC.index < LEC.items.length - 1) {
    LEC.index += 1;
    lecRender();
    lecSchedule();
  } else {
    lecAuto(false);
    $('lecAudio').pause();
    say($('lecOutMsg'), '这一课讲完了。', 'ok');
  }
}


function lecSchedule() {
  clearTimeout(LEC.timer);
  if (!LEC.auto || !LEC.items.length) return;
  const it = LEC.items[LEC.index];
  const script = String(it['讲稿'] || '');
  const 估毫秒 = Math.max(4, Math.round(script.length / 6)) * 1000;
  const 有音频 = !!(it['音频'] && $('lecAudio').getAttribute('src'));
  if (有音频) {
    
    
    LEC.timer = setTimeout(lecNextPage, 估毫秒 * 2 + 3000);
  } else {
    LEC.timer = setTimeout(lecNextPage, 估毫秒);
  }
}

function lecAuto(on) {
  LEC.auto = on;
  $('btnAuto').textContent = on ? '暂停自动播放' : '自动播放';
  lecSchedule();
}

function lecSwapSource() {
  
  const 已有 = $('lecSource').value === '已有';
  $('lecDeckBox').classList.toggle('hide', !已有);
  $('lecTopicBox').classList.toggle('hide', 已有);
  $('lecSlidesBox').classList.toggle('hide', 已有);
  if (已有) lecFillDecks();
}

async function lecFillDecks() {
  const sel = $('lecDeck');
  sel.innerHTML = '';
  try {
    await fillSelect(sel, await paramOptions('用已有课件', '课件文件'),
      '（课件输出/ 里还没有 .pptx。先把你那份复制进去，再点刷新列表）');
  } catch (e) {
    sel.innerHTML = '<option value="">（读不到课件列表）</option>';
  }
}

async function doLectureStart() {
  const btn = $('btnLecStart');
  const msg = $('lecMsg');
  const 已有 = $('lecSource').value === '已有';
  const topic = $('lecTopic').value.trim();

  if (!$('lecSkill').value) { say(msg, '请先选一位教师的技能包', 'err'); return; }
  if (已有 && !$('lecDeck').value) {
    say(msg, '请先选一份课件（把你那份 pptx 复制进 课件输出/，再点「刷新列表」）', 'err');
    return;
  }
  if (!已有 && !topic) { say(msg, '请填课题', 'err'); return; }

  btn.disabled = true;
  const 要配 = $('lecWantVoice').checked;
  say(msg, 已有
    ? (要配 ? '正在给这份课件补讲稿、导出每页图并配音：热身后约半分钟；刚起服务时可能三分钟以上。请不要刷新页面…'
           : '正在给这份课件补讲稿并导出每页图，可能要十几秒到一分钟…')
    : (要配 ? '正在备课、导出每页图并配音：热身后约半分钟；服务刚起、要把 5 GB 模型加载进显存时可能三分钟以上。请不要刷新页面…'
           : '正在备课，可能要十几秒到一分钟…'));
  try {
    const d = 已有
      ? await run('用已有课件', { 课件文件: $('lecDeck').value, 技能包: $('lecSkill').value,
                         要不要配音: 要配 ? '要' : '不' })
      : await run('联动教学', { 技能包: $('lecSkill').value, 课题: topic,
                         页数: $('lecSlides').value.trim() || '6',
                         要不要配音: 要配 ? '要' : '不' });
    if (!d.条目 || !d.条目.length) throw new Error(已有 ? '这份课件里没有可讲的页' : '没有生成任何页面');

    LEC.items = d.条目;
    LEC.index = 0;
    LEC.skill = $('lecSkill').value;
    $('lecTitle').textContent = '上课中 · ' + (d.课名 || topic || $('lecDeck').value);
    $('lecSetup').classList.add('hide');
    $('lecPlayer').classList.remove('hide');
    say($('lecOutMsg'), d.提示 || '开始上课', 'ok');
    lecRender();
    lecAuto(true);
  } catch (e) {
    say(msg, '失败：' + e.message, 'err');
  } finally {
    btn.disabled = false;
  }
}


function lecPause() {
  lecAuto(false);
  const 播放器 = $('lecAudio');
  LEC.audioWasPlaying = !播放器.paused && !!播放器.getAttribute('src');
  播放器.pause();
  $('askBox').classList.remove('hide');
  $('askOut').classList.add('hide');
  $('askMsg').className = '';
  $('askMsg').textContent = '';
  $('askText').value = '';
  $('askText').focus();
}

async function doAskSend() {
  const btn = $('btnAskSend');
  const msg = $('askMsg');
  const out = $('askOut');
  const question = $('askText').value.trim();
  if (!question) { say(msg, '请先写下问题', 'err'); return; }

  btn.disabled = true;
  say(msg, '正在按这位老师的方式作答…');
  out.classList.add('hide');
  try {
    const d = await run('答疑', { 技能包: LEC.skill, 问题: question });
    say(msg, d.提示 || '回答完成', 'ok');
    out.textContent = d.正文 || '';
    out.classList.remove('hide');
  } catch (e) {
    say(msg, '失败：' + e.message, 'err');
  } finally {
    btn.disabled = false;
  }
}

function doResume() {
  $('askBox').classList.add('hide');
  say($('lecOutMsg'), '继续上课。', 'ok');
  
  
  const 播放器 = $('lecAudio');
  if (LEC.audioWasPlaying && $('lecAudioAuto').checked && 播放器.getAttribute('src')) {
    const 试 = 播放器.play();
    if (试 && 试.catch) 试.catch(() => {});
  }
  LEC.audioWasPlaying = false;
  lecAuto(true);
}



async function loadCacheUse() {
  const tb = $('cacheRows');
  try {
    const d = await run('用量统计', {});
    say($('cacheMsg'), d.提示 || '', '');
    tb.innerHTML = (d.条目 && d.条目.length)
      ? d.条目.map(r => '<tr><td>' + esc(r['来源']) + '</td><td>' + esc(r['计入的调用次数']) +
          '</td><td>' + esc(r['命中token']) + '</td><td>' + esc(r['未命中token']) +
          '</td><td>' + esc(r['推理token']) + '</td><td>' + esc(r['命中率']) +
          '</td></tr>').join('')
      : '<tr><td colspan="6">' + esc(d.正文 || '还没有记录') + '</td></tr>';
  } catch (e) {
    say($('cacheMsg'), '读取失败：' + e.message, 'err');
    tb.innerHTML = '<tr><td colspan="6">读取失败</td></tr>';
  }
}

async function loadSettings() {
  const tb = $('setRows');
  try {
    const d = await run('模型配置', {});
    SETTINGS.items = d.条目 || [];
    if (!SETTINGS.items.length) {
      tb.innerHTML = '<tr><td colspan="5">没有读到任何服务商配置</td></tr>';
      return;
    }
    tb.innerHTML = SETTINGS.items.map(s =>
      '<tr><td>' + esc(s['代号']) + '</td><td>' + esc(s['当前']) + '</td><td>' + esc(s['模型']) +
      '</td><td>' + esc(s['接口地址']) + '</td><td>' + esc(s['密钥']) + '</td></tr>'
    ).join('');
    say($('setMsg'), d.提示 || '', '');
    
    
    
    const 当前服务商 = (SETTINGS.items.find(s => String(s['当前'] || '').trim() === '是') || {})['代号'] || '';
    fillSelect($('setProvider'), SETTINGS.items.map(s => s['代号']), '（没有服务商）', 当前服务商);
    fillSettingsForm();
  } catch (e) {
    tb.innerHTML = '<tr><td colspan="5">读取失败：' + esc(e.message) + '</td></tr>';
  }
}

function fillSettingsForm() {
  const name = $('setProvider').value;
  const item = SETTINGS.items.find(s => s['代号'] === name);
  if (!item) return;
  $('setModel').value = item['模型'] || '';
  $('setBase').value = item['接口地址'] || '';
  $('setKeyEnv').value = '';
  $('setKey').value = '';
}

async function doSaveSettings() {
  const btn = $('btnSaveSettings');
  const msg = $('setMsg');
  btn.disabled = true;
  say(msg, '正在保存…');
  try {
    const d = await run('保存模型配置', {
      服务商: $('setProvider').value,
      模型: $('setModel').value.trim(),
      接口地址: $('setBase').value.trim(),
      密钥变量名: $('setKeyEnv').value.trim(),
      密钥: $('setKey').value.trim(),
      设为当前: $('setDefault').value
    });
    say(msg, d.提示 || '已保存', 'ok');
    $('setKey').value = '';
    loadSettings();
  } catch (e) {
    say(msg, '失败：' + e.message, 'err');
  } finally {
    btn.disabled = false;
  }
}



async function doDistill() {
  const btn = $('btnDistill');
  const msg = $('distillMsg');
  const out = $('distillOut');
  const file = $('fileSelect').value;
  const name = $('skillName').value.trim();
  const desc = $('skillDesc').value.trim();

  if (!file) { say(msg, '请先选一份材料', 'err'); return; }
  if (!name) { say(msg, '请填技能包代号', 'err'); return; }
  if (!desc) { say(msg, '请填描述（它决定这个技能包什么时候被用上）', 'err'); return; }

  btn.disabled = true;
  say(msg, '正在调用大模型，可能要十几秒到一分钟…');
  out.classList.add('hide');
  try {
    const d = await run('蒸馏', { 文件: file, 代号: name, 描述: desc });
    say(msg, d.提示 || '完成', 'ok');
    loadSkills();
    out.textContent = d.正文 || '';
    out.classList.remove('hide');
  } catch (e) {
    say(msg, '失败：' + e.message, 'err');
  } finally {
    btn.disabled = false;
  }
}



function 读对话缓存() {
  try {
    const 原 = JSON.parse(localStorage.getItem('shao_xin_chat') || '[]');
    if (!Array.isArray(原)) return [];
    return 原.filter(m => m && (m.role === 'user' || m.role === 'assistant')
      && typeof m.content === 'string').slice(-40);
  } catch (e) { return []; }
}

function 存对话缓存() {
  try { localStorage.setItem('shao_xin_chat', JSON.stringify(CHAT.history.slice(-40))); }
  catch (e) {  }
}

const CHAT = { history: 读对话缓存() };


function chatRender() {
  if (!CHAT.history.length) {
    $('chatLog').innerHTML = '<div class="msg ai">你好，我是「邵新」的助手。想做什么直接说，' +
      '比如「用 teacher-a 的风格出一节分数的除法的课件」。</div>';
    return;
  }
  $('chatLog').innerHTML = CHAT.history.map(m =>
    '<div class="msg ' + (m.role === 'user' ? 'me' : 'ai') + '">' + esc(m.content) + '</div>'
  ).join('');
  $('chatLog').scrollTop = $('chatLog').scrollHeight;
}

async function doChatSend() {
  const text = $('chatText').value.trim();
  const msg = $('chatMsg');
  const btn = $('btnChatSend');
  if (!text) { say(msg, '请先写下想做什么', 'err'); return; }

  CHAT.history.push({ role: 'user', content: text });
  存对话缓存();
  $('chatText').value = '';
  chatRender();

  btn.disabled = true;
  say(msg, 'AI 正在处理…');
  try {
    
    const history = CHAT.history.slice(0, -1)
      .map(m => (m.role === 'user' ? '老师：' : '助手：') + m.content).join('\n');
    const d = await run('创造模式', { 内容: text, 之前的对话: history });
    CHAT.history.push({ role: 'assistant', content: d.正文 || '（没有返回内容）' });
    存对话缓存();
    say(msg, d.提示 || '', 'ok');
    chatRender();
    cmdShow(d.待确认命令);
    画授权状态(d['授权']);
  } catch (e) {
    
    say(msg, '失败：' + e.message + '（这句没进对话记录）', 'err');
  } finally {
    btn.disabled = false;
  }
}

function doChatClear() {
  CHAT.history = [];
  try { localStorage.removeItem('shao_xin_chat'); } catch (e) {}
  chatRender();
  say($('chatMsg'), '对话已清空。');
}



function 画授权状态(a) {
  const el = $('authState');
  if (a === undefined) {
    
    
    el.textContent = '状态未刷新（窗口可能还开着）。点下面任一按钮、或发一轮对话就会显示最新。';
    return;
  }
  if (!a || !a['档位']) {
    
    el.textContent = '现在没有授权窗口' + (a && a['结束原因'] ? '（' + a['结束原因'] + '）' : '') + '。';
    $('authButtons').classList.remove('hide');
    return;
  }
  if (a['说明'] === '默认档位（测试期）') {
    
    
    el.innerHTML = '测试期：默认 <b>' + esc(a['档位']) + '</b>，AI 提的命令<b>不再逐条问你</b>。'
      + '每条命令照旧进审计。';
    $('authButtons').classList.add('hide');
    return;
  }
  $('authButtons').classList.remove('hide');
  const 时间话 = a['不限时']
    ? '不限时（到你点「收回」为止）'
    : ('还剩约 ' + Math.max(1, Math.ceil(a['剩余秒'] / 60)) + ' 分钟');
  el.innerHTML = '现在开着 <b>' + esc(a['档位']) + '</b>：' + 时间话 + '、'
    + esc(a['剩余几条']) + ' 条。'
    + (a['档位'] === '全部授权'
      ? '　<b style="color:#c00">禁用清单已放行：格式化磁盘、删注册表那类也拦不住；每条命令都进了审计</b>'
      : '');
}

async function 查授权状态() {
  
  
  try {
    const d = await run('看授权状态', {});
    画授权状态(d['授权']);
  } catch (e) {
    画授权状态(undefined);
  }
}


function 说授权(文字, 坏) {
  const el = $('authMsg');
  el.textContent = 文字;
  el.style.color = 坏 ? '#c00' : '#2e7d32';
}

const 授权按钮们 = () => [$('btnAuthSafe'), $('btnAuthNormal'), $('btnAuthFull'), $('btnAuthOff')];

async function 开授权(档位) {
  const 分钟 = '不限';      
  授权按钮们().forEach(b => { b.disabled = true; });
  try {
    const d = await run('长任务授权', { 档位: 档位, 分钟: 分钟 });
    说授权(d.提示 || '', false);
    画授权状态(d['授权']);
  } catch (e) {
    说授权('开不了：' + e.message, true);
  } finally {
    
    授权按钮们().forEach(b => { b.disabled = false; });
  }
}

async function 收回授权() {
  授权按钮们().forEach(b => { b.disabled = true; });
  try {
    const d = await run('长任务授权', { 档位: '安全授权', 分钟: '0' });
    
    说授权(d.提示 || '', !(d['授权'] && d['授权']['档位']));
    画授权状态(d['授权']);
  } catch (e) {
    说授权('收回失败：' + e.message, true);
  } finally {
    授权按钮们().forEach(b => { b.disabled = false; });
  }
}

$('btnAuthSafe').onclick = () => 开授权('安全授权');
$('btnAuthNormal').onclick = () => 开授权('普通授权');
$('btnAuthFull').onclick = () => 开授权('全部授权');
$('btnAuthOff').onclick = 收回授权;



const PC = { pending: '' };

function pcTable(items) {
  if (!items || !items.length) return '';
  const cols = Object.keys(items[0]);
  return '<thead><tr>' + cols.map(c => '<th>' + esc(c) + '</th>').join('') + '</tr></thead>' +
    '<tbody>' + items.map(r =>
      '<tr>' + cols.map(c => '<td>' + esc(r[c]) + '</td>').join('') + '</tr>').join('') + '</tbody>';
}

function pcShow(d) {
  $('pcOut').textContent = d.正文 || '';
  $('pcOut').classList.toggle('hide', !d.正文);
  const html = pcTable(d.条目);
  $('pcTable').innerHTML = html;
  $('pcTable').classList.toggle('hide', !html);
  PC.pending = d.需要确认 ? (d.动作 || '') : '';
  $('btnPcRun').classList.toggle('hide', !d.需要确认);
}

async function loadPcMenu() {
  try {
    const d = await run('电脑服务', { 一句话: '' });
    $('pcMenu').innerHTML = (d.条目 || []).map(a =>
      '<button class="ghost" data-pc="' + esc(a['代号']) + '">' + esc(a['名称']) + '</button>'
    ).join(' ');
  } catch (e) {
    say($('pcMsg'), '读取动作清单失败：' + e.message, 'err');
  }
}

async function pcPreview(action) {
  try {
    const d = await run('执行电脑动作', { 动作代号: action, 确认: '否' });
    say($('pcMsg'), d.提示 || '', 'ok');
    pcShow(d);
  } catch (e) {
    say($('pcMsg'), '失败：' + e.message, 'err');
  }
}

async function pcAsk() {
  const sentence = $('pcText').value.trim();
  if (!sentence) { say($('pcMsg'), '请先用一句话说说想干什么', 'err'); return; }
  const btn = $('btnPcAsk');
  btn.disabled = true;
  say($('pcMsg'), '正在理解这句话…');
  try {
    const d = await run('电脑服务', { 一句话: sentence });
    if (d.动作) {
      await pcPreview(d.动作);
    } else {
      say($('pcMsg'), d.提示 || '', 'err');
      pcShow(d);
    }
  } catch (e) {
    say($('pcMsg'), '失败：' + e.message, 'err');
  } finally {
    btn.disabled = false;
  }
}

async function pcRun() {
  if (!PC.pending) return;
  const btn = $('btnPcRun');
  btn.disabled = true;
  say($('pcMsg'), '正在执行…');
  try {
    const d = await run('执行电脑动作', { 动作代号: PC.pending, 确认: '是' });
    say($('pcMsg'), d.提示 || '', 'ok');
    pcShow(d);
  } catch (e) {
    say($('pcMsg'), '失败：' + e.message, 'err');
  } finally {
    btn.disabled = false;
  }
}


$('pcMenu').addEventListener('click', e => {
  const btn = e.target.closest('button[data-pc]');
  if (btn) pcPreview(btn.dataset.pc);
});



const ENV = { pending: '' };


function kvTable(items) {
  const cols = Object.keys(items[0]);
  return '<thead><tr>' + cols.map(c => '<th>' + esc(c) + '</th>').join('') + '</tr></thead><tbody>' +
    items.map(r => '<tr>' + cols.map(c => '<td>' + esc(r[c]) + '</td>').join('') + '</tr>').join('') +
    '</tbody>';
}

function envShow(d) {
  const items = d.条目 || [];
  $('envOut').textContent = d.正文 || '';
  $('envOut').classList.toggle('hide', !d.正文);

  const isScan = items.length > 0 && items[0]['代号'] !== undefined;

  if (isScan) {
    const miss = items.filter(x => x['状态'] !== '已就绪');
    if (miss.length) {
      $('envAlert').innerHTML = '<b>有 ' + miss.length + ' 项还没配齐：' +
        miss.map(x => esc(x['环境'])).join('、') + '</b>\n' +
        miss.map(x => x['补充提示'] ? esc(x['环境']) + '：' + esc(x['补充提示']) : '').filter(Boolean).join('\n');
      $('envAlert').classList.remove('hide');
    } else {
      $('envAlert').classList.add('hide');
      $('envAlert').innerHTML = '';
    }
    envBadge(miss.length);

    const cols = Object.keys(items[0]).filter(c => c !== '补充提示');
    $('envTable').innerHTML =
      '<thead><tr>' + cols.map(c => '<th>' + esc(c) + '</th>').join('') +
      '<th style="width:90px">操作</th></tr></thead><tbody>' +
      items.map(r => '<tr>' + cols.map(c => '<td>' + esc(r[c]) + '</td>').join('') +
        '<td><button class="ghost" data-env="' + esc(r['代号']) + '">安装</button></td></tr>').join('') +
      '</tbody>';
    $('envTable').classList.remove('hide');
  }

  
  if (!isScan && items.length) {
    $('envPlan').innerHTML = kvTable(items);
    $('envPlan').classList.remove('hide');
  } else {
    $('envPlan').classList.add('hide');
    $('envPlan').innerHTML = '';
  }

  ENV.pending = d.需要确认 ? (d.环境项 || '') : '';
  $('btnEnvRun').classList.toggle('hide', !d.需要确认);
}

function envBadge(missingCount, 测不出) {
  const el = $('envState');
  if (!el) return;
  if (测不出) {
    
    
    el.className = 't-state wait';
    el.textContent = '没测出来';
    return;
  }
  if (missingCount) {
    el.className = 't-state wait';
    el.textContent = '有 ' + missingCount + ' 项未配齐';
  } else {
    el.className = 't-state ok';
    el.textContent = '全部就绪';
  }
}

async function envCheckQuiet() {
  try {
    const d = await run('环境配置', {});
    envBadge((d.条目 || []).filter(x => x['状态'] !== '已就绪').length);
  } catch (e) {
    envBadge(0, true);
  }
}


let 待接入 = null;

function 接入画(清单) {
  const 箱 = $('接入清单');
  if (!清单.length) { 箱.innerHTML = '<div>清单是空的（接入可选.json 没读到）。</div>'; return; }
  箱.innerHTML = 清单.map(一 => {
    const 能 = !!一.能装上, 已 = !!一.已装上;
    const 待 = (待接入 && 待接入.名字 === 一.名字) ? 待接入.动作 : null;
    const 动 = 待 || (已 ? '卸下' : '装上');
    const 标 = 待 ? ('确认' + 待) : (已 ? '卸下' : '装上');
    const 状态 = 已 ? '<b style="color:#14663a">已装上</b>'
                    : (能 ? '可以装' : '<b style="color:#a32020">接不了</b>');
    return '<div style="border:1px solid #e5e7eb;border-radius:8px;padding:10px;margin-bottom:8px">'
      + '<div><b>' + esc(一.名字) + '</b>　' + 状态
      + '　<span style="color:#6b7280">' + esc(一.形态 || '') + '</span></div>'
      + '<div style="color:#374151;margin-top:4px">' + esc(一.用处 || '') + '</div>'
      + '<div style="color:#6b7280;margin-top:4px">前置：' + esc(一.前置 || '（没写）') + '</div>'
      + (能 ? '' : '<div style="color:#a32020;margin-top:4px">' + esc(一.状态说明 || '') + '</div>')
      + '<div style="color:#6b7280;margin-top:4px">出处：' + esc(一.出处 || '（没核到）') + '</div>'
      + '<div style="margin-top:8px"><button ' + (能 ? '' : 'disabled ')
      + 'data-接入="' + esc(一.名字) + '" data-动="' + esc(动) + '">' + esc(标) + '</button></div>'
      + '</div>';
  }).join('');
}

async function 接入查() {
  say($('接入提示'), '正在读清单…');
  待接入 = null;
  try {
    const d = await run('可选接入', {});
    say($('接入提示'), d.提示 || '', 'ok');
    接入画(d.接入清单 || []);
  } catch (e) {
    say($('接入提示'), '读不到：' + e.message, 'err');
  }
}

async function 接入做(名字, 动作) {
  const 确认 = (待接入 && 待接入.名字 === 名字) ? '是' : '否';
  try {
    const d = await run('装接入', { 接入名: 名字, 动作: 动作, 确认: 确认 });
    if (d.需要确认) {
      待接入 = { 名字: 名字, 动作: 动作 };
      say($('接入提示'), (d.正文 || '') + '　——再点一次那个按钮就真做。', 'err');
    } else {
      待接入 = null;
      say($('接入提示'), d.提示 || '', 'ok');
    }
    const 再 = await run('可选接入', {});
    接入画(再.接入清单 || []);
  } catch (e) {
    待接入 = null;
    say($('接入提示'), '没做成：' + e.message, 'err');
  }
}

async function envScan() {
  say($('envMsg'), '正在检测…');
  try {
    const d = await run('环境配置', {});
    say($('envMsg'), d.提示 || '', 'ok');
    envShow(d);
  } catch (e) {
    say($('envMsg'), '检测失败：' + e.message, 'err');
  }
}

async function envPreview(tool) {
  if (!tool) {
    say($('envMsg'), '这一行没带环境代号，点「检测本机环境」重来一次。', 'err');
    return;
  }
  try {
    const d = await run('安装环境', { 环境代号: tool, 确认: '否' });
    say($('envMsg'), d.提示 || '', d.需要确认 ? 'err' : 'ok');
    envShow(d);
  } catch (e) {
    say($('envMsg'), '失败：' + e.message, 'err');
  }
}

async function envRun() {
  if (!ENV.pending) return;
  const btn = $('btnEnvRun');
  btn.disabled = true;
  say($('envMsg'), '正在安装，可能要几分钟，请不要关窗口…');
  try {
    const d = await run('安装环境', { 环境代号: ENV.pending, 确认: '是' });
    say($('envMsg'), d.提示 || '', (d.提示 || '').indexOf('成功') >= 0 ? 'ok' : 'err');
    envShow(d);
  } catch (e) {
    say($('envMsg'), '失败：' + e.message, 'err');
  } finally {
    btn.disabled = false;
  }
}

$('envTable').addEventListener('click', e => {
  const btn = e.target.closest('button[data-env]');
  if (btn) envPreview(btn.dataset.env);
});



const CMD = { pending: [] };

function cmdShow(list) {
  CMD.pending = list || [];
  $('cmdCard').classList.toggle('hide', !CMD.pending.length);
  $('cmdList').innerHTML = CMD.pending.map((c, i) =>
    '<div class="cmdbx"><code>' + esc(c.命令) + '</code>' +
    (c.为什么 ? '<p class="cmdwhy">' + esc(c.为什么) + '</p>' : '') +
    (c.风险 ? '<p class="cmdrisk">' + esc(c.风险) + '</p>' : '') +
    '<button class="danger" data-cmd="' + i + '">执行这条命令</button></div>'
  ).join('');
}

async function cmdRun(i) {
  const c = CMD.pending[i];
  if (!c) return;
  say($('cmdMsg'), '正在执行…');
  try {
    const d = await run('执行命令', { 命令: c.命令, 确认: '是', 编号: c.编号 || '' });
    say($('cmdMsg'), d.提示 || '', 'ok');
    $('cmdOut').textContent = d.正文 || '';
    $('cmdOut').classList.remove('hide');
  } catch (e) {
    say($('cmdMsg'), '失败：' + e.message, 'err');
  }
}

$('cmdList').addEventListener('click', e => {
  const btn = e.target.closest('button[data-cmd]');
  if (btn) cmdRun(Number(btn.dataset.cmd));
});

$('btnEnvScan').onclick = envScan;
$('btnEnvRun').onclick = envRun;
$('btnPcAsk').onclick = pcAsk;
$('btnPcRun').onclick = pcRun;
$('btnChatSend').onclick = doChatSend;
$('btnChatClear').onclick = doChatClear;
$('btnDistill').onclick = doDistill;
$('btnRefreshDistill').onclick = () => fillOptions('蒸馏', '文件', 'fileSelect', '（材料/ 目录暂无材料）');
$('btnRefreshSkills').onclick = loadSkills;
$('btnRefreshMats').onclick = loadMaterials;
$('btnRefreshDecks').onclick = loadDecks;


async function loadQaStu() {
  await fillOptions('学生问答', '技能包', 'qaStuSkill',
    '（还没有技能包，先去「教师蒸馏」生成）');
}

async function doQaStuAsk() {
  const btn = $('btnQaStuAsk');
  const msg = $('qaStuMsg');
  const out = $('qaStuOut');
  const 编号 = $('qaStuSid').value.trim();
  const 问题 = $('qaStuQuestion').value.trim();

  if (!编号) { say(msg, '请先填你的编号', 'err'); return; }
  if (!$('qaStuSkill').value) { say(msg, '请先选一位老师', 'err'); return; }
  if (!问题) { say(msg, '请先写问题', 'err'); return; }

  btn.disabled = true;
  say(msg, '正在请这位老师回答，请稍候…');
  out.classList.add('hide');
  try {
    const d = await run('学生问答', { 编号: 编号, 技能包: $('qaStuSkill').value, 问题: 问题 });
    say(msg, d.提示 || '已作答', 'ok');
    $('qaStuQuestion').value = '';
    out.textContent = d.正文 || '';
    out.classList.remove('hide');
  } catch (e) {
    say(msg, '失败：' + e.message, 'err');
  } finally {
    btn.disabled = false;
  }
}



async function loadReg() {
  const tb = $('regRows');
  try {
    const d = await run('学生名册', {});
    if (d.正文) {
      say($('regMsg'), d.正文, 'err');
    }
    if (!d.条目 || !d.条目.length) {
      tb.innerHTML = '<tr><td colspan="9">' + esc(d.提示 || '还没有学生') + '</td></tr>';
      return;
    }
    tb.innerHTML = d.条目.map((r, i) =>
      '<tr><td>' + (i + 1) + '</td><td>' + esc(r['编号']) + '</td><td>' + esc(r['姓名']) +
      '</td><td>' + esc(r['学号']) + '</td><td>' + esc(r['年级']) + '</td><td>' +
      esc(r['班级']) + '</td><td>' + esc(r['家长同意书']) + '</td><td>' +
      esc(r['记录条数']) + '</td><td>' + esc(r['最近一条']) + '</td></tr>').join('');
  } catch (e) {
    tb.innerHTML = '<tr><td colspan="9">读取失败：' + esc(e.message) + '</td></tr>';
  }
}

async function doRegAdd() {
  const btn = $('btnRegAdd');
  const msg = $('regMsg');
  const 编号 = $('regSid').value.trim();
  const 姓名 = $('regName').value.trim();
  if (!编号) { say(msg, '请先填学生编号', 'err'); return; }
  if (!姓名) { say(msg, '请填学生姓名', 'err'); return; }
  btn.disabled = true;
  say(msg, '正在注册…');
  try {
    const d = await run('学生注册', {
      编号: 编号,
      姓名: 姓名,
      学号: $('regNo').value.trim(),
      年级: $('regGrade').value.trim(),
      班级: $('regClass').value.trim(),
      备注: $('regNote').value.trim(),
      家长同意书: $('regConsent').value
    });
    say(msg, [d.提示, d.正文].filter(Boolean).join('　'), 'ok');
    ['regSid', 'regName', 'regNo', 'regGrade', 'regClass', 'regNote'].forEach(id => { $(id).value = ''; });
    loadReg();
  } catch (e) {
    say(msg, '失败：' + e.message, 'err');
  } finally {
    btn.disabled = false;
  }
}

$('btnRefreshArc').onclick = loadArchive;
$('btnQaStuAsk').onclick = doQaStuAsk;
$('btnRefreshQaStu').onclick = loadQaStu;
$('btnRegAdd').onclick = doRegAdd;
$('btnRefreshReg').onclick = loadReg;
$('btnArcAdd').onclick = doArchiveAdd;
$('btnPpt').onclick = doPpt;
$('btnRefreshPpt').onclick = () => fillOptions('课件生成', '技能包', 'pptSkill', '（还没有技能包）');
$('lecSource').onchange = lecSwapSource;
$('btnRefreshLec').onclick = () => {
  fillOptions('联动教学', '技能包', 'lecSkill', '（还没有技能包）');
  if ($('lecSource').value === '已有') lecFillDecks();
};
$('btnLecStart').onclick = doLectureStart;
$('btnPrev').onclick = () => { LEC.index = Math.max(0, LEC.index - 1); lecRender(); lecSchedule(); };
$('btnNext').onclick = () => { LEC.index = Math.min(LEC.items.length - 1, LEC.index + 1); lecRender(); lecSchedule(); };
$('btnAuto').onclick = () => lecAuto(!LEC.auto);
$('btnAskPause').onclick = lecPause;
$('btnAskSend').onclick = doAskSend;
$('btnResume').onclick = doResume;
$('btnLecStop').onclick = () => { lecReset(); say($('lecMsg'), '已结束上课。', 'ok'); };

$('lecAudio').addEventListener('ended', () => { if (LEC.auto) lecNextPage(); });
$('btnSaveSettings').onclick = doSaveSettings;
$('btnReloadSettings').onclick = loadSettings;
$('btnCacheRefresh').onclick = loadCacheUse;
$('setProvider').onchange = fillSettingsForm;

(async () => {
  try {
    const 表 = await api('/api/能力');
    ABILITIES = 表.条目;
    
    
    if (表.版本 && $('verNo')) $('verNo').textContent = 表.版本;
    fillSelect($('arcCorrect'), await paramOptions('录入学生记录', '对错'), '（没有选项）', '对');
    
    
    
    fillSelect($('arcError'), await paramOptions('录入学生记录', '错误类型'), '（没有选项）', '其他');
    fillSelect($('regConsent'), await paramOptions('学生注册', '家长同意书'), '（无）', '未签回');
    fillSelect($('evalVerdict'), await paramOptions('记讲解评定', '判定'), '（没有选项）', '可接受');
    fillSelect($('evalOnly'), await paramOptions('评定台账', '只看'), '（没有选项）', '全部');
    fillSelect($('fbKind'), await paramOptions('记反馈', '类型'), '（没有选项）', '不好用');

    
    $('btnNetGo').addEventListener('click', async () => {
      const 出 = $('netOut');
      出.textContent = '查着…';
      try {
        const d = await run('联网查证', {
          问题: $('netQuestion').value,
          网址: $('netUrl').value,
          条数: $('netCount').value,
        });
        出.textContent = (d.提示 || '') + '\n\n' + (d.正文 || '');
      } catch (e) {
        出.textContent = '没查成：' + (e.message || e);
      }
    });
    fillSelect($('fbOnly'), await paramOptions('反馈清单', '只看'), '（没有选项）', '全部');
    fillSelect($('fbFilterKind'), await paramOptions('反馈清单', '类型'), '（没有选项）', '全部');
    fillSelect($('fbResult'), await paramOptions('记反馈处理', '结果'), '（没有选项）', '已修');
  } catch (e) {
    say($('arcMsg'), '读取能力列表失败：' + e.message, 'err');
  }
  envCheckQuiet();
  show('首页');
})();



async function 刷新记忆() {
  try {
    const d = await run('记忆库', { 动作: '查看' });
    $('memCount').textContent = d['关键条数'] ?? 0;
    $('memSum').textContent = d['摘要条数'] ?? 0;
    const 条 = d['关键记忆'] || [];
    $('memList').textContent = 条.length
      ? 条.map((x, i) => (i + 1) + '. [' + (x['类别'] || '关键') + '] ' + x['内容']).join(String.fromCharCode(10))
      : '（还没有记住什么）';
  } catch (e) {
    $('memMsg').textContent = '读不到记忆：' + e.message;
  }
}

$('btnMemClear').onclick = async () => {
  const 确认 = prompt('清空后不可恢复。确实要清，请输入四个字：确认清空');
  if (确认 === null) return;
  try {
    await run('记忆库', { 动作: '清空', 确认 });
    $('memMsg').textContent = '已清空';
    刷新记忆();
  } catch (e) {
    $('memMsg').textContent = e.message;
  }
};
