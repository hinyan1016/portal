(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  // スマホは1列なので、最初の表示と追加分を6件にして、ツールやシリーズの入口までの距離を縮める。
  var pageSize = window.matchMedia && window.matchMedia('(max-width: 680px)').matches ? 6 : 9;
  var catalog = [], byURL = Object.create(null), searchByGroup = Object.create(null), articleImages = Object.create(null), loaded = false, limit = pageSize, timer, toastTimer;
  var kinds = ['記事', '図解', '動画', 'スライド', 'ツール'];
  var hosts = ['ichisouzo-lab.com', 'blog.ichisouzo-lab.com', 'tools.ichisouzo-lab.com', 'check.ichisouzo-lab.com', 'www.youtube.com'];
  var imageHosts = ['tools.ichisouzo-lab.com', 'i.ytimg.com', 'cdn.image.st-hatena.com', 'cdn-ak.f.st-hatena.com'];
  var audienceLabels = { general: '一般の方・ご家族', professional: '医療従事者向け', both: '一般・医療従事者', unspecified: '読者区分なし' };
  var seriesLabels = { 'anti-aging': '医師が採点するアンチエイジング', 'body-mysteries': 'からだの不思議' };
  // 同じ語の表記だけをそろえる。症状と病名、関連する別の疾患は同義語にしない。
  var searchAliases = [
    ['物忘れ', ['もの忘れ', '物忘れ', '物わすれ', 'ものわすれ']],
    ['しびれ', ['しびれ', '痺れ']], ['めまい', ['めまい', '眩暈']], ['けいれん', ['けいれん', '痙攣']],
    ['ssri', ['SSRI', 'SSRIs', '選択的セロトニン再取り込み阻害薬']],
    ['snri', ['SNRI', 'SNRIs', 'セロトニン・ノルアドレナリン再取り込み阻害薬', 'セロトニンノルアドレナリン再取り込み阻害薬']],
    ['nsaids', ['NSAIDs', 'NSAID', '非ステロイド性抗炎症薬']],
    ['ppi', ['PPI', 'PPIs', 'プロトンポンプ阻害薬']],
    ['レベチラセタム', ['LEV', 'レベチラセタム']], ['ブリーバラセタム', ['BRV', 'ブリーバラセタム']]
  ];
  // 英字の略語は単語の一部に一致させない（例: NSAIDsやBRAINのai、RCTやinteractのct）。
  var topicRules = {
    '脳・神経': /脳|神経|てんかん|頭痛|認知症|パーキンソン|めまい|しびれ|振戦/,
    '生活習慣': /生活習慣|血圧|糖尿|睡眠|肥満|禁煙|飲酒|認知症|アンチエイジング/,
    '薬・治療': /薬|治療|投与|処方|ワクチン|副作用|抗菌|ステロイド|サプリ/,
    '検査・診断': /検査|診断|鑑別|画像|(^|[^a-z])(mri|ct)(?![a-z])|心電図|脳波|スコア|基準/,
    '栄養・運動': /栄養|運動|筋トレ|食事|ビタミン|サプリ|nmn|フレイル|たんぱく|リハビリ/,
    '医療とAI': /(^|[^a-z])ai(?![a-z])|人工知能|chatgpt|gemini|claude|生成ai|llm|機械学習/
  };
  var state = { q: '', audience: 'all', kind: 'all', topic: '', sort: 'recommended', series: '' };
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
  function safeImage(value) {
    // 自サイトの軽量サムネイル（thumbs/*.webp）か、許可した画像ホストのURLだけを表示する。
    return /^thumbs\/[A-Za-z0-9_-]+\.webp$/.test(String(value || '')) ? value : safeURL(value, imageHosts);
  }
  function decodeTitle(value) {
    var text = String(value || ''), named = { amp: '&', quot: '"', apos: "'", lt: '<', gt: '>', nbsp: ' ' };
    // 文字参照だけを復号し、HTMLとして解釈しない。二重エスケープにも対応する。
    for (var pass = 0; pass < 3; pass += 1) {
      var decoded = text.replace(/&(#\d{1,7}|#x[0-9a-f]{1,6}|amp|quot|apos|lt|gt|nbsp);/gi, function (entity, code) {
        if (code[0] !== '#') return named[code.toLowerCase()];
        var point = code[1].toLowerCase() === 'x' ? parseInt(code.slice(2), 16) : parseInt(code.slice(1), 10);
        return point > 0 && point <= 0x10ffff && !(point >= 0xd800 && point <= 0xdfff) ? String.fromCodePoint(point) : entity;
      });
      if (decoded === text) break;
      text = decoded;
    }
    return text;
  }
  function normalized(value) {
    var text = decodeTitle(value).normalize('NFKC').toLowerCase().replace(/\s+/g, ' ').trim();
    searchAliases.forEach(function (rule) {
      rule[1].forEach(function (alias) {
        var word = alias.normalize('NFKC').toLowerCase(), escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        // 略語は英数字の一部に一致させない（例: LEVとlevodopa）。
        var bounded = /^[a-z0-9-]+$/.test(word);
        var pattern = bounded ? new RegExp('(^|[^a-z0-9])' + escaped + '(?=$|[^a-z0-9])', 'g') : new RegExp(escaped, 'g');
        text = text.replace(pattern, function (match, prefix) { return (bounded ? prefix || '' : '') + rule[0]; });
      });
    });
    return text;
  }
  function matchesTerm(text, term) {
    return /^(ssri|snri|nsaids|ppi)$/.test(term) ? new RegExp('(^|[^a-z0-9])' + term + '(?=$|[^a-z0-9])').test(text) : text.indexOf(term) >= 0;
  }
  function searchable(value) {
    // 略語へ置き換えた後も元の「薬」等の語を残し、テーマ絞り込みを保つ。
    return normalized(value) + ' ' + decodeTitle(value).normalize('NFKC').toLowerCase().replace(/\s+/g, ' ').trim();
  }
  function clean(item) {
    if (!item || typeof item.t !== 'string' || !item.t.trim() || !safeURL(item.u, hosts) || kinds.indexOf(item.k) < 0) return null;
    var tags = Array.isArray(item.tags) ? item.tags.filter(function (x) { return typeof x === 'string'; }).slice(0, 30) : [];
    var aliases = Array.isArray(item.aliases) ? item.aliases.filter(function (x) { return typeof x === 'string'; }).slice(0, 30) : [];
    var record = { t: decodeTitle(item.t).slice(0, 500), u: safeURL(item.u, hosts), k: item.k, a: Object.prototype.hasOwnProperty.call(audienceLabels, item.a) ? item.a : 'unspecified', d: /^\d{4}-\d{2}-\d{2}$/.test(item.d || '') ? item.d : '', tags: tags, aliases: aliases, summary: typeof item.summary === 'string' ? decodeTitle(item.summary).slice(0, 180) : '', img: safeImage(item.img), pages: Number(item.pages) > 0 ? Number(item.pages) : 0 };
    if (item.k === '記事' && item.series && Object.prototype.hasOwnProperty.call(seriesLabels, item.series.id) && Number.isInteger(item.series.number) && item.series.number > 0 && item.series.number <= 999) record.series = { id: item.series.id, number: item.series.number };
    record.text = searchable(record.t + ' ' + tags.join(' ') + ' ' + aliases.join(' '));
    record.group = safeURL(item.group, ['blog.ichisouzo-lab.com']) || (record.k === '記事' ? record.u : '');
    return record;
  }
  function readStore(key) { try { var data = JSON.parse(localStorage.getItem(key) || '[]'); return Array.isArray(data) ? data.map(clean).filter(Boolean).slice(0, 200) : []; } catch (e) { return []; } }
  function writeStore(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch (e) { storageOK = false; return false; } }
  function toast(message) { $('toast').textContent = message; $('toast').classList.add('visible'); clearTimeout(toastTimer); toastTimer = setTimeout(function () { $('toast').classList.remove('visible'); }, 3200); }
  function merge(items) {
    if (!Array.isArray(items)) return;
    items.forEach(function (raw) {
      var item = clean(raw); if (!item) return;
      var prev = byURL[item.u];
      if (prev) {
        if (!item.img) item.img = prev.img;
        if (item.a === 'unspecified') item.a = prev.a;
        if (!item.group) item.group = prev.group;
        if (!item.summary) item.summary = prev.summary;
        if (!item.series && prev.series) item.series = prev.series;
        item.aliases = item.aliases.concat(prev.aliases || []).filter(function (alias, index, all) { return all.indexOf(alias) === index; }).slice(0, 30);
        item.text = searchable(item.t + ' ' + item.tags.join(' ') + ' ' + item.aliases.join(' '));
      }
      if (articleImages[item.u]) item.img = articleImages[item.u];
      byURL[item.u] = item;
    });
    catalog = Object.keys(byURL).map(function (url) { return byURL[url]; });
    searchByGroup = Object.create(null);
    catalog.forEach(function (item) { var key = item.group || item.u; searchByGroup[key] = (searchByGroup[key] || '') + ' ' + item.text; });
  }
  function fetchText(url) {
    var controller = new AbortController(), timeout = setTimeout(function () { controller.abort(); }, 12000);
    return fetch(url, { signal: controller.signal }).then(function (r) { if (!r.ok) throw new Error('fetch'); return r.text(); }).finally(function () { clearTimeout(timeout); });
  }
  function classify(title, tags) {
    var text = tags.join(' '), pro = /医療従事者|医療者|医師向け|(?:初期)?研修医|医向け/.test(text), general = /一般向け|一般の方|一般読者|一般・|一般$/.test(text);
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
    state.series = Object.prototype.hasOwnProperty.call(seriesLabels, params.get('series')) ? params.get('series') : '';
    $('site-search').value = state.q; $('hero-q').value = state.q; $('sort-order').value = state.sort;
  }
  function updateURL(push) {
    var url = new URL(location.href);
    ['q', 'audience', 'kind', 'topic', 'sort', 'series'].forEach(function (key) { var value = state[key]; if (value && value !== 'all' && value !== 'recommended') url.searchParams.set(key, value); else url.searchParams.delete(key); });
    if (url.href !== location.href) history[push ? 'pushState' : 'replaceState']({}, '', url);
  }
  function art(item) {
    var cls = { 'ツール': 'kind-tool', 'スライド': 'kind-slides', '動画': 'kind-video' }[item.k] || '';
    var topic = Object.keys(topicRules).filter(function (x) { return topicRules[x].test(item.text); })[0] || '医療と健康';
    return '<div class="media-art ' + cls + '" aria-hidden="true"><svg viewBox="0 0 24 24">' + paths[item.k] + '</svg><span class="art-title">' + escapeHTML(topic) + '</span></div>';
  }
  function saveMarkup(item) {
    var isSaved = saved.some(function (x) { return x.u === item.u; });
    return '<button type="button" class="save-button" data-save="' + escapeHTML(item.u) + '" aria-pressed="' + isSaved + '" aria-label="' + escapeHTML((isSaved ? '保存を解除：' : 'あとで読むに保存：') + item.k + '：' + item.t) + '">' + bookmark + '</button>';
  }
  function effectiveAudience(item) {
    var source = item.group && byURL[item.group];
    return item.a === 'unspecified' && source && source.k === '記事' ? source.a : item.a;
  }
  function seriesFor(item) {
    // シリーズ名と番号が明記された記事のみを正本とし、その記事URLで関連する形式へ引き継ぐ。
    var source = item.k === '記事' ? item : item.group && byURL[item.group];
    if (!source || source.k !== '記事') return null;
    if (source.series) return { id: source.series.id, number: source.series.number, article: source };
    var title = decodeTitle(source.t).normalize('NFKC'), match = title.match(/医師が採点するアンチエイジング\s*第\s*(\d{1,3})\s*回/);
    if (match && Number(match[1]) > 0) return { id: 'anti-aging', number: Number(match[1]), article: source };
    match = title.match(/【からだの不思議\s*#\s*(\d{1,3})\s*】/);
    return match && Number(match[1]) > 0 ? { id: 'body-mysteries', number: Number(match[1]), article: source } : null;
  }
  function seriesEntries(id) {
    return catalog.filter(function (item) { var episode = seriesFor(item); return item.k === '記事' && episode && episode.id === id; }).map(function (item) { return seriesFor(item); }).sort(function (a, b) { return a.number - b.number || a.article.u.localeCompare(b.article.u); });
  }
  function seriesNext(item) {
    var episode = seriesFor(item); if (!episode) return '';
    var next = seriesEntries(episode.id).find(function (entry) { return entry.number === episode.number + 1; });
    return next ? '<a class="series-next" data-track href="' + escapeHTML(next.article.u) + '">次へ：第' + next.number + '回 <span aria-hidden="true">→</span></a>' : '';
  }
  function episodeMarkup(item) {
    var episode = seriesFor(item);
    return episode ? '<span class="series-episode">' + escapeHTML(seriesLabels[episode.id]) + ' 第' + episode.number + '回</span>' : '';
  }
  function summaryMarkup(item) { return item.summary ? '<p class="card-summary">' + escapeHTML(item.summary) + '</p>' : ''; }
  function card(item) {
    var image = item.img ? '<img src="' + escapeHTML(item.img) + '" alt="" loading="lazy" decoding="async" data-fallback-url="' + escapeHTML(item.u) + '">' : art(item);
    var note = item.d ? '<time datetime="' + item.d + '">' + item.d.replace(/-/g, '.') + '</time>' : '<span class="record-note">' + (item.k === 'ツール' ? '診断支援ツール' : '公開コンテンツ') + '</span>';
    var reader = effectiveAudience(item);
    return '<article class="content-card" data-reader="' + reader + '"><a class="card-link" data-track href="' + escapeHTML(item.u) + '"><div class="card-media">' + image + '<span class="kind-label">' + item.k + '</span></div><div class="card-body"><div class="card-category"><span>' + audienceLabels[reader] + '</span>' + (item.pages ? '<span>' + item.pages + '枚</span>' : '') + '</div>' + episodeMarkup(item) + '<h3>' + escapeHTML(item.t) + '</h3>' + summaryMarkup(item) + '</div></a><div class="card-footer">' + note + saveMarkup(item) + '</div>' + seriesNext(item) + '</article>';
  }
  function topicCard(topic) {
    var item = topic.primary, preview = topic.members.find(function (member) { return member.img; }) || item;
    var image = preview.img ? '<img src="' + escapeHTML(preview.img) + '" alt="" loading="lazy" decoding="async" data-fallback-url="' + escapeHTML(item.u) + '">' : art(item);
    var formats = topic.members.map(function (member) {
      var label = { '記事': '記事を読む', '図解': '図解を見る', '動画': '動画を見る', 'スライド': 'スライドを見る', 'ツール': 'ツールを使う' }[member.k];
      return '<div class="format-option"><a class="format-link" data-track href="' + escapeHTML(member.u) + '" aria-label="' + escapeHTML(label + '：' + member.t) + '">' + label + (member.pages ? '（' + member.pages + '枚）' : '') + ' <span aria-hidden="true">↗</span></a>' + saveMarkup(member) + '</div>';
    }).join('');
    var note = item.d ? '<span class="record-note">' + (item.k === '記事' ? '記事公開 ' : item.k + '公開 ') + '<time datetime="' + item.d + '">' + item.d.replace(/-/g, '.') + '</time></span>' : '<span class="record-note">公開コンテンツ</span>';
    var formatCount = topic.members.map(function (member) { return member.k; }).filter(function (kind, index, all) { return all.indexOf(kind) === index; }).length;
    return '<article class="content-card topic-card" data-reader="' + topic.a + '" data-group="' + escapeHTML(topic.key) + '"><a class="card-link" data-track href="' + escapeHTML(item.u) + '"><div class="card-media">' + image + '<span class="kind-label">' + (formatCount > 1 ? formatCount + 'つの形式' : item.k) + '</span></div><div class="card-body"><div class="card-category"><span>' + audienceLabels[topic.a] + '</span></div>' + episodeMarkup(item) + '<h3>' + escapeHTML(item.t) + '</h3>' + summaryMarkup(item) + '</div></a><div class="topic-formats" aria-label="このテーマのコンテンツ">' + formats + '</div><div class="card-footer">' + note + '</div>' + seriesNext(item) + '</article>';
  }
  function grouped(items) {
    var groups = Object.create(null);
    items.forEach(function (item) { var key = item.group || item.u; if (!groups[key]) groups[key] = []; groups[key].push(item); });
    return Object.keys(groups).map(function (key) {
      var members = groups[key].sort(function (a, b) { return kinds.indexOf(a.k) - kinds.indexOf(b.k) || a.u.localeCompare(b.u); });
      var primary = members.find(function (item) { return item.k === '記事'; }) || members[0];
      var readers = members.map(effectiveAudience).filter(function (reader, index, all) { return all.indexOf(reader) === index; });
      var audience = readers.length === 1 ? readers[0] : readers.indexOf('both') >= 0 || readers.indexOf('general') >= 0 && readers.indexOf('professional') >= 0 ? 'both' : effectiveAudience(primary);
      return { key: key, primary: primary, members: members, t: primary.t, d: primary.d, a: audience, text: members.map(function (item) { return item.text; }).join(' ') };
    });
  }
  function results() {
    var terms = normalized(state.q).split(' ').filter(Boolean);
    var candidates = catalog.filter(function (item) {
      var reader = effectiveAudience(item), episode = state.series && seriesFor(item);
      return (state.audience === 'all' || reader === state.audience || reader === 'both') && (state.kind === 'all' || item.k === state.kind) && (!state.series || episode && episode.id === state.series);
    });
    var list = (state.kind === 'all' ? grouped(candidates) : candidates).filter(function (item) {
      var text = state.kind === 'all' ? item.text : searchByGroup[item.group || item.u] || item.text;
      return (!state.topic || topicRules[state.topic].test(text)) && terms.every(function (term) { return matchesTerm(text, term); });
    });
    list.sort(state.sort === 'title' ? function (a, b) { return a.t.localeCompare(b.t, 'ja'); } : state.series && state.sort === 'recommended' ? function (a, b) { return seriesFor(a.primary || a).number - seriesFor(b.primary || b).number || a.t.localeCompare(b.t, 'ja'); } : function (a, b) { return b.d.localeCompare(a.d) || a.t.localeCompare(b.t, 'ja'); });
    if (state.sort === 'recommended' && state.kind === 'all' && !state.series && !state.q && !state.topic && state.audience === 'all') {
      // 最初の一段に両方の読者と診断支援ツールへの入口を置く。重複は記事URLでのみまとめる。
      var featured = [], remaining = list.slice();
      [['記事', 'general'], ['記事', 'professional'], ['ツール', 'professional']].forEach(function (choice) {
        var index = remaining.findIndex(function (topic) { return topic.primary.k === choice[0] && (topic.a === choice[1] || topic.a === 'both') && (choice[0] !== 'ツール' || /頭痛/.test(topic.t)); });
        if (index >= 0) featured.push(remaining.splice(index, 1)[0]);
      });
      list = featured.concat(remaining);
    }
    return list;
  }
  function renderSeries() {
    var nav = $('series-navigation'); if (!nav) return;
    nav.hidden = !state.series;
    if (!state.series) { nav.innerHTML = ''; return; }
    var entries = seriesEntries(state.series), first = entries.find(function (entry) { return entry.number === 1; });
    nav.innerHTML = '<div class="series-heading"><span>回の順に学ぶ</span><strong>' + escapeHTML(seriesLabels[state.series]) + '</strong></div><div class="series-actions">' + (first ? '<a class="series-start" data-track href="' + escapeHTML(first.article.u) + '">第1回から読む <span aria-hidden="true">↗</span></a>' : '') + '<button class="series-clear" type="button" data-clear-series>シリーズの絞り込みを解除</button></div><p class="series-note">記事に明記された回番号で並べます。表示順を変更するときは「表示順」から選べます。</p>';
  }
  function render() {
    if (!loaded) return;
    var list = results();
    $('content-grid').innerHTML = list.slice(0, limit).map(state.kind === 'all' ? topicCard : card).join('');
    $('content-grid').setAttribute('aria-busy', 'false');
    var unit = state.kind === 'all' ? 'テーマ' : '件', count = state.kind === 'all' ? '（' + list.reduce(function (total, topic) { return total + topic.members.length; }, 0).toLocaleString('ja-JP') + 'コンテンツ）' : '';
    $('result-status').textContent = list.length.toLocaleString('ja-JP') + unit + count + (state.q ? '「' + state.q + '」' : '') + ' / ' + Math.min(limit, list.length) + unit + 'を表示';
    $('empty-state').hidden = list.length !== 0;
    $('load-more').hidden = list.length <= limit;
    $('fulltext-link').href = 'https://blog.ichisouzo-lab.com/search?q=' + encodeURIComponent(state.q || state.topic);
    $('reset-filters').hidden = !state.q && !state.topic && !state.series && state.audience === 'all' && state.kind === 'all';
    [['audience-filters', 'audience'], ['kind-filters', 'kind'], ['topic-filters', 'topic']].forEach(function (pair) {
      $(pair[0]).querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset[pair[1]] === state[pair[1]])); });
    });
    bindImages($('content-grid'));
    renderSeries();
  }
  function bindImages(root) {
    // 図解は thumbs/ の軽量版（16:9のWebP）を使う。原寸PNG（1枚約2MB）へは切り替えない。
    root.querySelectorAll('img[data-fallback-url]').forEach(function (img) {
      function fallbackArt() {
        var item = byURL[img.dataset.fallbackUrl];
        if (item) { var box = document.createElement('div'); box.innerHTML = art(item); img.replaceWith(box.firstChild); }
        else img.hidden = true;
      }
      function checkPlaceholder() {
        // YouTubeの小さな灰色代替画像はHTTP 200でもサムネイルとして表示しない。
        if (img.src.indexOf('https://i.ytimg.com/') === 0 && /\/hqdefault\.jpg$/.test(img.src) && img.naturalWidth <= 120 && img.naturalHeight <= 90) fallbackArt();
      }
      img.addEventListener('load', checkPlaceholder);
      img.addEventListener('error', fallbackArt);
      if (img.complete) { if (img.naturalWidth) checkPlaceholder(); else img.dispatchEvent(new Event('error')); }
    });
  }
  function change(push) { limit = pageSize; updateURL(push); render(); }
  function savedUI() {
    $('saved-count').textContent = saved.length;
    $('open-collection').setAttribute('aria-label', 'あとで読む：' + saved.length + '件');
    document.querySelectorAll('[data-save]').forEach(function (button) {
      var isSaved = saved.some(function (x) { return x.u === button.dataset.save; });
      var item = byURL[button.dataset.save] || saved.find(function (x) { return x.u === button.dataset.save; }) || recent.find(function (x) { return x.u === button.dataset.save; });
      button.setAttribute('aria-pressed', String(isSaved));
      if (item) button.setAttribute('aria-label', (isSaved ? '保存を解除：' : 'あとで読むに保存：') + item.k + '：' + item.t);
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
    var seriesLink = event.target.closest('[data-series-id]');
    if (seriesLink && Object.prototype.hasOwnProperty.call(seriesLabels, seriesLink.dataset.seriesId)) {
      event.preventDefault(); state = { q: '', audience: 'all', kind: 'all', topic: '', sort: 'recommended', series: seriesLink.dataset.seriesId };
      $('site-search').value = ''; $('sort-order').value = state.sort; change(true); $('library').scrollIntoView({ block: 'start', behavior: 'smooth' });
    }
    var series = event.target.closest('[data-series]'); if (series) { state = { q: series.dataset.series, audience: 'all', kind: 'all', topic: '', sort: 'recommended', series: '' }; $('site-search').value = state.q; $('sort-order').value = state.sort; change(true); }
    if (event.target.closest('[data-clear-series]')) { state.series = ''; change(true); }
    var kind = event.target.closest('[data-kind-link]'); if (kind) { state.kind = kind.dataset.kindLink; state.q = ''; state.topic = ''; state.series = ''; $('site-search').value = ''; change(true); }
  });
  document.addEventListener('auxclick', function (event) { var link = event.target.closest('a[data-track]'); if (link && event.button === 1) track(link.href); });
  [['audience-filters', 'audience'], ['kind-filters', 'kind'], ['topic-filters', 'topic']].forEach(function (pair) { $(pair[0]).addEventListener('click', function (event) { var b = event.target.closest('button'); if (!b) return; var value = b.dataset[pair[1]]; state[pair[1]] = pair[1] === 'topic' && state.topic === value ? '' : value; change(true); }); });
  $('site-search').addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(function () { state.q = $('site-search').value.slice(0, 200); change(false); }, 160); });
  $('search-form').addEventListener('submit', function (event) { event.preventDefault(); clearTimeout(timer); state.q = $('site-search').value.slice(0, 200); change(true); $('result-status').scrollIntoView({ block: 'start', behavior: 'smooth' }); });
  // ヒーローの検索窓と症状の候補は、新しい検索として下の一覧に結果を出す。JavaScriptが無い場合は ?q= のリンクとして働く。
  function searchFromHero(query) {
    clearTimeout(timer);
    state = { q: query.slice(0, 200), audience: 'all', kind: 'all', topic: '', sort: 'recommended', series: '' };
    $('site-search').value = state.q; $('hero-q').value = state.q; $('sort-order').value = state.sort;
    change(true); $('result-status').scrollIntoView({ block: 'start', behavior: 'smooth' });
  }
  $('hero-search').addEventListener('submit', function (event) { event.preventDefault(); searchFromHero($('hero-q').value.trim()); });
  $('hero-chips').addEventListener('click', function (event) { var chip = event.target.closest('[data-query]'); if (!chip || event.ctrlKey || event.metaKey || event.shiftKey) return; event.preventDefault(); searchFromHero(chip.dataset.query); });
  $('sort-order').addEventListener('change', function () { state.sort = this.value; change(true); });
  $('reset-filters').addEventListener('click', function () { state = { q: '', audience: 'all', kind: 'all', topic: '', sort: 'recommended', series: '' }; $('site-search').value = ''; $('sort-order').value = 'recommended'; change(true); });
  $('load-more').addEventListener('click', function () { var old = limit; limit += pageSize; render(); var next = $('content-grid').children[old]; if (next) next.querySelector('a').focus({ preventScroll: true }); });
  window.addEventListener('popstate', function () { readURL(); limit = pageSize; render(); });
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
      // 軽量サムネイルは日次更新で作る。未作成の新着は代替図柄で表示する。
      if (kind === '図解') record.img = 'thumbs/' + item.slug + '.webp';
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
  function heroFallback() { document.querySelector('.hero-image').innerHTML = art({ k: '図解', text: '運動' }); }
  heroImg.addEventListener('error', heroFallback);
  if (heroImg.complete && !heroImg.naturalWidth) heroFallback();
  // カタログは6時間ごとに更新する（GitHubの定期実行は数時間遅れることがある）。
  // 更新から12時間以内は、ブログRSS（約1.6MB）などを表示のたびに取得しない。
  var freshFor = 12 * 60 * 60 * 1000;
  var catalogUpdated = fetchText('catalog-meta.json').then(function (s) { return Date.parse(JSON.parse(s).updated) || 0; }).catch(function () { return 0; });
  function scheduleRefresh(updated) {
    var age = Date.now() - updated;
    if (!loaded) { refreshPublic(); return; }
    if (age >= 0 && age < freshFor) {
      $('catalog-status').textContent = '公開ブログ・資料一覧を' + new Date(updated).toLocaleString('ja-JP', { timeZone: 'Asia/Tokyo', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit' }) + 'に反映したカタログです。読者の絞り込みは対象が明記された情報のみ。';
      return;
    }
    (window.requestIdleCallback || function (callback) { return setTimeout(callback, 1200); })(function () { refreshPublic(); }, { timeout: 3000 });
  }
  fetchText('search-index.json').then(function (s) { var data = JSON.parse(s); if (!Array.isArray(data)) throw new Error('catalog'); merge(data); loaded = true; render(); }).catch(function () { $('catalog-status').textContent = '公開サイトから検索情報を取得しています…'; }).finally(function () { catalogUpdated.then(scheduleRefresh); });
})();
