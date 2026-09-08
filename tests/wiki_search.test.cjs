const test = require('node:test');
const assert = require('node:assert/strict');
const { filter } = require('../study_wiki/assets/search.js');
const taxonomy = require('../study_wiki/taxonomy.json');
const records = [
  {id:'a',kind:'problem',user:'alice',title:'탐색',date:'2026-09-08',language:'python',data_structures:['해시'],algorithms:['깊이 우선 탐색'],tags:[],search:'탐색 해시 깊이 우선 탐색 visited'},
  {id:'b',kind:'note',user:'bob',title:'해시 노트',date:'2026-09-07',language:'',data_structures:[],algorithms:[],tags:['해시'],search:'해시 개념 충돌'},
  {id:'c',kind:'problem',user:'alice',title:'기초',date:'2026-09-09',language:'java',data_structures:[],algorithms:[],tags:['Lv.1'],search:'기초 return value'}
];
test('combines personal, type, structure, algorithm and language filters',()=>{
  assert.deepEqual(filter(records,{user:'alice',kind:'problem',structure:'해시',algorithm:'깊이 우선 탐색',language:'python'}).map(r=>r.id),['a']);
  assert.equal(filter(records,{user:'alice',kind:'note'}).length,0);
});
test('topics connect problems and notes; unclassified remains findable',()=>{
  assert.deepEqual(filter(records,{topic:'해시'}).map(r=>r.id),['a','b']);
  assert.deepEqual(filter(records,{classification:'missing'}).map(r=>r.id),['c']);
});
test('aliases, code search, AND queries and no results',()=>{
  assert.equal(filter(records,{q:'DFS'},taxonomy)[0].id,'a');
  assert.equal(filter(records,{q:'dict visited'},taxonomy)[0].id,'a');
  assert.equal(filter(records,{q:'return value'},taxonomy)[0].id,'c');
  assert.equal(filter(records,{q:'visited 충돌'},taxonomy).length,0);
});
test('ordering and inputs remain stable',()=>{
  assert.deepEqual(filter(records,{sort:'oldest'}).map(r=>r.id),['b','a','c']);
  assert.deepEqual(records.map(r=>r.id),['a','b','c']);
});
test('AI notes use contributor filters and exam metadata is independent',()=>{
  const note={...records[1],id:'ai',kind:'ai_note',user:'AI',contributors:['alice','bob']};
  assert.equal(filter([note],{user:'alice',kind:'ai_note'}).length,1);
  assert.equal(filter([note],{user:'charlie'}).length,0);
  const exam={...records[0],exam:{name:'공채',year:'2024'}};
  assert.equal(filter([exam,...records],{exam:'공채',exam_year:'2024'}).length,1);
  assert.equal(filter([exam],{exam_year:'2025'}).length,0);
});

test('exams with identical names from different organizations remain distinct',()=>{
  const a={...records[0],exam:{name:'공채',organization:'기관 A'}};
  const b={...records[1],exam:{name:'공채',organization:'기관 B'}};
  assert.equal(filter([a,b],{exam:'기관 A · 공채'}).length,1);
});
test('placeholder concepts are omitted and counted as unclassified',()=>{
  const {terms,isPlaceholder}=require('../study_wiki/assets/search.js');
  const record={...records[0],data_structures:['none'],algorithms:['null'],tags:['미분류']};
  assert.deepEqual(terms(record),[]);
  assert.equal(filter([record],{classification:'missing'}).length,1);
  assert.equal(isPlaceholder('None'),true);
});
test('spelling variants work in queries and old topic/filter URLs',()=>{
  for (const q of ['깊이우선탐색', 'ＤＦＳ', 'depthfirstsearch', '깊이  우선 탐색']) {
    assert.deepEqual(filter(records,{q},taxonomy).map(r=>r.id),['a']);
  }
  assert.deepEqual(filter(records,{topic:'D F S'},taxonomy).map(r=>r.id),['a']);
  assert.deepEqual(filter(records,{structure:'hash map'},taxonomy).map(r=>r.id),['a']);
  assert.deepEqual(filter(records,{algorithm:'깊이우선탐색'},taxonomy).map(r=>r.id),['a']);
});
test('raw detail keywords remain searchable even when they have a core mapping',()=>{
  const detail={...records[0],search:'index 처음 보는 표현 구현'};
  assert.equal(filter([detail],{q:'index'},taxonomy).length,1);
  assert.equal(filter([detail],{q:'처음보는표현'},taxonomy).length,1);
});
