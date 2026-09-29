(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var catalog = [], byURL = Object.create(null), articleImages = Object.create(null), loaded = false, limit = 9, timer, toastTimer;
  var kinds = ['記事', '図解', '動画', 'スライド', 'ツール'];
  var hosts = ['ichisouzo-lab.com', 'blog.ichisouzo-lab.com', 'tools.ichisouzo-lab.com', 'check.ichisouzo-lab.com', 'www.youtube.com'];
  var imageHosts = ['tools.ichisouzo-lab.com', 'i.ytimg.com', 'cdn.image.st-hatena.com', 'cdn-ak.f.st-hatena.com'];
  var audienceLabels = { general: '一般の方・ご家族', professional: '医療従事者向け', both: '一般・医療従事者', unspecified: '読者区分なし' };
  var topicRules = {
    '脳・神経': /脳|神経|てんかん|頭痛|認知症|パーキンソン|めまい|しびれ|振戦/,
    '生活習慣': /生活習慣|血圧|糖尿|睡眠|肥満|禁煙|飲酒|認知症|アンチエイジング/,
    '薬・治療': /薬|治療|投与|処方|ワクチン|副作用|抗菌|ステロイド|サプリ/,
    '検査・診断': /検査|診断|鑑別|画像|mri|ct|心電図|脳波|スコア|基準/,
    '栄養・運動': /栄養|運動|筋トレ|食事|ビタミン|サプリ|nmn|フレイル|たんぱく|リハビリ/,
    '医療とAI': /ai|人工知能|chatgpt|gemini|claude|生成|llm|機械学習/
  };
  var state = { q: '', audience: 'all', kind: 'all', topic: '', sort: 'recommended' };
  var storageOK = true;
  var saved = readStore('ichisouzo-saved'), recent = readStore('ichisouzo-recent'), collectionView = 'saved';
  var bookmark = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4h12v17l-6-4-6 4Z"/></svg>';
  var paths = {
    '記事': '<path d="M4 5h7a3 3 0 0 1 3 3v13a4 4 0 0 0-4-3H4Z"/><path d="M14 8a3 3 0 0 1 3-3h5v13h-4a4 4 0 0 0-4 3M7 9h3M7 12h3M17 9h2M17 12h2"/>',
    '図解': '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="2"/><path d="m4 18 6-6 4 4 3-3 4 5"/>',
    '動画': '<rect x="2" y="4" width="20" height="16" rx="3"/><path d="m10 8 6 4-6 4Z"/>',
    'スライド': '<rect x="3" y="3" width="18" height="13" rx="1"/><path d="M12 16v6M8 22l4-3 4 3M7 12l3-3 3 2 4-5"/>',
    'ツール': '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 7h6M9 11h6M9 15h2M14 15h1"/>'
  };
  function escapeHTML(value) { return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function safeURL(value, allowed) {
    try { var u = new URL(value); return u.protocol === 'https:' && !u.username && !u.password && !u.port && allowed.indexOf(u.hostname) >= 0 ? u.href : ''; } catch (e) { return ''; }
  }
  function normalized(value) { return String(value || '').normalize('NFKC').toLowerCase().replace(/\s+/g, ' ').trim(); }
  function clean(item) {
    if (!item || typeof item.t !== 'string' || !item.t.trim() || !safeURL(item.u, hosts) || kinds.indexOf(item.k) < 0) return null;
    var tags = Array.isArray(item.tags) ? item.tags.filter(function (x) { return typeof x === 'string'; }).slice(0, 30) : [];
    var record = { t: item.t.slice(0, 500), u: safeURL(item.u, hosts), k: item.k, a: Object.prototype.hasOwnProperty.call(audienceLabels, item.a) ? item.a : 'unspecified', d: /^\d{4}-\d{2}-\d{2}$/.test(item.d || '') ? item.d : '', tags: tags, img: safeURL(item.img, imageHosts), pages: Number(item.pages) > 0 ? Number(item.pages) : 0 };
    record.text = normalized(record.t + ' ' + tags.join(' '));
    record.group = safeURL(item.group, ['blog.ichisouzo-lab.com']) || (record.k === '記事' ? record.u : '');
    return record;
  }
  function readStore(key) { try { var data = JSON.parse(localStorage.getItem(key) || '[]'); return Array.isArray(data) ? data.map(clean).filter(Boolean).slice(0, 200) : []; } catch (e) { return []; } }
  function writeStore(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch (e) { storageOK = false; return false; } }
  function toast(message) { $('toast').textContent = message; $('toast').classList.add('visible'); clearTimeout(toastTimer); toastTimer = setTimeout(function () { $('toast').classList.remove('visible'); }, 3200); }
  function merge(items) {
    if (!Array.isArray(items)) return;
    items.forEach(function (raw) { var item = clean(raw); if (item) { var prev = byURL[item.u]; if (prev && !item.img) item.img = prev.img; if (prev && item.k === '動画' && item.a === 'unspecified') item.a = prev.a; if (articleImages[item.u]) item.img = articleImages[item.u]; byURL[item.u] = item; } });
    catalog = Object.keys(byURL).map(function (url) { return byURL[url]; });
  }
  function fetchText(url) {
    var controller = new AbortController(), timeout = setTimeout(function () { controller.abort(); }, 12000);
    return fetch(url, { signal: controller.signal }).then(function (r) { if (!r.ok) throw new Error('fetch'); return r.text(); }).finally(function () { clearTimeout(timeout); });
  }
  function classify(title, tags) {
    var text = tags.join(' '), pro = /医療従事者|医療者|医師向け|初期研修医|医向け/.test(text), general = /一般向け|一般の方/.test(text);
    if (/医療従事者向け|医師向け|医向け/.test(title)) return 'professional';
    return pro && general ? 'both' : pro ? 'professional' : general ? 'general' : 'unspecified';
  }
  function readURL() {
    var params = new URLSearchParams(location.search);
    state.q = (params.get('q') || '').slice(0, 200);
    state.audience = ['all', 'general', 'professional'].indexOf(params.get('audience')) >= 0 ? params.get('audience') : 'all';
    state.kind = kinds.indexOf(params.get('kind')) >= 0 ? params.get('kind') : 'all';
    state.topic = Object.prototype.hasOwnProperty.call(topicRules, params.get('topic')) ? params.get('topic') : '';
    state.sort = ['newest', 'title'].indexOf(params.get('sort')) >= 0 ? params.get('sort') : 'recommended';
    $('site-search').value = state.q; $('sort-order').value = state.sort;
  }
  function updateURL(push) {
    var url = new URL(location.href);
    ['q', 'audience', 'kind', 'topic', 'sort'].forEach(function (key) { var value = state[key]; if (value && value !== 'all' && value !== 'recommended') url.searchParams.set(key, value); else url.searchParams.delete(key); });
    if (url.href !== location.href) history[push ? 'pushState' : 'replaceState']({}, '', url);
  }
  function art(item) {
    var cls = { 'ツール': 'kind-tool', 'スライド': 'kind-slides', '動画': 'kind-video' }[item.k] || '';
    var topic = Object.keys(topicRules).filter(function (x) { return topicRules[x].test(item.text); })[0] || '医療と健康';
    return '<div class="media-art ' + cls + '" aria-hidden="true"><svg viewBox="0 0 24 24">' + paths[item.k] + '</svg><span class="art-title">' + escapeHTML(topic) + '</span></div>';
  }
  function saveMarkup(item) {
    var isSaved = saved.some(function (x) { return x.u === item.u; });
    return '<button type="button" class="save-button" data-save="' + escapeHTML(item.u) + '" aria-pressed="' + isSaved + '" aria-label="' + escapeHTML((isSaved ? '保存を解除：' : 'あとで読むに保存：') + item.t) + '">' + bookmark + '</button>';
  }
  function card(item) {
    var image = item.img ? '<img src="' + escapeHTML(item.img) + '" alt="" loading="lazy" decoding="async" data-fallback-url="' + escapeHTML(item.u) + '">' : art(item);
    var note = item.d ? '<time datetime="' + item.d + '">' + item.d.replace(/-/g, '.') + '</time>' : '<span class="record-note">' + (item.k === 'ツール' ? '診断支援ツール' : '公開コンテンツ') + '</span>';
    return '<article class="content-card" data-reader="' + item.a + '"><a class="card-link" data-track href="' + escapeHTML(item.u) + '"><div class="card-media">' + image + '<span class="kind-label">' + item.k + '</span></div><div class="card-body"><div class="card-category"><span>' + audienceLabels[item.a] + '</span>' + (item.pages ? '<span>' + item.pages + '枚</span>' : '') + '</div><h3>' + escapeHTML(item.t) + '</h3></div></a><div class="card-footer">' + note + saveMarkup(item) + '</div></article>';
  }
  function results() {
    var terms = normalized(state.q).split(' ').filter(Boolean);
    var list = catalog.filter(function (item) {
      return (state.audience === 'all' || item.a === state.audience || item.a === 'both') && (state.kind === 'all' || item.k === state.kind) && (!state.topic || topicRules[state.topic].test(item.text)) && terms.every(function (term) { return item.text.indexOf(term) >= 0; });
    });
    list.sort(state.sort === 'title' ? function (a, b) { return a.t.localeCompare(b.t, 'ja'); } : function (a, b) { return b.d.localeCompare(a.d); });
    if (state.sort === 'recommended' && state.kind === 'all') {
      // 形式を交互に並べ、同じテーマだけで最初の画面が埋まらないようにする。
      var groups = {}, mixed = [], order = ['記事', '図解', 'ツール', '動画', 'スライド'];
      order.forEach(function (kind) { groups[kind] = list.filter(function (x) { return x.k === kind; }); });
      if (!state.q && !state.topic && state.audience === 'all') {
        // 最初の一段で両方の読者への入口を見せる。
        [['記事', 'general'], ['記事', 'professional'], ['ツール', 'professional'], ['図解', 'general'], ['スライド', 'professional'], ['動画', 'general']].forEach(function (choice) {
          var group = groups[choice[0]], index = group.findIndex(function (x) { return x.a === choice[1] && (choice[0] !== 'ツール' || /頭痛/.test(x.t)); });
          if (index >= 0) mixed.push(group.splice(index, 1)[0]);
        });
      }
      while (mixed.length < list.length) order.forEach(function (kind) { if (groups[kind].length) mixed.push(groups[kind].shift()); });
      list = mixed;
      if (!state.q && !state.topic) {
        var seen = Object.create(null), repeated = [];
        list = list.filter(function (item) {
          var key = item.group || item.u;
          var titleKey = normalized(item.t).split(/[｜|：:？?]/)[0].replace(/\s/g, '').slice(0, 18);
          if (seen[key] || (titleKey.length >= 6 && seen['title:' + titleKey])) { repeated.push(item); return false; }
          seen[key] = true; if (titleKey.length >= 6) seen['title:' + titleKey] = true; return true;
        }).concat(repeated);
      }
    }
    return list;
  }
  function render() {
    if (!loaded) return;
    var list = results();
    $('content-grid').innerHTML = list.slice(0, limit).map(card).join('');
    $('content-grid').setAttribute('aria-busy', 'false');
    $('result-status').textContent = list.length.toLocaleString('ja-JP') + '件' + (state.q ? '「' + state.q + '」' : '') + ' / ' + Math.min(limit, list.length) + '件を表示';
    $('empty-state').hidden = list.length !== 0;
    $('load-more').hidden = list.length <= limit;
    $('fulltext-link').href = 'https://blog.ichisouzo-lab.com/search?q=' + encodeURIComponent(state.q || state.topic);
    $('reset-filters').hidden = !state.q && !state.topic && state.audience === 'all' && state.kind === 'all';
    [['audience-filters', 'audience'], ['kind-filters', 'kind'], ['topic-filters', 'topic']].forEach(function (pair) {
      $(pair[0]).querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset[pair[1]] === state[pair[1]])); });
    });
    bindImages($('content-grid'));
  }
  function bindImages(root) {
    root.querySelectorAll('img[data-fallback-url]').forEach(function (img) {
      function upgradeStrip() {
        // タイトル帯だけの極端に横長なサムネイルは、実図解の上部プレビューへ。
        if (img.naturalWidth > img.naturalHeight * 3 && /\/thumb\.png$/.test(img.src) && !img.dataset.triedOriginal) { img.dataset.triedOriginal = 'true'; img.src = img.src.replace(/thumb\.png$/, 'infographic.png'); }
      }
      img.addEventListener('load', upgradeStrip);
      img.addEventListener('error', function fallback() {
        if (img.src.indexOf('/infographics/') >= 0 && /\/thumb\.png$/.test(img.src) && !img.dataset.triedOriginal) { img.dataset.triedOriginal = 'true'; img.src = img.src.replace(/thumb\.png$/, 'infographic.png'); return; }
        var item = byURL[img.dataset.fallbackUrl];
        if (item) { var box = document.createElement('div'); box.innerHTML = art(item); img.replaceWith(box.firstChild); }
        else img.hidden = true;
      });
      if (img.complete) { if (img.naturalWidth) upgradeStrip(); else img.dispatchEvent(new Event('error')); }
    });
  }
  function change(push) { limit = 9; updateURL(push); render(); }
  function savedUI() {
    $('saved-count').textContent = saved.length;
    $('open-collection').setAttribute('aria-label', 'あとで読む：' + saved.length + '件');
    document.querySelectorAll('[data-save]').forEach(function (button) {
      var isSaved = saved.some(function (x) { return x.u === button.dataset.save; });
      var item = byURL[button.dataset.save] || saved.find(function (x) { return x.u === button.dataset.save; }) || recent.find(function (x) { return x.u === button.dataset.save; });
      button.setAttribute('aria-pressed', String(isSaved));
      if (item) button.setAttribute('aria-label', (isSaved ? '保存を解除：' : 'あとで読むに保存：') + item.t);
    });
  }
  function renderCollection() {
    var data = collectionView === 'saved' ? saved : recent;
    document.querySelectorAll('[data-collection]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.collection === collectionView)); });
    $('collection-list').innerHTML = data.length ? data.map(function (item) { return '<div class="collection-item"><a data-track href="' + escapeHTML(item.u) + '"><span>' + item.k + ' ・ ' + audienceLabels[item.a] + '</span><h3>' + escapeHTML(item.t) + '</h3></a>' + saveMarkup(item) + '</div>'; }).join('') : '<div class="collection-empty">' + (collectionView === 'saved' ? '気になるコンテンツのしおりボタンを押すと、<br>ここに保存されます。' : 'このページから開いたコンテンツが<br>ここに表示されます。') + '</div>';
    $('clear-history').hidden = collectionView !== 'recent' || !recent.length;
  }
  function toggleSaved(url) {
    var idx = saved.findIndex(function (x) { return x.u === url; });
    var item = byURL[url] || recent.find(function (x) { return x.u === url; });
    if (idx >= 0) saved.splice(idx, 1);
    else if (item) { if (saved.length >= 200) { toast('保存は200件までです。不要な保存を解除してください。'); return; } saved.unshift(item); }
    else return;
    var persisted = writeStore('ichisouzo-saved', saved);
    savedUI();
    if ($('collection-dialog').open) { renderCollection(); $('close-collection').focus(); }
    toast(persisted ? (idx >= 0 ? '保存を解除しました' : 'あとで読むに保存しました') : 'ブラウザーに保存できないため、この画面内だけで保持します');
  }
  function track(url) {
    var item = byURL[url] || saved.find(function (x) { return x.u === url; });
    if (!item) return;
    recent = [item].concat(recent.filter(function (x) { return x.u !== url; })).slice(0, 30);
    writeStore('ichisouzo-recent', recent);
  }
  var menu = document.querySelector('.menu-button'), nav = $('global-nav');
  function closeMenu() { menu.setAttribute('aria-expanded', 'false'); menu.setAttribute('aria-label', 'メニューを開く'); nav.classList.remove('open'); }
  menu.addEventListener('click', function () { var open = menu.getAttribute('aria-expanded') !== 'true'; menu.setAttribute('aria-expanded', String(open)); menu.setAttribute('aria-label', open ? 'メニューを閉じる' : 'メニューを開く'); nav.classList.toggle('open', open); });
  nav.addEventListener('click', closeMenu);
  document.addEventListener('keydown', function (event) { if (event.key === 'Escape') closeMenu(); if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !event.target.isContentEditable && !/INPUT|TEXTAREA|SELECT/.test(event.target.tagName) && !$('collection-dialog').open) { event.preventDefault(); $('site-search').focus(); } });
  document.addEventListener('click', function (event) {
    var save = event.target.closest('[data-save]'); if (save) { toggleSaved(save.dataset.save); return; }
    var trackLink = event.target.closest('a[data-track]'); if (trackLink) track(trackLink.href);
    var series = event.target.closest('[data-series]'); if (series) { state = { q: series.dataset.series, audience: 'all', kind: 'all', topic: '', sort: 'recommended' }; $('site-search').value = state.q; $('sort-order').value = state.sort; change(true); }
    var kind = event.target.closest('[data-kind-link]'); if (kind) { state.kind = kind.dataset.kindLink; state.q = ''; state.topic = ''; $('site-search').value = ''; change(true); }
  });
  document.addEventListener('auxclick', function (event) { var link = event.target.closest('a[data-track]'); if (link && event.button === 1) track(link.href); });
  [['audience-filters', 'audience'], ['kind-filters', 'kind'], ['topic-filters', 'topic']].forEach(function (pair) { $(pair[0]).addEventListener('click', function (event) { var b = event.target.closest('button'); if (!b) return; var value = b.dataset[pair[1]]; state[pair[1]] = pair[1] === 'topic' && state.topic === value ? '' : value; change(true); }); });
  $('site-search').addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(function () { state.q = $('site-search').value.slice(0, 200); change(false); }, 160); });
  $('search-form').addEventListener('submit', function (event) { event.preventDefault(); clearTimeout(timer); state.q = $('site-search').value.slice(0, 200); change(true); $('result-status').scrollIntoView({ block: 'start', behavior: 'smooth' }); });
  $('sort-order').addEventListener('change', function () { state.sort = this.value; change(true); });
  $('reset-filters').addEventListener('click', function () { state = { q: '', audience: 'all', kind: 'all', topic: '', sort: 'recommended' }; $('site-search').value = ''; $('sort-order').value = 'recommended'; change(true); });
  $('load-more').addEventListener('click', function () { var old = limit; limit += 9; render(); var next = $('content-grid').children[old]; if (next) next.querySelector('a').focus({ preventScroll: true }); });
  window.addEventListener('popstate', function () { readURL(); limit = 9; render(); });
  $('share-search').addEventListener('click', function () { updateURL(false); var url = new URL(location.href); url.hash = 'library'; if (!navigator.clipboard) { toast('アドレスバーのURLをコピーして共有できます'); return; } navigator.clipboard.writeText(url.href).then(function () { toast('検索条件のリンクをコピーしました'); }).catch(function () { toast('アドレスバーのURLをコピーして共有できます'); }); });
  $('open-collection').addEventListener('click', function () { renderCollection(); $('collection-dialog').showModal(); });
  $('close-collection').addEventListener('click', function () { $('collection-dialog').close(); });
  $('collection-dialog').addEventListener('click', function (event) { if (event.target === this) { var rect = this.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right) this.close(); } });
  document.querySelectorAll('[data-collection]').forEach(function (b) { b.addEventListener('click', function () { collectionView = b.dataset.collection; renderCollection(); }); });
  $('clear-history').addEventListener('click', function () { recent = []; var persisted = writeStore('ichisouzo-recent', recent); renderCollection(); toast(persisted ? '閲覧履歴を消去しました' : '保存領域にアクセスできず、履歴の消去を記録できませんでした'); });
  function themeUI() { var dark = document.documentElement.dataset.theme === 'dark'; $('theme-toggle').setAttribute('aria-pressed', String(dark)); $('theme-toggle').setAttribute('aria-label', dark ? 'ライトモードに切り替える' : 'ダークモードに切り替える'); }
  $('theme-toggle').addEventListener('click', function () { var dark = document.documentElement.dataset.theme !== 'dark'; document.documentElement.dataset.theme = dark ? 'dark' : 'light'; try { localStorage.setItem('ichisouzo-theme', dark ? 'dark' : 'light'); } catch (e) {} themeUI(); });
  window.addEventListener('storage', function (event) { if (event.key === 'ichisouzo-saved' || event.key === 'ichisouzo-recent') { saved = readStore('ichisouzo-saved'); recent = readStore('ichisouzo-recent'); savedUI(); if ($('collection-dialog').open) renderCollection(); } });
  function updateRSS(xml) {
    var doc = new DOMParser().parseFromString(xml, 'application/xml');
    if (doc.querySelector('parsererror')) throw new Error('rss');
    var records = Array.prototype.map.call(doc.querySelectorAll('item'), function (node) {
      function val(tag) { var n = node.querySelector(tag); return n ? n.textContent.trim() : ''; }
      var tags = Array.prototype.map.call(node.querySelectorAll('category'), function (x) { return x.textContent.trim(); });
      var date = new Date(val('pubDate'));
      // フィードの暦日を優先し、時差で前日へずらさない。
      var formatted = isNaN(date.getTime()) ? '' : new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Tokyo' }).format(date);
      return { t: val('title'), u: safeURL(val('link'), ['blog.ichisouzo-lab.com']), k: '記事', a: classify(val('title'), tags), d: formatted, tags: tags };
    });
    if (!records.some(function (item) { return clean(item); })) throw new Error('empty rss');
    merge(records);
  }
  function updateManifest(data, kind) {
    var entries = data[kind === '図解' ? 'items' : 'decks']; if (!Array.isArray(entries) || !entries.length) throw new Error('manifest');
    var records = [];
    entries.forEach(function (item) {
      if (!item || !/^[a-zA-Z0-9_-]+$/.test(item.slug || '') || typeof item.title !== 'string') return;
      var tags = (Array.isArray(item.tags) ? item.tags : []).concat([item.audience || '', item.subtitle || '']);
      var record = { t: item.title, u: 'https://tools.ichisouzo-lab.com/' + (kind === '図解' ? 'infographics/' : 'slides/') + item.slug + '/', k: kind, a: classify(item.title, tags), d: item.date || item.published_date || '', tags: tags, pages: kind === 'スライド' ? item.slide_count : 0, group: item.blog_url };
      if (kind === '図解') record.img = record.u + 'thumb.png';
      records.push(record);
      if (/^[\w-]{11}$/.test(item.youtube_id || '')) records.push({ t: item.title, u: 'https://www.youtube.com/watch?v=' + item.youtube_id, k: '動画', a: record.a, d: record.d, tags: tags, img: 'https://i.ytimg.com/vi/' + item.youtube_id + '/hqdefault.jpg', group: item.blog_url });
      if (kind === '図解' && safeURL(item.blog_url, ['blog.ichisouzo-lab.com'])) { articleImages[item.blog_url] = record.img; if (byURL[item.blog_url]) byURL[item.blog_url].img = record.img; }
    });
    merge(records);
  }
  function refreshPublic() {
    return Promise.allSettled([
      fetchText('https://blog.ichisouzo-lab.com/rss').then(updateRSS),
      fetchText('https://tools.ichisouzo-lab.com/infographics/manifest.json').then(function (s) { updateManifest(JSON.parse(s), '図解'); }),
      fetchText('https://tools.ichisouzo-lab.com/slides/manifest.json').then(function (s) { updateManifest(JSON.parse(s), 'スライド'); })
    ]).then(function (statuses) {
      if (!loaded && catalog.length) { loaded = true; render(); }
      else if (loaded) render();
      var complete = statuses.every(function (x) { return x.status === 'fulfilled'; });
      $('catalog-status').textContent = complete ? '公開ブログ・資料一覧の新着を反映しています。読者の絞り込みは対象が明記された情報のみ。' : '保存済みのカタログを表示しています。一部の新着情報は取得できませんでした。';
      if (!catalog.length) { $('result-status').textContent = '検索データを取得できませんでした'; $('content-grid').setAttribute('aria-busy', 'false'); $('empty-state').hidden = false; $('empty-state').querySelector('h3').textContent = '検索データを読み込めません'; $('empty-state').querySelector('p').textContent = '通信をご確認のうえ再読み込みするか、ブログ一覧をご利用ください。'; }
    });
  }
  readURL(); savedUI(); themeUI();
  var heroImg = document.querySelector('.hero-image img');
  heroImg.addEventListener('error', function () { if (!heroImg.dataset.triedOriginal) { heroImg.dataset.triedOriginal = 'true'; heroImg.src = heroImg.src.replace('thumb.png', 'infographic.png'); } else { heroImg.hidden = true; document.querySelector('.hero-image').innerHTML = art({ k: '図解', text: '運動' }); } });
  fetchText('search-index.json').then(function (s) { var data = JSON.parse(s); if (!Array.isArray(data)) throw new Error('catalog'); merge(data); loaded = true; render(); }).catch(function () { $('catalog-status').textContent = '公開サイトから検索情報を取得しています…'; }).finally(refreshPublic);
})();
