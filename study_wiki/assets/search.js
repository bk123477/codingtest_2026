/* Shared pure query engine: browser and Node tests use the same implementation. */
(function (root) {
  'use strict';
  function termKey(value) { return String(value || '').normalize('NFKC').toLocaleLowerCase().replace(/\s+/g, ''); }
  function canonical(value, taxonomy = {}, field) {
    const groups = field ? [taxonomy[field] || {}] : Object.values(taxonomy);
    for (const group of groups) for (const [name, aliases] of Object.entries(group)) {
      if ([name, ...aliases].some(alias => termKey(alias) === termKey(value))) return name;
    }
    return value;
  }
  function isPlaceholder(value) { return ['none','null','n/a','미분류','미입력','없음','-'].includes(String(value||'').trim().toLocaleLowerCase()); }
  function terms(record) { return [...new Set([...record.data_structures, ...record.algorithms, ...record.tags])].filter(t=>!isPlaceholder(t)); }
  function unclassified(record) { return record.kind === 'problem' ? ![...record.data_structures,...record.algorithms].some(t=>!isPlaceholder(t)) : !terms(record).length; }
  function examKey(record) { const e=record.exam||{}; return e.name ? [e.organization,e.name].filter(Boolean).join(' · ') : ''; }
  function filter(records, state, taxonomy = {}) {
    const aliases = {};
    Object.values(taxonomy).forEach(group => Object.entries(group).forEach(([name, values]) => {
      [name, ...values].forEach(value => { aliases[termKey(value)] = name.toLocaleLowerCase(); });
    }));
    const query = (state.q || '').trim().toLocaleLowerCase();
    const words = aliases[termKey(query)] ? [[query, aliases[termKey(query)]]] : query.split(/\s+/).filter(Boolean).map(word => [word, aliases[termKey(word)] || word]);
    const rows = records.filter(r => (!state.user || r.user === state.user || (r.contributors || []).includes(state.user))
      && (!state.kind || r.kind === state.kind)
      && (!state.exam || examKey(r) === state.exam)
      && (!state.exam_year || (r.exam || {}).year === state.exam_year)
      && (!state.structure || r.data_structures.includes(canonical(state.structure, taxonomy, 'data_structures')))
      && (!state.algorithm || r.algorithms.includes(canonical(state.algorithm, taxonomy, 'algorithms')))
      && (!state.language || r.language === state.language)
      && (!state.topic || terms(r).includes(canonical(state.topic, taxonomy)))
      && (state.classification !== 'missing' || unclassified(r))
      && words.every(variants => variants.some(word => termKey(r.search).includes(termKey(word)))));
    return rows.sort((a,b) => state.sort === 'title' ? a.title.localeCompare(b.title, 'ko') || a.id.localeCompare(b.id)
      : state.sort === 'oldest' ? a.date.localeCompare(b.date) || a.id.localeCompare(b.id)
      : b.date.localeCompare(a.date) || b.id.localeCompare(a.id));
  }
  const api = { canonical, termKey, filter, terms, unclassified, examKey, isPlaceholder };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.WikiSearch = api;
})(typeof window === 'undefined' ? globalThis : window);
