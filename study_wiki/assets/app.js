(() => {
  'use strict';
  const data = window.STUDY_WIKI;
  const { filter, terms, unclassified, examKey, isPlaceholder } = window.WikiSearch;
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safe = value => { try { if (/^[a-z][a-z0-9+.-]*:/i.test(value) && !/^https?:/i.test(value)) return ''; const u = new URL(value, location.href); return ['http:', 'https:', 'file:'].includes(u.protocol) ? esc(value) : ''; } catch { return ''; } };
  const fields = ['user', 'structure', 'algorithm', 'language', 'classification', 'sort', 'exam', 'exam_year'];
  let state = {}, page = 1, previousQuery = '', selectedTab = 'read';
  const storageKey = 'study-wiki-user:' + location.pathname;
  const labels = { problem: '코딩 문제', note: '학습 노트', ai_note: 'AI 개념 노트' };
  if (!data) { $('cards').textContent = 'Wiki 데이터를 불러오지 못했습니다. 다시 생성한 뒤 열어주세요.'; return; }
  const all = data.records;
  function route(changes, replace = false) {
    const next = { ...state, ...changes };
    const params = new URLSearchParams(Object.entries(next).filter(([,v]) => v));
    const hash = '#' + params.toString();
    if (replace) { history.replaceState(null, '', hash); render(); }
    else if (location.hash !== hash) location.hash = hash;
    else render();
  }
  function recordLink(r) { const params = new URLSearchParams(state); params.set('record', r.id); return '#' + params.toString(); }
  function options(id, values, placeholder) {
    $(id).innerHTML = '<option value="">' + placeholder + '</option>' + [...new Set(values.filter(Boolean))].sort((a,b) => a.localeCompare(b,'ko')).map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
  }
  options('user', all.flatMap(r=>r.contributors || [r.user]), '모든 참여자');
  options('structure', all.flatMap(r=>r.data_structures), '전체 자료구조');
  options('algorithm', all.flatMap(r=>r.algorithms), '전체 알고리즘');
  options('language', all.map(r=>r.language), '전체 언어');
  options('exam', all.map(examKey), '전체 기출·일반 문제');
  options('exam_year', all.map(r=>(r.exam||{}).year), '전체 연도');
  function tagButtons(r) { return terms(r).map(t=>`<button class="tag" data-topic="${esc(t)}">${esc(t)}</button>`).join('') + (unclassified(r) ? '<span class="tag missing">미분류</span>' : ''); }
  function card(r) {
    return `<article class="card"><div class="card-meta"><span class="type ${r.kind}">${r.kind==='ai_note'?'AI / 자동 생성':r.kind==='note'?'NOTE / 직접 작성':esc((r.platform||'PROBLEM').toUpperCase()) + ' / ' + esc(r.problem_id)}</span><span>${esc(r.level || r.language || '학습 노트')}</span></div><h3><a href="${esc(recordLink(r))}">${esc(r.title)}</a></h3><p class="excerpt">${esc(r.summary || '설명이 아직 없습니다. 원본 기록에서 내용을 보완해 주세요.')}</p><div class="tags">${tagButtons(r)}${r.status==='draft'?'<span class="tag draft">작성 중</span>':''}${r.kind==='ai_note'?`<span class="tag draft">${r.stale?'원본 변경 · 재검토 필요':r.status==='reviewed'?'사람 검토 완료':'AI 생성 · 미검토'}</span>`:''}${(r.exam||{}).name?`<span class="tag">${esc(r.exam.name)} ${esc(r.exam.year||'')}</span>`:''}</div><div class="card-footer">${r.kind==='ai_note'?'<span>AI 자동 생성</span>':`<button data-user="${esc(r.user)}"><span class="avatar">${esc(r.user.slice(0,2).toUpperCase())}</span>${esc(r.user)}</button>`}<span>${esc(r.date)}</span></div></article>`;
  }
  function showLibrary() {
    const scope = all.filter(r=>!state.user || r.user===state.user || (r.contributors||[]).includes(state.user));
    const problems = scope.filter(r=>r.kind==='problem');
    const counts = [scope.length, new Set(problems.map(r=>r.platform+'/'+r.problem_id)).size, scope.filter(r=>r.kind==='note').length, new Set(scope.flatMap(terms)).size];
    $('stats').innerHTML = counts.map((n,i)=>`<div class="stat"><strong>${n}</strong><span>${['풀이·학습 기록','서로 다른 문제','학습 노트','연결된 개념'][i]}</span></div>`).join('');
    $('nav-ai').textContent = scope.filter(r=>r.kind==='ai_note').length; $('nav-all').textContent = scope.length; $('nav-problem').textContent = problems.length; $('nav-note').textContent = counts[2];
    document.querySelectorAll('[data-kind]').forEach(el=>{ el.classList.toggle('active',!state.view && el.dataset.kind===(state.kind||'')); el.setAttribute('aria-pressed',String(!state.view && el.dataset.kind===(state.kind||''))); });
    const topicCounts = new Map(); scope.forEach(r=>terms(r).forEach(t=>topicCounts.set(t,(topicCounts.get(t)||0)+1)));
    $('topics').innerHTML = [...topicCounts].sort((a,b)=>b[1]-a[1] || a[0].localeCompare(b[0],'ko')).map(([t,n])=>`<button data-topic="${esc(t)}" class="${state.topic===t?'active':''}"><span># ${esc(t)}</span><small>${n}</small></button>`).join('') || '<p class="hint">분류를 채우면 개념별로 연결됩니다.</p>';
    const results = filter(all, state, data.taxonomy);
    const queryKey = JSON.stringify({...state,record:''});
    if (queryKey !== previousQuery) { page = 1; previousQuery = queryKey; }
    const pages = Math.max(1, Math.ceil(results.length/18)); page = Math.min(page,pages);
    $('list-title').textContent = labels[state.kind] || '모든 기록';
    $('result-count').textContent = `${results.length}건 / ${scope.length}건`;
    $('active-topic').innerHTML = state.topic ? `<div class="topic-banner"><span># ${esc(state.topic)} · 관련 풀이와 학습 노트</span><button id="clear-topic" aria-label="개념 필터 해제">해제 ×</button></div>` : '';
    $('cards').innerHTML = results.length ? results.slice((page-1)*18,page*18).map(card).join('') : '<div class="empty"><strong>표시할 기록이 없습니다.</strong><br>검색어나 필터를 바꿔보세요. 작성 중 기록은 미리보기 빌드에서 볼 수 있습니다.</div>';
    $('pagination').innerHTML = pages>1 ? `<button id="prev-page" ${page===1?'disabled':''}>← 이전</button><span>${page} / ${pages}</span><button id="next-page" ${page===pages?'disabled':''}>다음 →</button>` : '';
  }
  function requestLink(topic='auto') {
    if (!data.repo_url || !/^https:\/\/github\.com\/[^/]+\/[^/]+$/.test(data.repo_url)) return '';
    const body='<!-- study-wiki-note-request -->\n이 요청을 제출하면 무료 Nemotron으로 개념 노트 초안을 생성합니다.\n\n```json\n'+JSON.stringify({topic,user:state.user||''},null,2)+'\n```\n';
    return data.repo_url+'/issues/new?'+new URLSearchParams({title:'[Wiki 노트] '+(topic==='auto'?'개념 자동 탐색':topic),body});
  }
  function generationBox(topic='auto') {
    const link=requestLink(topic);
    return `<div class="generation-box"><div><h2>AI 개념 노트 생성</h2><p>${topic==='auto'?'전체 완료 기록에서 공통 개념을 탐색합니다.':esc(topic)+' 관련 완료 기록을 묶어 정리합니다.'} 관련 기록 전체를 나누어 분석하고, 기존 분석 결과는 재사용합니다.</p><p>GitHub에서 요청을 제출하면 작업이 시작됩니다. 생성 결과는 검토 PR로 올라오며, 학습 목표에 합산되지 않습니다.</p></div>${link?`<a class="primary-button" href="${esc(link)}" target="_blank" rel="noopener noreferrer">GitHub에서 생성 요청 ↗</a>`:'<p>GitHub 저장소 연결이 필요합니다. 도움말의 설정 안내를 확인하세요.</p>'}</div>`;
  }
  function showKnowledge() {
    const scope=all.filter(r=>!state.user || r.user===state.user || (r.contributors||[]).includes(state.user));
    const graph=data.graph||{nodes:[],edges:[]};
    const scopeIds=new Set(scope.map(r=>r.id));
    const nodes=graph.nodes.filter(n=>n.records.some(id=>scopeIds.has(id)));
    if(state.view==='help') {
      $('knowledge').innerHTML=`<p class="eyebrow">HELP</p><h1>도움말</h1><div class="help-list">
      <details open><summary>문제와 코드는 어디서 보나요?</summary><p>기록 제목을 누르면 문제 요약과 풀이를 볼 수 있습니다. ‘풀이 코드’ 탭이나 solution.py 링크를 누르면 UTF-8 코드 화면이 열립니다. 원문 전체는 문제 원문 링크에서 확인하세요.</p></details>
      <details><summary>개념은 어떻게 연결되나요?</summary><p>‘개념 연결’에서 개념을 선택하세요. 같은 기록에 함께 분류된 개념과 근거 기록을 표시합니다. 선후 관계나 선수 지식을 추측한 연결은 아닙니다. 분류가 비어 있으면 연결이 나타나지 않으므로 에이전트에게 기록 보완을 요청하세요.</p></details>
      <details><summary>AI 노트는 어떻게 만드나요?</summary><p>개념 연결 화면의 ‘GitHub에서 생성 요청’을 눌러 요청을 제출합니다. 저장소 쓰기 권한이 있는 참여자의 요청만 실행합니다. Actions가 무료 Nemotron으로 초안을 만들고 PR을 엽니다. PR을 검토하고 merge하면 사이트에 표시됩니다. 미분류 기록도 ‘개념 자동 탐색’으로 분석할 수 있습니다.</p></details>
      <details><summary>직접 쓴 노트와 무엇이 다른가요?</summary><p>학습 노트는 참여자가 작성한 기록이고, AI 개념 노트는 자동 생성 표시·모델·원본 출처·검토 상태가 붙습니다. AI 노트는 일일 목표에 합산하지 않습니다. 원본이 변경되면 재검토 필요 표시가 나타납니다.</p></details>
      <details><summary>기출은 어떻게 모으나요?</summary><p>확인된 시험·채용 이름, 기관, 연도, 회차, 출처를 기록에 추가하면 ‘기출 모음’과 기출·연도 필터에서 찾을 수 있습니다. 제목만 보고 회사나 기출 여부를 자동 추측하지 않습니다.</p></details>
      <details><summary>검색과 개인 Wiki는 어떻게 사용하나요?</summary><p>참여자를 고르면 개인 기록과 해당 참여자의 원본을 인용한 AI 노트를 봅니다. 검색은 제목·본문·코드·분류를 대상으로 하며, 여러 단어는 모두 포함해야 합니다. DFS 등 등록된 별칭도 검색할 수 있습니다. 주소를 복사하면 필터나 상세 기록을 공유할 수 있습니다.</p></details>
      <details><summary>생성 버튼이 실행되지 않거나 노트가 안 보여요.</summary><p>변경 사항이 main에 반영되고 Actions가 활성화되어 있어야 합니다. OPENROUTER_API_KEY Secret과 무료 Nemotron용 WIKI_MODEL 설정을 확인하세요. Actions의 PR 생성 허용도 필요합니다. 요청 이후 작업 상태는 GitHub Actions에서 확인합니다. 무료 한도 초과 시 진행 상태를 저장합니다. 같은 요청을 다시 실행하면 이어가며 유료 모델로 전환하지 않습니다. 생성 PR을 merge해야 공개 Wiki에 반영됩니다.</p></details>
      <details><summary>로컬과 GitHub 사이트는 언제 갱신되나요?</summary><p>로컬은 wiki.py build를 다시 실행하고, 공개 사이트는 main merge 후 갱신됩니다. 로컬 미리보기에는 작성 중 기록을 포함할 수 있습니다. GitHub 연결이 없는 로컬 빌드에서는 --repo-url로 저장소 URL을 지정해야 생성 요청 링크가 활성화됩니다.</p></details></div>`;
      return;
    }
    if(state.view==='exams') {
      const groups=new Map();scope.filter(r=>(r.exam||{}).name).forEach(r=>{const key=examKey(r);groups.set(key,[...(groups.get(key)||[]),r]);});
      $('knowledge').innerHTML=`<p class="eyebrow">PAST EXAMS</p><h1>기출 모음</h1><p class="subtitle">확인된 시험·채용 출처별 문제 기록입니다.</p><div class="cards">${[...groups].map(([name,rows])=>`<article class="card"><h2><button data-exam="${esc(name)}">${esc(name)} →</button></h2><p>${rows.length}개 풀이 · ${esc([...new Set(rows.map(r=>r.exam.organization).filter(Boolean))].join(', '))}</p><div class="tags">${[...new Set(rows.map(r=>r.exam.year).filter(Boolean))].sort().map(y=>`<span class="tag">${esc(y)}</span>`).join('')}</div></article>`).join('')||'<div class="empty">아직 기출 출처가 등록되지 않았습니다.<br>기록에 시험 이름·연도·출처를 추가하면 여기에 모입니다.</div>'}</div>`;
      return;
    }
    const selected=state.topic;
    const rows=selected?scope.filter(r=>terms(r).includes(selected)):[];
    const linked=new Map();
    if(selected)scope.filter(r=>r.kind!=='ai_note' && terms(r).includes(selected)).forEach(r=>terms(r).filter(t=>t!==selected && nodes.some(n=>n.name===t)).forEach(t=>linked.set(t,(linked.get(t)||0)+1)));
    $('knowledge').innerHTML=`<p class="eyebrow">CONCEPTS</p><h1>${selected?esc(selected):'개념 연결'}</h1><p class="subtitle">${selected?'같은 기록에서 함께 사용된 개념과 관련 노트입니다.':'자료구조·알고리즘·태그를 기준으로 풀이와 노트를 연결합니다.'}</p>
    ${selected?`<button class="back" data-view="concepts">← 전체 개념</button><h2 class="section-title">연결된 개념</h2><div class="concept-links">${[...linked].map(([t,n])=>`<button data-topic="${esc(t)}"><strong>${esc(selected)} ↔ ${esc(t)}</strong><span>공통 기록 ${n}개</span></button>`).join('')||'<p class="source-note">함께 분류된 다른 개념이 없습니다. 원본의 분류를 보완하면 연결됩니다.</p>'}</div>`:`<div class="concept-grid">${nodes.map(n=>`<button data-topic="${esc(n.name)}"><strong>${esc(n.name)}</strong><span>관련 기록 ${n.records.filter(id=>scopeIds.has(id)).length}개 →</span></button>`).join('')||'<div class="empty">아직 개념 분류가 없습니다. 에이전트에게 자료구조·알고리즘 보완을 요청하거나, 아래에서 기록을 분석해 노트 초안을 만들 수 있습니다.</div>'}</div>`}
    ${generationBox(selected||'auto')}
    ${selected?`<h2 class="section-title">관련 풀이·노트 (${rows.length})</h2><div class="cards">${rows.map(card).join('')}</div>`:`<h2 class="section-title">노트로 정리할 후보</h2><p class="source-note">완료 기록이 2개 이상 연결된 개념입니다. 실제 생성 시 출처의 관련성을 다시 확인합니다.</p><div class="concept-grid">${nodes.filter(n=>scope.filter(r=>r.kind!=='ai_note' && r.status!=='draft' && n.records.includes(r.id)).length>=2).map(n=>`<button data-topic="${esc(n.name)}"><strong>${esc(n.name)}</strong><span>출처 확인 및 노트 생성 →</span></button>`).join('')||'<p class="source-note">분류 기반 후보가 없습니다. 위의 자동 탐색으로 본문과 코드를 분석할 수 있습니다.</p>'}</div>`}`;
  }
  function showDetail(r) {
    const same = all.filter(x=>x.id!==r.id && r.kind==='problem' && x.kind==='problem' && x.platform===r.platform && x.problem_id===r.problem_id);
    const related = all.filter(x=>x.id!==r.id && !same.includes(x) && terms(x).some(t=>terms(r).includes(t))).slice(0,8);
    const relatedLinks = rows => rows.map(x=>`<a href="${esc(recordLink(x))}">${esc(x.title)}<small>${esc(x.user)} · ${labels[x.kind]}</small></a>`).join('') || '<p class="source-note">아직 연결된 기록이 없습니다.</p>';
    $('detail').innerHTML = `<button class="back" id="back">← 기록 목록으로</button><header class="detail-header"><span class="type">${labels[r.kind]} ${r.problem_id?' / '+esc(r.problem_id):''}</span><h1 tabindex="-1" id="detail-title">${esc(r.title)}</h1><div class="detail-meta">${r.kind==='ai_note'?'<span>AI 자동 생성</span>':`<button data-user="${esc(r.user)}">${esc(r.user)}</button>`}<span>${esc(r.date)}</span><span>${esc(r.language)}</span><span>${r.kind==='ai_note'?(r.stale?'AI 생성 · 원본 변경':r.status==='reviewed'?'AI 생성 · 사람 검토 완료':'AI 생성 · 미검토'):r.status==='draft'?'작성 중': '완료 기록'}</span>${r.level?'<span>'+esc(r.level)+'</span>':''}</div><div class="detail-links"><a href="${safe(r.source_url)}">원본 기록 ↗</a>${r.url && safe(r.url)?`<a href="${safe(r.url)}">문제 원문 ↗</a>`:''}</div><div class="tags">${tagButtons(r)}</div></header><div class="detail-layout"><article class="reader"><div class="tabs" role="tablist" aria-label="기록 내용"><button role="tab" id="read-tab" aria-controls="read-panel" aria-selected="true">${r.kind!=='problem'?'학습 내용':'문제와 풀이'}</button>${r.kind==='problem'?'<button role="tab" id="code-tab" aria-controls="code-panel" aria-selected="false" tabindex="-1">풀이 코드</button>':''}</div><div id="read-panel" role="tabpanel" aria-labelledby="read-tab" class="prose">${r.html}</div>${r.kind==='problem'?`<div id="code-panel" role="tabpanel" aria-labelledby="code-tab" class="code-panel" hidden><div class="code-toolbar"><span>${esc(r.language)}</span><button id="copy-code" aria-live="polite">코드 복사</button></div><pre class="code-block"><code>${esc(r.code)}</code></pre></div>`:''}</article><aside class="related"><section><h2>같은 문제, 다른 기록</h2>${relatedLinks(same)}</section><section><h2>함께 읽을 기록</h2>${relatedLinks(related)}</section><section><h2>출처</h2>${r.kind==='ai_note'?`<p class="source-note">모델: ${esc(r.model)}<br>${r.stale?'원본 변경·삭제로 재검토가 필요합니다.':'AI가 생성한 설명입니다. 인용된 기록과 대조하세요.'}</p>${relatedLinks(all.filter(x=>(r.sources||[]).some(s=>s.id===x.id)))}`:'<p class="source-note">작성자의 README와 풀이 코드.</p>'}${(r.exam||{}).name?`<p class="source-note">기출: ${esc([r.exam.organization,r.exam.name,r.exam.year,r.exam.round].filter(Boolean).join(' · '))}</p>${r.exam.url&&safe(r.exam.url)?`<a href="${safe(r.exam.url)}">기출 출처 ↗</a>`:''}`:''}</section></aside></div>`;
    $('back').onclick = ()=>route({record:''});
    function tab(which) {
      selectedTab=which;
      ['read','code'].forEach(name=>{if($(name+'-tab')) { $(name+'-tab').setAttribute('aria-selected',String(which===name)); $(name+'-tab').tabIndex=which===name?0:-1; $(name+'-panel').hidden=which!==name; }});
    }
    ['read','code'].forEach(name=>{if($(name+'-tab')) { $(name+'-tab').onclick=()=>tab(name); $(name+'-tab').onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key) && $('code-tab')) {e.preventDefault(); const target=e.key==='Home'?'read':e.key==='End'?'code':name==='read'?'code':'read';tab(target);$(target+'-tab').focus();}};}});
    tab(r.kind==='problem'?(state.tab==='code'?'code':selectedTab):'read');
    if ($('copy-code')) $('copy-code').onclick = async()=>{try {await navigator.clipboard.writeText(r.code);$('copy-code').textContent='복사 완료';} catch {$('copy-code').textContent='코드를 선택해 복사하세요';const range=document.createRange();range.selectNodeContents(document.querySelector('#code-panel code'));const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);}};
    document.title = `${r.title} · ${r.user} · Study Wiki`;
  }
  function render() {
    state = Object.fromEntries(new URLSearchParams(location.hash.slice(1)));
    if(isPlaceholder(state.topic)){delete state.topic;history.replaceState(null,'','#'+new URLSearchParams(state));}
    fields.forEach(key=>$(key).value=state[key] || (key==='sort'?'newest':''));
    $('search').value=state.q||'';
    $('scope').textContent = state.user ? `${state.user}의 Wiki` : '전체 기록';
    $('build-status').textContent = data.preview ? '미리보기 · 작성 중 포함' : '완료 기록';
    const r=all.find(r=>r.id===state.record);
    $('library').hidden=!!state.record || !!state.view; $('detail').hidden=!state.record; $('knowledge').hidden=!!state.record || !state.view;
    showLibrary();
    document.querySelectorAll('[data-view]').forEach(el=>el.classList.toggle('active',el.dataset.view===state.view));
    if(state.view && !state.record) showKnowledge();
    if(r) showDetail(r);
    else if(state.record) $('detail').innerHTML='<a class="back" href="#">← 목록으로</a><div class="empty">이 빌드에 없는 기록입니다. 작성자 필터 또는 원본의 변경·삭제 여부를 확인하세요.</div>';
    else document.title='코테 스터디 Wiki';
  }
  fields.forEach(key=>$(key).addEventListener('change',()=>{if(key==='user') {try{localStorage.setItem(storageKey,$(key).value);}catch{}} route({[key]:$(key).value,record:'',tab:''});}));
  $('search').addEventListener('input',()=>route({q:$('search').value,record:''},true));
  $('reset').onclick=()=>{ try {localStorage.removeItem(storageKey);}catch{} location.hash='';render();};
  document.addEventListener('click',e=>{
    const kind=e.target.closest('[data-kind]'),topic=e.target.closest('[data-topic]'),user=e.target.closest('[data-user]'),view=e.target.closest('[data-view]'),exam=e.target.closest('[data-exam]');
    if(view)route({view:view.dataset.view,record:'',topic:'',tab:''});
    if(exam)route({exam:exam.dataset.exam,view:'',kind:'problem',record:'',topic:''});
    if(kind) route({kind:kind.dataset.kind,record:'',view:'',topic:'',tab:''});
    if(topic) route({topic:topic.dataset.topic,record:'',view:'concepts',kind:'',tab:''});
    if(user) route({user:user.dataset.user,record:'',view:'',tab:''});
    if(e.target.id==='clear-topic') route({topic:''});
    if(['next-page','prev-page'].includes(e.target.id)){page+=e.target.id==='next-page'?1:-1;showLibrary();$('list-title').scrollIntoView({block:'start'});}
  });
  document.addEventListener('keydown',e=>{if(e.key==='/' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault(); if(state.record)route({record:''});$('search').focus();}});
  window.addEventListener('hashchange',()=>{render();if(state.record && $('detail-title')){$('detail-title').focus();window.scrollTo(0,0);}});
  if(!location.hash){let saved='';try{saved=localStorage.getItem(storageKey)||'';}catch{}const initial=data.user||saved;if(initial && all.some(r=>r.user===initial))history.replaceState(null,'','#user='+encodeURIComponent(initial));}
  render();
})();
