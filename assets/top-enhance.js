/* トップページ刷新の補助スクリプト（2026-11-27）。app.js には触れず、公開されている入口（#hero-search の送信）だけを使う。
   古い iOS Safari でも動くよう var と function で書く。 */
(function () {
  'use strict';
  var doc = document;
  var body = doc.body;
  if (!body || !body.classList.contains('tr-home')) { return; }
  var reduce = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

  /* ── 検索の候補 ── */
  var form = doc.getElementById('hero-search');
  var input = doc.getElementById('hero-q');
  var MAX = 6;
  var rows = null;
  var loading = false;
  var list = null;
  var active = -1;

  function norm(s) {
    s = String(s || '');
    if (s.normalize) { s = s.normalize('NFKC'); }
    s = s.toLowerCase();
    return s.replace(/[ァ-ヶ]/g, function (c) { return String.fromCharCode(c.charCodeAt(0) - 0x60); });
  }

  function load(done) {
    if (rows) { done(); return; }
    if (loading) { return; }
    loading = true;
    fetch('search-index.json').then(function (r) { return r.ok ? r.json() : []; }).then(function (data) {
      var i, r;
      rows = [];
      for (i = 0; i < data.length; i++) {
        r = data[i];
        if (!r || !r.t || !r.u) { continue; }
        rows.push({ t: r.t, u: r.u, k: r.k || '', d: r.d || '', nt: norm(r.t), ng: norm((r.tags || []).join(' ')) });
      }
      loading = false;
      done();
    }).catch(function () { loading = false; rows = []; });
  }

  function find(q) {
    var tokens = norm(q).split(/\s+/).filter(function (x) { return x; });
    var hits = [];
    var i, j, r, score, ok, pos;
    if (!tokens.length || !rows) { return hits; }
    for (i = 0; i < rows.length; i++) {
      r = rows[i];
      score = 0;
      ok = true;
      for (j = 0; j < tokens.length; j++) {
        pos = r.nt.indexOf(tokens[j]);
        if (pos === 0) { score += 4; } else if (pos > 0) { score += 3; } else if (r.ng.indexOf(tokens[j]) >= 0) { score += 1; } else { ok = false; break; }
      }
      if (ok) {
        if (r.k === 'ツール') { score += 1; }
        hits.push({ r: r, s: score });
      }
    }
    hits.sort(function (a, b) { return b.s - a.s || (a.r.d < b.r.d ? 1 : a.r.d > b.r.d ? -1 : 0); });
    return hits.slice(0, MAX);
  }

  function close() {
    if (!list) { return; }
    list.hidden = true;
    list.innerHTML = '';
    active = -1;
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
  }

  function items() { return list ? list.querySelectorAll('a.tr-sg-item') : []; }

  function setActive(n) {
    var els = items();
    var i;
    if (!els.length) { return; }
    if (n < -1) { n = els.length - 1; }
    if (n >= els.length) { n = -1; }
    active = n;
    for (i = 0; i < els.length; i++) {
      if (i === n) { els[i].classList.add('is-active'); els[i].setAttribute('aria-selected', 'true'); } else { els[i].classList.remove('is-active'); els[i].setAttribute('aria-selected', 'false'); }
    }
    if (n >= 0) {
      input.setAttribute('aria-activedescendant', els[n].id);
      if (els[n].scrollIntoView) { els[n].scrollIntoView({ block: 'nearest' }); }
    } else {
      input.removeAttribute('aria-activedescendant');
    }
  }

  function titleNode(title, q) {
    var span = doc.createElement('span');
    var token = norm(q).split(/\s+/)[0] || '';
    var pos = token ? norm(title).indexOf(token) : -1;
    var mark;
    span.className = 'tr-sg-title';
    /* 正規化で文字数が変わらないときだけ、一致した部分を強調する */
    if (pos >= 0 && norm(title).length === title.length) {
      span.appendChild(doc.createTextNode(title.slice(0, pos)));
      mark = doc.createElement('mark');
      mark.textContent = title.slice(pos, pos + token.length);
      span.appendChild(mark);
      span.appendChild(doc.createTextNode(title.slice(pos + token.length)));
    } else {
      span.textContent = title;
    }
    return span;
  }

  function render() {
    var q = input.value.replace(/^\s+|\s+$/g, '');
    var hits, i, li, a, kind, note;
    if (!q) { close(); return; }
    if (!rows) { load(render); return; }
    hits = find(q);
    list.innerHTML = '';
    active = -1;
    input.removeAttribute('aria-activedescendant');
    for (i = 0; i < hits.length; i++) {
      li = doc.createElement('li');
      li.setAttribute('role', 'presentation');
      a = doc.createElement('a');
      a.className = 'tr-sg-item';
      a.id = 'tr-sg-' + i;
      a.setAttribute('role', 'option');
      a.setAttribute('aria-selected', 'false');
      a.href = hits[i].r.u;
      if (hits[i].r.k) {
        kind = doc.createElement('span');
        kind.className = 'tr-sg-kind';
        kind.textContent = hits[i].r.k;
        a.appendChild(kind);
      }
      a.appendChild(titleNode(hits[i].r.t, q));
      li.appendChild(a);
      list.appendChild(li);
    }
    if (!hits.length) {
      note = doc.createElement('li');
      note.className = 'tr-sg-note';
      note.setAttribute('role', 'presentation');
      note.textContent = '題名に一致する資料は見つかりませんでした。';
      list.appendChild(note);
    }
    li = doc.createElement('li');
    li.setAttribute('role', 'presentation');
    a = doc.createElement('a');
    a.className = 'tr-sg-item tr-sg-all';
    a.id = 'tr-sg-all';
    a.setAttribute('role', 'option');
    a.setAttribute('aria-selected', 'false');
    a.href = './?q=' + encodeURIComponent(q) + '#library';
    a.textContent = '「' + q + '」ですべての資料から探す';
    li.appendChild(a);
    list.appendChild(li);
    list.hidden = false;
    input.setAttribute('aria-expanded', 'true');
  }

  if (form && input && window.fetch) {
    list = doc.createElement('ul');
    list.className = 'tr-suggest';
    list.id = 'hero-suggest';
    list.setAttribute('role', 'listbox');
    list.setAttribute('aria-label', '検索の候補');
    list.hidden = true;
    form.appendChild(list);
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-controls', 'hero-suggest');
    input.setAttribute('aria-expanded', 'false');

    input.addEventListener('input', render);
    input.addEventListener('focus', function () { if (input.value) { render(); } });
    input.addEventListener('keydown', function (e) {
      var els;
      if (e.isComposing || e.keyCode === 229) { return; }
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        if (list.hidden) { render(); return; }
        e.preventDefault();
        setActive(active + (e.key === 'ArrowDown' ? 1 : -1));
      } else if (e.key === 'Enter') {
        els = items();
        if (!list.hidden && active >= 0 && els[active] && els[active].id !== 'tr-sg-all') {
          e.preventDefault();
          window.location.href = els[active].href;
        }
      } else if (e.key === 'Escape' && !list.hidden) {
        e.stopPropagation();
        close();
      }
    });
    /* 「すべての資料から探す」は、ページを読み直さず既存の検索へ渡す */
    list.addEventListener('click', function (e) {
      var t = e.target;
      while (t && t !== list && !(t.classList && t.classList.contains('tr-sg-all'))) { t = t.parentNode; }
      if (t && t !== list) {
        e.preventDefault();
        close();
        if (form.requestSubmit) { form.requestSubmit(); } else { form.querySelector('button[type="submit"]').click(); }
      }
    });
    form.addEventListener('submit', function () { close(); });
    doc.addEventListener('click', function (e) { if (list && !list.hidden && !form.contains(e.target)) { close(); } });
    input.addEventListener('blur', function () {
      setTimeout(function () { if (!form.contains(doc.activeElement)) { close(); } }, 150);
    });
  }

  /* ── Ctrl+K（Mac は ⌘K）で検索欄へ ── */
  var kbd = doc.querySelector('.tr-kbd');
  if (kbd && /Mac|iPhone|iPad/.test(navigator.platform || '')) { kbd.textContent = '⌘ K'; }
  doc.addEventListener('keydown', function (e) {
    var dialog;
    if (!(e.ctrlKey || e.metaKey) || e.altKey || e.shiftKey || (e.key !== 'k' && e.key !== 'K')) { return; }
    dialog = doc.getElementById('collection-dialog');
    if (!input || (dialog && dialog.open)) { return; }
    e.preventDefault();
    input.focus();
    input.select();
    if (input.scrollIntoView) { input.scrollIntoView({ block: 'center', behavior: reduce ? 'auto' : 'smooth' }); }
  });

  /* ── 実数のカウントアップ（表示されたときに1回だけ。動きを減らす設定では出さない） ── */
  function countUp(el) {
    var target = parseInt(el.getAttribute('data-count'), 10);
    var start = null;
    var DURATION = 1100;
    if (!target || isNaN(target)) { return; }
    function step(now) {
      var p;
      if (start === null) { start = now; }
      p = Math.min(1, (now - start) / DURATION);
      p = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * p).toLocaleString('ja-JP');
      if (p < 1) { window.requestAnimationFrame(step); }
    }
    window.requestAnimationFrame(step);
  }

  var hasIO = 'IntersectionObserver' in window;
  var counts = doc.querySelectorAll('.tr-stats [data-count]');
  var statObserver, i;
  if (counts.length && hasIO && !reduce && window.requestAnimationFrame) {
    statObserver = new IntersectionObserver(function (entries) {
      var j;
      for (j = 0; j < entries.length; j++) {
        if (entries[j].isIntersecting) { statObserver.unobserve(entries[j].target); countUp(entries[j].target); }
      }
    }, { threshold: 0.6 });
    for (i = 0; i < counts.length; i++) { statObserver.observe(counts[i]); }
  }

  /* ── セクションの入場（不透明度だけ。位置は動かさない）。#付きで来たときは飛び先を隠さないよう行わない ── */
  var sections, revealObserver;
  if (hasIO && !reduce && !window.location.hash) {
    sections = doc.querySelectorAll('main > section, main > .tg-landing > .tg-feature');
    revealObserver = new IntersectionObserver(function (entries) {
      var j;
      for (j = 0; j < entries.length; j++) {
        if (entries[j].isIntersecting) { entries[j].target.classList.add('tr-in'); revealObserver.unobserve(entries[j].target); }
      }
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.01 });
    for (i = 0; i < sections.length; i++) { sections[i].classList.add('tr-rv'); revealObserver.observe(sections[i]); }
    body.classList.add('tr-rv-on');
    /* 何かの理由で監視が働かないときも、内容が隠れたままにならないようにする */
    window.addEventListener('hashchange', function () { body.classList.remove('tr-rv-on'); });
  }
})();
