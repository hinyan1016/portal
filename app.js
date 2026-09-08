(function(){
  'use strict';
  var menuButton=document.querySelector('.menu-button');
  var nav=document.getElementById('global-nav');
  menuButton.addEventListener('click',function(){var open=menuButton.getAttribute('aria-expanded')==='true';menuButton.setAttribute('aria-expanded',String(!open));nav.classList.toggle('open',!open);});
  nav.addEventListener('click',function(){menuButton.setAttribute('aria-expanded','false');nav.classList.remove('open');});

  var input=document.getElementById('site-search');
  var results=document.getElementById('search-results');
  var submit=document.getElementById('search-submit');
  var searchIndex=null,loading=false,timer;
  var colors={'記事':'#355f88','ツール':'#12324a','図解':'#0b6b68','スライド':'#2e7d62'};
  function escapeHTML(value){return (value||'').replace(/[&<>\"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c];});}
  function safeURL(value,hosts){try{var url=new URL(value,window.location.href);return url.protocol==='https:'&&hosts.indexOf(url.hostname)>=0?url.href:'';}catch(error){return '';}}
  function loadIndex(){if(searchIndex||loading)return;loading=true;fetch('https://ichisouzo-lab.com/search-index.json').then(function(r){if(!r.ok)throw new Error('search');return r.json();}).then(function(data){searchIndex=data;loading=false;renderSearch(input.value);}).catch(function(){loading=false;});}
  function fullSearch(query){window.location.href='https://blog.ichisouzo-lab.com/search?q='+encodeURIComponent(query);}
  function appendSearchResult(href,kind,label,color){var link=document.createElement('a');link.href=href;var badge=document.createElement('span');badge.className='result-kind';badge.textContent=kind;if(color)badge.style.background=color;var title=document.createElement('span');title.textContent=label;link.appendChild(badge);link.appendChild(title);results.appendChild(link);}
  function showSearchMessage(message){var empty=document.createElement('div');empty.className='empty';empty.textContent=message;results.appendChild(empty);}
  function renderSearch(query){query=(query||'').trim();results.replaceChildren();if(!query){results.hidden=true;return;}results.hidden=false;if(!searchIndex){showSearchMessage('検索データを読み込んでいます…');loadIndex();return;}var term=query.toLowerCase(),found=[];for(var i=0;i<searchIndex.length&&found.length<12;i++){if((searchIndex[i].t||'').toLowerCase().indexOf(term)>=0)found.push(searchIndex[i]);}found.forEach(function(item){var href=safeURL(item.u,['ichisouzo-lab.com','blog.ichisouzo-lab.com','tools.ichisouzo-lab.com','check.ichisouzo-lab.com']);if(href)appendSearchResult(href,String(item.k||'記事'),String(item.t||''),colors[item.k]||colors['記事']);});if(!results.children.length)showSearchMessage('見出しに一致する結果はありません。');appendSearchResult('https://blog.ichisouzo-lab.com/search?q='+encodeURIComponent(query),'全文','ブログで「'+query+'」を全文検索',colors['記事']);}
  input.addEventListener('focus',loadIndex);
  input.addEventListener('input',function(){clearTimeout(timer);timer=setTimeout(function(){renderSearch(input.value);},120);});
  input.addEventListener('keydown',function(event){if(event.key==='Escape'){results.hidden=true;}if(event.key==='Enter'){event.preventDefault();var first=results.querySelector('a');if(first)window.location.href=first.href;else if(input.value.trim())fullSearch(input.value.trim());}});
  submit.addEventListener('click',function(){var first=results.querySelector('a');if(!results.hidden&&first)window.location.href=first.href;else if(input.value.trim())fullSearch(input.value.trim());});
  document.addEventListener('click',function(event){if(!event.target.closest('.search'))results.hidden=true;});

  function text(node,name){var el=node.querySelector(name);return el?el.textContent.trim():'';}
  function formatDate(raw){var d=new Date(raw);if(isNaN(d.getTime()))return '';var iso=d.toISOString().slice(0,10);return {iso:iso,label:iso.replace(/-/g,'.')};}
  function getImage(item){var enc=item.querySelector('enclosure[type^="image"]');if(enc&&enc.getAttribute('url'))return enc.getAttribute('url');var desc=text(item,'description');var match=desc.match(/<img[^>]+src=["']([^"']+)/i);return match?match[1]:'';}
  function articleMarkup(item){var title=escapeHTML(text(item,'title'));var link=safeURL(text(item,'link'),['blog.ichisouzo-lab.com']);if(!link)return '';var date=formatDate(text(item,'pubDate'));var image=safeURL(getImage(item),['cdn.image.st-hatena.com','cdn-ak.f.st-hatena.com']);var media=image?'<img src="'+escapeHTML(image)+'" alt="" loading="lazy">':'<span class="article-placeholder" aria-hidden="true">記</span>';return '<a class="article-card" href="'+link+'">'+media+'<span><time datetime="'+date.iso+'">'+date.label+'</time><strong>'+title+'</strong></span></a>';}
  fetch('https://blog.ichisouzo-lab.com/rss').then(function(r){if(!r.ok)throw new Error('rss');return r.text();}).then(function(xml){var doc=new DOMParser().parseFromString(xml,'application/xml');var items=Array.prototype.slice.call(doc.querySelectorAll('item'));var general=[],professional=[];items.forEach(function(item){var cats=Array.prototype.slice.call(item.querySelectorAll('category')).map(function(c){return c.textContent.trim();});var title=text(item,'title');var proMarker=/(医療従事者向け|医師向け|医向け)/.test(title);var isProfessional=proMarker||cats.some(function(c){return c==='医師向け'||c==='初期研修医'||c==='医療従事者向け';});var isGeneral=!isProfessional&&cats.indexOf('一般向け')>=0;if(isGeneral)general.push(item);else if(isProfessional)professional.push(item);});[['general',general],['professional',professional]].forEach(function(group){var target=document.querySelector('[data-audience="'+group[0]+'"] .article-list');var markup=group[1].slice(0,3).map(articleMarkup).filter(Boolean).join('');if(target&&markup)target.innerHTML=markup;});document.getElementById('article-status').textContent='公開ブログのRSSから、読者カテゴリが明示された最新記事を表示しています。';}).catch(function(){document.getElementById('article-status').textContent='試作保存時に確認した新着を表示しています。';});

  // 新着にはサムネイル未作成の図解もある。実画像の読込成功後にだけ差し替える。
  function loadVisual(item){
    var url='https://tools.ichisouzo-lab.com/infographics/'+encodeURIComponent(item.slug)+'/';
    return new Promise(function(resolve){
      var image=new Image(), original=false;
      image.onload=function(){resolve({item:item,url:url,image:image.src,portrait:image.naturalHeight>image.naturalWidth});};
      image.onerror=function(){
        if(!original){original=true;image.src=url+'infographic.png';}
        else resolve(null);
      };
      image.src=url+'thumb.png';
    });
  }
  fetch('https://tools.ichisouzo-lab.com/infographics/manifest.json')
    .then(function(r){if(!r.ok)throw new Error('manifest');return r.json();})
    .then(function(data){
      var items=(data.items||[]).filter(function(item){return item&&item.slug;})
        .sort(function(a,b){return (b.date||'').localeCompare(a.date||'');}).slice(0,3);
      return Promise.all(items.map(loadVisual));
    }).then(function(loaded){
      var visuals=loaded.filter(Boolean);
      if(!visuals.length)return;
      document.getElementById('visual-preview').innerHTML=visuals.map(function(visual,index){
        return '<a class="visual-tile'+(index===0?' visual-tile-large':'')+'" href="'+visual.url+'"><img src="'+visual.image+'" alt="'+escapeHTML(visual.item.title)+'の図解" loading="lazy"><span>'+escapeHTML(visual.item.title)+'</span></a>';
      }).join('');
      var hero=visuals[0],heroLink=document.querySelector('.hero-visual');
      heroLink.href=hero.url;
      heroLink.setAttribute('aria-label','最新の図解：'+hero.item.title);
      heroLink.querySelector('img').src=hero.image;
      heroLink.querySelector('img').classList.toggle('portrait-preview',hero.portrait);
      heroLink.querySelector('img').alt=hero.item.title+'の図解';
      heroLink.querySelector('.visual-caption span').textContent=hero.item.title;
    }).catch(function(){});

})();
