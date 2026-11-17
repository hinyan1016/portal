(function(){
  var FEED_BASE = 'https://ichisouzo-lab.com/';
  var FEED_URL = FEED_BASE + 'blog-home-feed.json';
  var INDEX_URL = FEED_BASE + 'search-index.json';
  var ENTRY_RE = /^\/entry\/(\d{4}\/\d{2}\/\d{2}\/\d{6})$/;
  var THUMB_RE = /^thumbs\/[A-Za-z0-9\/_.-]+\.webp$/;
  var YT_ID_RE = /^[A-Za-z0-9_-]{11}$/;
  var SLIDE_SLUG_RE = /^[A-Za-z0-9_-]+$/;
  var ALLOWED_LINK_RE = /^https:\/\/(?:blog|tools|check)\.ichisouzo-lab\.com\/|^https:\/\/ichisouzo-lab\.com\/|^https:\/\/www\.youtube\.com\/watch\?v=[A-Za-z0-9_-]{11}$/;
  var ALLOWED_MEDIA_OPEN_RE = /^https:\/\/(?:www\.youtube\.com\/watch\?v=[A-Za-z0-9_-]{11}|tools\.ichisouzo-lab\.com\/slides\/[A-Za-z0-9_-]+\/)$/;

  var EXCLUDE_WORDS = [
    '宗教', '世代区分', 'イシガメ', 'ギャンブル', '沼・池・湖',
    '観光ガイド', 'モデルコース', '米子', 'ガチャ', '聖地',
    'パチンコ', '競馬', '旅・地域', 'ポケモン', 'アニメ', 'グルメ', '温泉',
    '魚の分類', '日本の世代'
  ];
  var CLINICAL_MED_CATS = {
    '医学情報': 1, '脳神経内科': 1, 'てんかん': 1, '脳卒中': 1, '認知症': 1,
    '頭痛': 1, 'パーキンソン病': 1, '内科': 1, '感染症': 1, '生活習慣病': 1,
    '糖尿': 1, '薬': 1, '栄養': 1, 'アンチエイジング': 1, '初期研修医': 1,
    '医学教育': 1, '医療安全': 1, 'ガイドライン解説': 1, '20年の変遷シリーズ': 1,
    'その症状大丈夫': 1, 'セルフチェック': 1
  };
  var MUST_THUMBS = {
    '2026/05/06/204047': FEED_BASE + 'thumbs/articles/20260506-204047.webp',
    '2026/10/13/122059': FEED_BASE + 'thumbs/irae-myositis.webp'
  };

  var feedPromise = null;
  var indexPromise = null;

  function isIndex(){
    return document.body && document.body.classList.contains('page-index');
  }

  function isTopPage(){
    if(!isIndex() || location.pathname !== '/') return false;
    return Array.from(new URLSearchParams(location.search).keys()).every(function(key){
      return /^utm_/.test(key) || key === 'gclid' || key === 'fbclid';
    });
  }

  function isMedicalEntry(title, cats){
    var hay = (title || '') + ' ' + (cats || []).join(' ');
    if(EXCLUDE_WORDS.some(function(w){ return hay.indexOf(w) !== -1; })) return false;
    return (cats || []).some(function(c){ return !!CLINICAL_MED_CATS[c]; });
  }

  function getFeed(){
    if(!window.fetch) return Promise.resolve(null);
    if(!feedPromise){
      feedPromise = fetch(FEED_URL, {credentials: 'omit'}).then(function(r){
        return r.ok ? r.json() : null;
      }).catch(function(){ return null; });
    }
    return feedPromise;
  }

  function getSearchIndex(){
    if(!window.fetch) return Promise.resolve(null);
    if(!indexPromise){
      indexPromise = fetch(INDEX_URL, {credentials: 'omit'}).then(function(r){
        return r.ok ? r.json() : null;
      }).catch(function(){
        indexPromise = null;
        return null;
      });
    }
    return indexPromise;
  }

  function createAtlasSvg(){
    var ns = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 160 90');
    svg.setAttribute('width', '160');
    svg.setAttribute('height', '90');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');

    var defs = document.createElementNS(ns, 'defs');
    var grad = document.createElementNS(ns, 'linearGradient');
    grad.setAttribute('id', 'ichAtlasBg');
    grad.setAttribute('x1', '0%');
    grad.setAttribute('y1', '0%');
    grad.setAttribute('x2', '100%');
    grad.setAttribute('y2', '100%');
    var s1 = document.createElementNS(ns, 'stop');
    s1.setAttribute('offset', '0%');
    s1.setAttribute('stop-color', '#102a43');
    var s2 = document.createElementNS(ns, 'stop');
    s2.setAttribute('offset', '100%');
    s2.setAttribute('stop-color', '#1b4f72');
    grad.appendChild(s1);
    grad.appendChild(s2);
    defs.appendChild(grad);
    svg.appendChild(defs);

    var bg = document.createElementNS(ns, 'rect');
    bg.setAttribute('width', '160');
    bg.setAttribute('height', '90');
    bg.setAttribute('fill', 'url(#ichAtlasBg)');
    svg.appendChild(bg);

    var slice = document.createElementNS(ns, 'ellipse');
    slice.setAttribute('cx', '80');
    slice.setAttribute('cy', '45');
    slice.setAttribute('rx', '34');
    slice.setAttribute('ry', '36');
    slice.setAttribute('fill', '#173d5c');
    slice.setAttribute('stroke', '#4888b0');
    slice.setAttribute('stroke-width', '2');
    svg.appendChild(slice);

    var paths = [
      {d: 'M80 12 C68 18, 66 32, 78 44', c: '#38bdf8', w: '3'},
      {d: 'M80 12 C92 18, 94 32, 82 44', c: '#38bdf8', w: '3'},
      {d: 'M48 42 C56 32, 68 38, 78 46 C66 56, 54 58, 48 42', c: '#f59e0b', w: '2.5'},
      {d: 'M112 42 C104 32, 92 38, 82 46 C94 56, 106 58, 112 42', c: '#f59e0b', w: '2.5'},
      {d: 'M60 68 C70 60, 90 60, 100 68', c: '#2dd4bf', w: '3'},
      {d: 'M80 10 L80 80', c: 'rgba(255,255,255,0.28)', w: '1.2'}
    ];
    paths.forEach(function(item){
      var p = document.createElementNS(ns, 'path');
      p.setAttribute('d', item.d);
      p.setAttribute('fill', 'none');
      p.setAttribute('stroke', item.c);
      p.setAttribute('stroke-width', item.w);
      p.setAttribute('stroke-linecap', 'round');
      svg.appendChild(p);
    });
    return svg;
  }

  // (4a) Add 16:9 thumbnails to the 3 Must-Read pickup items
  function enhanceMustReadThumbs(){
    if(!isIndex()) return;
    var items = document.querySelectorAll('#ich-must-read .ich-must-item');
    Array.prototype.forEach.call(items, function(item){
      if(item.getAttribute('data-ich-s5-thumb') === '1') return;
      var href = item.getAttribute('href') || '';
      var thumbBox = document.createElement('div');
      thumbBox.className = 'ich-must-thumb';
      var matched = false;
      Object.keys(MUST_THUMBS).forEach(function(key){
        if(href.indexOf(key) !== -1){
          var img = document.createElement('img');
          img.src = MUST_THUMBS[key];
          img.alt = '';
          img.loading = 'lazy';
          thumbBox.appendChild(img);
          matched = true;
        }
      });
      if(!matched && href.indexOf('vascular-territory-atlas') !== -1){
        thumbBox.appendChild(createAtlasSvg());
        matched = true;
      }
      if(!matched) return;
      var body = document.createElement('div');
      body.className = 'ich-must-body';
      while(item.firstChild){
        body.appendChild(item.firstChild);
      }
      item.appendChild(thumbBox);
      item.appendChild(body);
      item.classList.add('has-thumb');
      item.setAttribute('data-ich-s5-thumb', '1');
    });
  }

  // (4b) Annotate #ich-disease-cats cards with live article counts from #box2 category module
  function annotateCategoryCounts(){
    if(!isIndex()) return;
    var countMap = {};
    document.querySelectorAll('#box2 .hatena-module-category a[href*="/archive/category/"]').forEach(function(a){
      var m = /\/archive\/category\/([^/?#]+)/.exec(a.getAttribute('href') || '');
      if(!m) return;
      var cat;
      try { cat = decodeURIComponent(m[1]); } catch(e){ cat = m[1]; }
      var cm = /\((\d+)\)\s*$/.exec(a.textContent || '');
      if(cat && cm) countMap[cat] = cm[1];
    });
    document.querySelectorAll('#ich-disease-cats .ich-cat-card').forEach(function(card){
      if(card.querySelector('.ich-cat-count')) return;
      var m = /\/archive\/category\/([^/?#]+)/.exec(card.getAttribute('href') || '');
      if(!m) return;
      var cat;
      try { cat = decodeURIComponent(m[1]); } catch(e){ cat = m[1]; }
      var cnt = countMap[cat];
      if(!cnt) return;
      var badge = document.createElement('span');
      badge.className = 'ich-cat-count';
      badge.textContent = cnt;
      badge.title = '公開記事 ' + cnt + '件';
      var arrow = card.querySelector('.ich-cat-arrow');
      if(arrow){
        card.insertBefore(badge, arrow);
      } else {
        card.appendChild(badge);
      }
    });
  }

  // (4c) Show cumulative site metrics in .ich-trust-bar
  function updateTrustStats(stats){
    if(!isIndex()) return;
    var prof = document.querySelector('.ich-trust-bar .ich-trust-profile');
    if(!prof) return;
    var el = document.getElementById('ich-trust-stats');
    if(!el){
      el = document.createElement('span');
      el.id = 'ich-trust-stats';
      el.className = 'ich-trust-stats';
      prof.appendChild(el);
    }
    var st = stats && typeof stats === 'object' ? stats : {};
    var a = typeof st.articles === 'number' ? st.articles : 1400;
    var v = typeof st.videos === 'number' ? st.videos : 281;
    var s = typeof st.slides === 'number' ? st.slides : 277;
    var t = typeof st.tools === 'number' ? st.tools : 80;
    function fmt(n){ return Number(n).toLocaleString('ja-JP'); }
    var parts = [
      {cls: 'ich-ib', text: '公開実績：'},
      {cls: 'ich-ib', text: '記事 ' + fmt(a) + '本'},
      {sep: '・'},
      {cls: 'ich-ib', text: '動画 ' + fmt(v) + '本'},
      {sep: '・'},
      {cls: 'ich-ib', text: 'スライド ' + fmt(s) + '組'},
      {sep: '・'},
      {cls: 'ich-ib', text: '診断ツール ' + fmt(t) + '種'}
    ];
    el.replaceChildren();
    parts.forEach(function(p){
      if(p.sep){
        el.appendChild(document.createTextNode(p.sep));
      } else {
        var sp = document.createElement('span');
        sp.className = p.cls;
        sp.textContent = p.text;
        el.appendChild(sp);
      }
    });
  }

  function openMediaUrl(url){
    if(!ALLOWED_MEDIA_OPEN_RE.test(url)) return;
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  function populateCardMediaButtons(catBox, entryId, mediaMap){
    if(!catBox || !entryId || !mediaMap) return;
    var info = mediaMap[entryId];
    if(!info || typeof info !== 'object') return;
    if(catBox.querySelector('button.ich-media-flag[data-ich-s5-btn="1"]')) return;
    catBox.querySelectorAll('.ich-media-flag').forEach(function(oldEl){ oldEl.remove(); });
    if(typeof info.v === 'string' && YT_ID_RE.test(info.v)){
      var vUrl = 'https://www.youtube.com/watch?v=' + info.v;
      var vBtn = document.createElement('button');
      vBtn.type = 'button';
      vBtn.className = 'ich-media-flag ich-media-video';
      vBtn.setAttribute('data-ich-s5-btn', '1');
      vBtn.setAttribute('aria-label', 'YouTube解説動画を開く');
      vBtn.textContent = '▶ 動画';
      vBtn.addEventListener('click', function(e){
        e.preventDefault();
        e.stopPropagation();
        openMediaUrl(vUrl);
      });
      catBox.appendChild(vBtn);
    }
    if(typeof info.s === 'string' && SLIDE_SLUG_RE.test(info.s)){
      var sUrl = 'https://tools.ichisouzo-lab.com/slides/' + info.s + '/';
      var pCount = typeof info.p === 'number' && info.p > 0 ? info.p : 0;
      var sBtn = document.createElement('button');
      sBtn.type = 'button';
      sBtn.className = 'ich-media-flag ich-media-slide';
      sBtn.setAttribute('data-ich-s5-btn', '1');
      sBtn.setAttribute('aria-label', (pCount ? pCount + '枚の' : '') + 'スライドビューアーを開く');
      sBtn.textContent = pCount ? ('スライド ' + pCount + '枚') : 'スライド';
      sBtn.addEventListener('click', function(e){
        e.preventDefault();
        e.stopPropagation();
        openMediaUrl(sUrl);
      });
      catBox.appendChild(sBtn);
    }
  }

  // (2a) Upgrade existing cards' .ich-media-flag into interactive video & slide buttons
  function upgradeExistingMediaButtons(mediaMap){
    if(!isIndex() || !mediaMap) return;
    document.querySelectorAll('.page-index .archive-entry').forEach(function(card){
      var link = card.querySelector('.entry-title-link, .entry-thumb-link');
      var catBox = card.querySelector('.categories');
      if(!link || !catBox) return;
      var m = ENTRY_RE.exec(link.pathname);
      if(!m) return;
      populateCardMediaButtons(catBox, m[1], mediaMap);
    });
  }

  // (2b) Insert "スライド・動画で学ぶ最新解説" showcase card grid after .pager on top page
  function renderMediaShowcase(showcase, base){
    if(!isTopPage() || !Array.isArray(showcase) || !showcase.length) return;
    if(document.getElementById('ich-media-showcase')) return;
    var pager = document.querySelector('#main .pager');
    if(!pager || !pager.parentNode) return;

    var sec = document.createElement('section');
    sec.id = 'ich-media-showcase';
    sec.setAttribute('aria-labelledby', 'ich-media-showcase-title');

    var head = document.createElement('div');
    head.className = 'ich-sc-head';
    var h3 = document.createElement('h3');
    h3.id = 'ich-media-showcase-title';
    h3.textContent = 'スライド・動画で学ぶ最新解説';
    var more = document.createElement('a');
    more.className = 'ich-sc-more';
    more.href = FEED_BASE + '#sec-slides';
    more.textContent = '一覧を見る →';
    head.appendChild(h3);
    head.appendChild(more);
    sec.appendChild(head);

    var grid = document.createElement('div');
    grid.className = 'ich-sc-grid';

    showcase.slice(0, 4).forEach(function(item){
      if(!item || typeof item.id !== 'string' || !SLIDE_SLUG_RE.test(item.s || '')) return;
      var slideUrl = 'https://tools.ichisouzo-lab.com/slides/' + item.s + '/';
      var coverUrl = slideUrl + 'card.webp';
      var articleUrl = 'https://blog.ichisouzo-lab.com/entry/' + item.id;
      var pages = typeof item.p === 'number' && item.p > 0 ? item.p : 0;

      var card = document.createElement('article');
      card.className = 'ich-sc-card';

      var cover = document.createElement('a');
      cover.className = 'ich-sc-cover';
      cover.href = slideUrl;
      cover.target = '_blank';
      cover.rel = 'noopener noreferrer';
      cover.setAttribute('aria-label', item.t + ' のスライドを見る');
      var img = document.createElement('img');
      img.src = coverUrl;
      img.alt = '';
      img.loading = 'lazy';
      if(typeof item.img === 'string' && THUMB_RE.test(item.img) && item.img.indexOf('..') === -1){
        img.addEventListener('error', function onErr(){
          img.removeEventListener('error', onErr);
          img.src = (base || FEED_BASE) + item.img;
        });
      }
      cover.appendChild(img);
      if(pages){
        var pg = document.createElement('span');
        pg.className = 'ich-sc-pages';
        pg.textContent = '全' + pages + '枚';
        cover.appendChild(pg);
      }
      card.appendChild(cover);

      var body = document.createElement('div');
      body.className = 'ich-sc-body';

      var meta = document.createElement('div');
      meta.className = 'ich-sc-meta';
      if(item.aud){
        var audSpan = document.createElement('span');
        audSpan.className = 'ich-sc-aud ' + (item.aud === '一般向け' ? 'is-gen' : 'is-doc');
        audSpan.textContent = item.aud;
        meta.appendChild(audSpan);
      }
      if(item.d){
        var tm = document.createElement('time');
        tm.dateTime = item.d;
        tm.textContent = item.d;
        meta.appendChild(tm);
      }
      body.appendChild(meta);

      var pTitle = document.createElement('p');
      pTitle.className = 'ich-sc-title';
      var aTitle = document.createElement('a');
      aTitle.href = articleUrl;
      aTitle.textContent = item.t;
      pTitle.appendChild(aTitle);
      body.appendChild(pTitle);

      var actions = document.createElement('div');
      actions.className = 'ich-sc-actions';
      var sLink = document.createElement('a');
      sLink.className = 'ich-sc-btn ich-sc-btn-slide';
      sLink.href = slideUrl;
      sLink.target = '_blank';
      sLink.rel = 'noopener noreferrer';
      sLink.textContent = pages ? ('スライド（' + pages + '枚）') : 'スライドを見る';
      actions.appendChild(sLink);

      if(typeof item.v === 'string' && YT_ID_RE.test(item.v)){
        var vLink = document.createElement('a');
        vLink.className = 'ich-sc-btn ich-sc-btn-video';
        vLink.href = 'https://www.youtube.com/watch?v=' + item.v;
        vLink.target = '_blank';
        vLink.rel = 'noopener noreferrer';
        vLink.textContent = '▶ 動画で見る';
        actions.appendChild(vLink);
      }
      body.appendChild(actions);
      card.appendChild(body);
      grid.appendChild(card);
    });

    if(!grid.children.length) return;
    sec.appendChild(grid);
    pager.parentNode.insertBefore(sec, pager.nextSibling);
  }

  function extractCssUrl(bgValue){
    var m = /url\(["']?([^"')]+)["']?\)/.exec(bgValue || '');
    return m ? m[1] : '';
  }

  function collectServerCards(){
    var rows = [];
    document.querySelectorAll('.page-index .archive-entries > .archive-entry').forEach(function(card){
      var link = card.querySelector('.entry-title-link');
      if(!link) return;
      var m = ENTRY_RE.exec(link.pathname);
      if(!m) return;
      var id = m[1];
      var t = link.textContent.trim();
      var tm = card.querySelector('time');
      var d = (tm && (tm.getAttribute('datetime') || tm.textContent) || '').trim().slice(0, 10);
      var cats = Array.prototype.map.call(card.querySelectorAll('.categories > a'), function(a){
        return a.textContent.trim();
      }).filter(Boolean);
      var thumb = card.querySelector('.entry-thumb');
      var bgUrl = thumb ? extractCssUrl(thumb.style.backgroundImage) : '';
      rows.push({
        id: id,
        t: t,
        d: d,
        cats: cats,
        img: '',
        domBgUrl: bgUrl,
        isPortalDom: !!(thumb && thumb.classList.contains('ich-thumb-portal'))
      });
    });
    return rows;
  }

  function buildArchiveCard(item, base, mediaMap){
    var sec = document.createElement('section');
    sec.className = 'archive-entry autopagerize_page_element';
    sec.setAttribute('data-ich-s5-card', '1');
    var entryHref = 'https://blog.ichisouzo-lab.com/entry/' + item.id;

    var head = document.createElement('div');
    head.className = 'archive-entry-header';

    if(/^\d{4}-\d{2}-\d{2}$/.test(item.d || '')){
      var pts = item.d.split('-');
      var dtDiv = document.createElement('div');
      dtDiv.className = 'date archive-date';
      var dtA = document.createElement('a');
      dtA.href = 'https://blog.ichisouzo-lab.com/archive/' + pts[0] + '/' + pts[1] + '/' + pts[2];
      dtA.rel = 'nofollow';
      var tm = document.createElement('time');
      tm.dateTime = item.d;
      tm.title = item.d;
      var spY = document.createElement('span'); spY.className = 'date-year'; spY.textContent = pts[0];
      var spH1 = document.createElement('span'); spH1.className = 'hyphen'; spH1.textContent = '-';
      var spM = document.createElement('span'); spM.className = 'date-month'; spM.textContent = pts[1];
      var spH2 = document.createElement('span'); spH2.className = 'hyphen'; spH2.textContent = '-';
      var spD = document.createElement('span'); spD.className = 'date-day'; spD.textContent = pts[2];
      tm.appendChild(spY); tm.appendChild(spH1); tm.appendChild(spM); tm.appendChild(spH2); tm.appendChild(spD);
      dtA.appendChild(tm);
      dtDiv.appendChild(dtA);
      head.appendChild(dtDiv);
    }

    var h1 = document.createElement('h1');
    h1.className = 'entry-title';
    var aTitle = document.createElement('a');
    aTitle.className = 'entry-title-link';
    aTitle.href = entryHref;
    aTitle.textContent = item.t;
    h1.appendChild(aTitle);
    head.appendChild(h1);

    var catDiv = document.createElement('div');
    catDiv.className = 'categories';
    (item.cats || []).forEach(function(cat){
      var ca = document.createElement('a');
      ca.href = 'https://blog.ichisouzo-lab.com/archive/category/' + encodeURIComponent(cat);
      ca.className = 'archive-category-link category-' + String(cat).replace(/\s+/g, '-');
      ca.textContent = cat;
      catDiv.appendChild(ca);
    });
    populateCardMediaButtons(catDiv, item.id, mediaMap);

    var thumbHref = '';
    var usePortalCls = false;
    if(typeof item.img === 'string' && THUMB_RE.test(item.img) && item.img.indexOf('..') === -1){
      thumbHref = (base || FEED_BASE) + item.img;
      usePortalCls = true;
    } else if(item.domBgUrl && /^https:\/\//.test(item.domBgUrl)){
      thumbHref = item.domBgUrl;
      usePortalCls = !!item.isPortalDom;
    }

    sec.appendChild(head);
    sec.appendChild(catDiv);
    if(thumbHref){
      var tLink = document.createElement('a');
      tLink.className = 'entry-thumb-link';
      tLink.href = entryHref;
      var tDiv = document.createElement('div');
      tDiv.className = 'entry-thumb' + (usePortalCls ? ' ich-thumb-portal' : '');
      tDiv.style.backgroundImage = 'url("' + thumbHref + '")';
      tLink.appendChild(tDiv);
      sec.appendChild(tLink);
    }
    return sec;
  }

  // (1) Inline 4-tab switcher for Latest Articles on /
  function setupInlineTabs(feed, domCards){
    if(!isTopPage() || !feed || !feed.feeds) return;
    var header = document.getElementById('ich-latest-header');
    var chips = header ? header.querySelector('.ich-filter-chips') : null;
    var entriesBox = document.querySelector('#main .archive-entries');
    var pagerNext = document.querySelector('#main .pager .pager-next a');
    if(!chips || !entriesBox || chips.getAttribute('data-ich-s5-tabs') === '1') return;

    var origNextHref = pagerNext ? pagerNext.href : 'https://blog.ichisouzo-lab.com/?page=2';
    var origNextText = 'もっと記事を見る';
    var mediaMap = feed.media || {};

    var feeds = {
      all: (feed.feeds.all || []).slice(),
      doctor: (feed.feeds.doctor || []).slice(),
      general: (feed.feeds.general || []).slice(),
      media: (feed.feeds.media || []).slice()
    };

    function mergeFresh(targetList, predicate, prefixAud){
      var existing = {};
      targetList.forEach(function(it){ existing[it.id] = 1; });
      var extras = [];
      (domCards || []).forEach(function(dc){
        if(existing[dc.id] || !isMedicalEntry(dc.t, dc.cats)) return;
        if(!predicate || predicate(dc)){
          var cleanCats = dc.cats.slice();
          if(prefixAud && cleanCats.indexOf(prefixAud) === -1) cleanCats.unshift(prefixAud);
          if(cleanCats.length > 1 && cleanCats.indexOf('医学情報') !== -1){
            cleanCats = cleanCats.filter(function(c){ return c !== '医学情報'; });
          }
          extras.push({
            id: dc.id,
            t: dc.t,
            d: dc.d,
            cats: cleanCats,
            img: dc.img,
            domBgUrl: dc.domBgUrl,
            isPortalDom: dc.isPortalDom
          });
        }
      });
      if(extras.length){
        return extras.concat(targetList);
      }
      return targetList;
    }

    feeds.all = mergeFresh(feeds.all, null, null);
    feeds.doctor = mergeFresh(feeds.doctor, function(dc){
      return dc.cats.some(function(c){
        return c === '医師向け' || c === '初期研修医' || c === '医学教育' || c === 'ガイドライン解説';
      });
    }, '医師向け');
    feeds.general = mergeFresh(feeds.general, function(dc){
      return dc.cats.some(function(c){
        return c === '一般向け' || c === '患者さん向け' || c === 'その症状大丈夫';
      });
    }, '一般向け');
    feeds.media = mergeFresh(feeds.media, function(dc){
      return !!mediaMap[dc.id];
    }, null);

    var tabSpecs = [
      {key: 'all', label: '医療・新着', nextHref: origNextHref, nextText: origNextText},
      {key: 'doctor', label: '医師向け', nextHref: 'https://blog.ichisouzo-lab.com/archive/category/%E5%8C%BB%E5%B8%AB%E5%90%91%E3%81%91', nextText: '医師向けの記事一覧を見る'},
      {key: 'general', label: '一般向け', nextHref: 'https://blog.ichisouzo-lab.com/archive/category/%E4%B8%80%E8%88%AC%E5%90%91%E3%81%91', nextText: '一般向けの記事一覧を見る'},
      {key: 'media', label: '▶ 動画・スライド', nextHref: 'https://ichisouzo-lab.com/#sec-slides', nextText: '動画・スライド一覧を見る →'}
    ];

    var updates = (feed.updates || []).filter(function(row){
      return row.title && row.summary && /^https:\/\/blog\.ichisouzo-lab\.com\/entry\//.test(row.url);
    });
    if(updates.length){
      tabSpecs.splice(1, 0, {key: 'updated', label: '最近更新した記事', nextHref: FEED_BASE + 'article-updates.html', nextText: 'すべての更新を見る'});
      var heading = header.querySelector('h2');
      if(heading) heading.textContent = '新着・更新記事';
      document.body.classList.add('ich-updates-in-tabs');
    }
    chips.setAttribute('role', 'tablist');
    chips.setAttribute('aria-label', '新着記事の切り替え');
    chips.setAttribute('data-ich-s5-tabs', '1');
    chips.replaceChildren();

    entriesBox.id = entriesBox.id || 'ich-latest-tabpanel';
    entriesBox.setAttribute('role', 'tabpanel');

    var buttons = [];
    function activate(idx, moveFocus){
      var spec = tabSpecs[idx];
      if(!spec) return;
      buttons.forEach(function(btn, i){
        var active = i === idx;
        btn.classList.toggle('is-active', active);
        btn.setAttribute('aria-selected', active ? 'true' : 'false');
        btn.tabIndex = active ? 0 : -1;
      });
      entriesBox.setAttribute('aria-labelledby', buttons[idx].id);
      if(moveFocus) buttons[idx].focus();

      var list = (feeds[spec.key] || []).slice(0, 8);
      entriesBox.classList.toggle('ich-show-updates', spec.key === 'updated');
      if(spec.key === 'updated'){
        var updatesFragment = document.createDocumentFragment();
        updates.forEach(function(row){
          var card = document.createElement('article');
          card.className = 'ich-revision-card';
          var date = document.createElement('time');
          date.dateTime = row.date;
          date.textContent = row.date + ' 更新';
          var title = document.createElement('h3');
          var link = document.createElement('a');
          link.href = row.url;
          link.textContent = row.title;
          title.appendChild(link);
          var note = document.createElement('p');
          note.textContent = row.summary.split('。')[0] + (row.summary.indexOf('。') === -1 ? '' : '。');
          card.append(date, title, note);
          updatesFragment.appendChild(card);
        });
        entriesBox.replaceChildren(updatesFragment);
      } else if(list.length){
        var frag = document.createDocumentFragment();
        list.forEach(function(entry){
          frag.appendChild(buildArchiveCard(entry, feed.base || FEED_BASE, mediaMap));
        });
        entriesBox.replaceChildren(frag);
      }
      if(pagerNext){
        pagerNext.href = spec.nextHref;
        pagerNext.textContent = spec.nextText;
      }
    }

    tabSpecs.forEach(function(spec, idx){
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.id = 'ich-filter-tab-' + spec.key;
      btn.className = 'ich-filter-tab' + (idx === 0 ? ' is-active' : '');
      btn.setAttribute('role', 'tab');
      btn.setAttribute('aria-controls', entriesBox.id);
      btn.setAttribute('aria-selected', idx === 0 ? 'true' : 'false');
      btn.tabIndex = idx === 0 ? 0 : -1;
      btn.textContent = spec.label;
      btn.addEventListener('click', function(){ activate(idx, false); });
      btn.addEventListener('keydown', function(e){
        var next = -1;
        if(e.key === 'ArrowRight') next = (idx + 1) % tabSpecs.length;
        else if(e.key === 'ArrowLeft') next = (idx - 1 + tabSpecs.length) % tabSpecs.length;
        else if(e.key === 'Home') next = 0;
        else if(e.key === 'End') next = tabSpecs.length - 1;
        if(next !== -1){
          e.preventDefault();
          activate(next, true);
        }
      });
      buttons.push(btn);
      chips.appendChild(btn);
    });

    function openUpdatesAnchor(){
      if(!updates.length || !/^#(?:recent-updates(?:-title)?|ics-updates-host)$/.test(location.hash)) return false;
      activate(1, false);
      header.scrollIntoView();
      return true;
    }
    if(!openUpdatesAnchor()) activate(0, false);
    window.addEventListener('hashchange', openUpdatesAnchor);
  }

  // (3) Cross-site realtime search suggest on all pages with .ich-search
  function setupRealtimeSearch(){
    var form = document.querySelector('#top-editarea .ich-search');
    var input = document.getElementById('ich-search-query');
    if(!form || !input || form.getAttribute('data-ich-s5-search') === '1') return;
    form.setAttribute('data-ich-s5-search', '1');

    var box = document.getElementById('ich-search-suggest');
    if(!box){
      box = document.createElement('div');
      box.id = 'ich-search-suggest';
      box.className = 'ich-search-suggest';
      box.setAttribute('role', 'listbox');
      box.setAttribute('aria-label', '検索候補');
      box.hidden = true;
      form.appendChild(box);
    }
    input.placeholder = '疾患・薬剤・診断ツールを検索';
    input.setAttribute('autocomplete', 'off');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('aria-controls', box.id);

    var activeIdx = -1;
    var cachedIndex = null;

    function norm(s){
      var txt = String(s || '');
      try { txt = txt.normalize('NFKC'); } catch(e){}
      return txt.toLowerCase();
    }

    function hideBox(){
      box.hidden = true;
      input.setAttribute('aria-expanded', 'false');
      activeIdx = -1;
    }

    function focusables(){
      return Array.prototype.slice.call(box.querySelectorAll('.ich-suggest-item, .ich-suggest-all'));
    }

    function setFocus(idx){
      var els = focusables();
      els.forEach(function(el, i){ el.classList.toggle('is-focused', i === idx); });
      activeIdx = idx;
    }

    function classifyKind(item){
      var k = item.k;
      if(k === 'ツール') return {label: '診断ツール', cls: 'is-tool'};
      if(k === 'スライド') return {label: 'スライド', cls: 'is-slide'};
      if(k === '動画') return {label: '動画', cls: 'is-video'};
      var tags = item.tags || [];
      if(tags.indexOf('医師向け') !== -1 || item.a === 'professional') return {label: '医師向け', cls: 'is-doc'};
      if(tags.indexOf('一般向け') !== -1 || tags.indexOf('患者さん向け') !== -1 || tags.indexOf('その症状大丈夫') !== -1 || item.a === 'general'){
        return {label: '一般向け', cls: 'is-gen'};
      }
      return {label: '記事', cls: 'is-art'};
    }

    function renderSuggestions(rawQuery){
      var q = norm(rawQuery).trim();
      if(q.length < 2){
        hideBox();
        return;
      }
      var tokens = q.split(/\s+/).filter(Boolean);
      box.replaceChildren();

      if(!Array.isArray(cachedIndex)){
        var loading = document.createElement('div');
        loading.className = 'ich-suggest-meta';
        loading.textContent = '候補を読み込んでいます…';
        box.appendChild(loading);
      } else {
        var tools = [], medArts = [], otherArts = [], slides = [], videos = [];
        for(var i = 0; i < cachedIndex.length; i++){
          var it = cachedIndex[i];
          if(!it || typeof it.u !== 'string' || !ALLOWED_LINK_RE.test(it.u)) continue;
          var hay = norm((it.t || '') + ' ' + ((it.tags || []).join(' ')));
          var ok = true;
          for(var ti = 0; ti < tokens.length; ti++){
            if(hay.indexOf(tokens[ti]) === -1){ ok = false; break; }
          }
          if(!ok) continue;
          if(it.k === 'ツール' && tools.length < 3) tools.push(it);
          else if(it.k === '記事'){
            if(isMedicalEntry(it.t, it.tags) && medArts.length < 4) medArts.push(it);
            else if(otherArts.length < 2) otherArts.push(it);
          }
          else if(it.k === 'スライド' && slides.length < 2) slides.push(it);
          else if(it.k === '動画' && videos.length < 2) videos.push(it);
          if(tools.length >= 3 && medArts.length >= 4 && slides.length >= 2 && videos.length >= 2) break;
        }
        var artSlots = medArts.concat(otherArts).slice(0, 4);
        var picks = tools.concat(artSlots, slides).slice(0, 8);
        if(picks.length < 8 && videos.length){
          picks = picks.concat(videos).slice(0, 8);
        }
        if(!picks.length){
          var none = document.createElement('div');
          none.className = 'ich-suggest-meta';
          none.textContent = '該当する候補は見つかりませんでした。下のボタンで記事全文検索できます。';
          box.appendChild(none);
        } else {
          picks.forEach(function(item){
            var a = document.createElement('a');
            a.className = 'ich-suggest-item';
            a.setAttribute('role', 'option');
            a.href = item.u;
            if(item.u.indexOf('https://blog.ichisouzo-lab.com/') !== 0){
              a.target = '_blank';
              a.rel = 'noopener noreferrer';
            }
            var info = classifyKind(item);
            var badge = document.createElement('span');
            badge.className = 'ich-sug-kind ' + info.cls;
            badge.textContent = info.label;
            var title = document.createElement('span');
            title.className = 'ich-sug-title';
            title.textContent = item.t;
            a.appendChild(badge);
            a.appendChild(title);
            box.appendChild(a);
          });
        }
      }

      var allBtn = document.createElement('button');
      allBtn.type = 'submit';
      allBtn.className = 'ich-suggest-all';
      allBtn.textContent = '「' + rawQuery.trim() + '」でブログ内をすべて検索 →';
      box.appendChild(allBtn);

      box.hidden = false;
      input.setAttribute('aria-expanded', 'true');
      activeIdx = -1;
    }

    function ensureIndexAndRender(){
      var val = input.value || '';
      if(!cachedIndex){
        getSearchIndex().then(function(data){
          if(Array.isArray(data)){
            cachedIndex = data;
            if(document.activeElement === input || !box.hidden){
              renderSuggestions(input.value || '');
            }
          }
        });
      }
      if(val.trim().length >= 2) renderSuggestions(val);
      else hideBox();
    }

    input.addEventListener('focus', function(){
      if(!cachedIndex) getSearchIndex().then(function(data){ if(Array.isArray(data)) cachedIndex = data; });
      if((input.value || '').trim().length >= 2) renderSuggestions(input.value);
    });
    input.addEventListener('input', ensureIndexAndRender);
    input.addEventListener('keydown', function(e){
      if(box.hidden) return;
      var els = focusables();
      if(!els.length) return;
      if(e.key === 'ArrowDown'){
        e.preventDefault();
        setFocus((activeIdx + 1) % els.length);
      } else if(e.key === 'ArrowUp'){
        e.preventDefault();
        setFocus(activeIdx <= 0 ? els.length - 1 : activeIdx - 1);
      } else if(e.key === 'Escape'){
        e.preventDefault();
        hideBox();
      } else if(e.key === 'Enter' && activeIdx >= 0 && els[activeIdx]){
        var target = els[activeIdx];
        if(target.tagName === 'A'){
          e.preventDefault();
          if(target.target === '_blank') window.open(target.href, '_blank', 'noopener,noreferrer');
          else location.href = target.href;
        }
      }
    });
    document.addEventListener('pointerdown', function(e){
      if(!form.contains(e.target)) hideBox();
    });
  }

  function init(){
    if(isTopPage()){
      var form = document.querySelector('#top-editarea .ich-search');
      var input = document.getElementById('ich-search-query');
      if(form && input){
        import(FEED_BASE + 'blog-topic-search.js').then(function(module){
          module.setupTopicSearch(form, input);
        }).catch(setupRealtimeSearch);
      }
    } else {
      setupRealtimeSearch();
    }
    if(!isIndex()) return;

    var domCards = collectServerCards();
    enhanceMustReadThumbs();
    annotateCategoryCounts();
    updateTrustStats(null);

    getFeed().then(function(feed){
      if(!feed || feed.v !== 1) return;
      if(feed.stats) updateTrustStats(feed.stats);
      if(isTopPage()){
        setupInlineTabs(feed, domCards);
        renderMediaShowcase(feed.showcase, feed.base || FEED_BASE);
      }
      if(feed.media){
        upgradeExistingMediaButtons(feed.media);
        setTimeout(function(){ upgradeExistingMediaButtons(feed.media); }, 600);
      }
    });
  }

  var started = false;
  function runOnce(){
    if(started) return;
    started = true;
    init();
  }
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', runOnce);
  } else {
    setTimeout(runOnce, 0);
  }
})();
