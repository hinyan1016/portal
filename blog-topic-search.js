// ブログトップ専用。検索語の照合は端末内で行い、全文検索は読者が選んだときに開く。
const indexURL = new URL('blog-topic-index.json', import.meta.url);
const formats = ['記事', 'ツール', '図解', 'スライド', '動画'];
const examples = ['頭を打ったあとに気をつけること', 'ワルファリンの量を調整したい', '救急で使う薬を復習したい'];
const stopWords = new Set('です ます たい する いる ある なる ため こと もの とき かた あと どう どんな どの どれ について ください 知り 教え 探し 調べ 見る 見 使う 復習 ほしい いい した するべき さん'.split(' '));
const segmenter = typeof Intl.Segmenter === 'function' ? new Intl.Segmenter('ja', {granularity:'word'}) : null;

function normalize(text){
  return String(text || '').normalize('NFKC').toLowerCase().trim();
}

function tokenize(query){
  const subject = query.replace(/患者さんの/g,'').replace(/しびれる/g,'しびれ').replace(/を(?:作成|作り|書き)(?:したい|たい)/g,' ')
    .replace(/(?:の|を)(?:スライド|動画|図解|ツール)(?:で|を)?(?:見たい|使いたい|探したい)?/g,' ');
  const parts = segmenter
    ? Array.from(segmenter.segment(subject), part => part.isWordLike ? part.segment : '')
    : subject.split(/[\s、。！？をがはのにへともで]+/);
  return [...new Set(parts.filter(s => s && !stopWords.has(s) && (s.length > 1 || /[一-龯A-Za-z0-9]/.test(s))))].slice(0,24);
}

function selectFormat(query){
  if (/動画|youtube/.test(query)) return '動画';
  if (/スライド/.test(query)) return 'スライド';
  if (/図解/.test(query)) return '図解';
  if (/調整|計算|ツール|換算|作成したい|チェッカー/.test(query)) return 'ツール';
  return '記事';
}

function prepare(rows){
  return rows.map(row => ({
    row, title: normalize(row.t),
    titles: normalize(row.links.map(link => link.t || '').join(' ')),
    tags: normalize(row.tags.join(' ')), aliases: row.aliases.map(normalize)
  }));
}

function rank(index, query){
  const tokens = tokenize(query);
  // 稀な主題語（例「採血」）が、複数のテーマに現れる「手」「薬」より順位に効くようにする。
  const weights = tokens.map(token => {
    const frequency = index.reduce((n, item) => n + Number(item.title.includes(token) || item.titles.includes(token) ||
      item.tags.includes(token) || item.aliases.some(alias => alias.includes(token))), 0);
    return Math.log(1 + index.length / (1 + frequency));
  });
  const preferred = selectFormat(query);
  const matches = [];
  for (const topic of index) {
    let direct = 0;
    if (topic.title.includes(query)) direct = 90;
    else if (topic.titles.includes(query)) direct = 78;
    else if (topic.tags.includes(query)) direct = 30;
    for (const alias of topic.aliases) {
      if (alias === query) direct = Math.max(direct, 120);
      else if (query.includes(alias)) direct = Math.max(direct, 39 + Math.min(alias.length, 18));
    }
    let score = 0, count = 0;
    for (const [i,token] of tokens.entries()) {
      const weight = topic.title.includes(token) ? 8 : topic.titles.includes(token) ? 6
        : topic.aliases.some(alias => alias.includes(token)) ? 5 : topic.tags.includes(token) ? 3 : 0;
      if (weight) { count++; score += weight * Math.min(token.length, 5) * weights[i] / 3; }
    }
    if (!direct && (!count || count < Math.ceil(tokens.length * 0.7))) continue;
    const formatBonus = preferred !== '記事' && topic.row.links.some(link => link.k === preferred) ? 18 : 0;
    matches.push({row:topic.row, score:direct + score + formatBonus});
  }
  matches.sort((a,b) => b.score - a.score);
  return matches.slice(0,8).map(match => match.row);
}

function make(tag, cls, text){
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text) node.textContent = text;
  return node;
}

function topicCard(topic, preferred){
  const group = make('section', 'ich-topic-group');
  group.append(make('h3', '', topic.t));
  const actions = make('div', 'ich-topic-actions');
  const order = [preferred, ...formats.filter(k => k !== preferred)];
  const links = topic.links.slice().sort((a,b) => order.indexOf(a.k) - order.indexOf(b.k));
  const labels = {記事:'記事を読む',動画:'動画を見る',図解:'図解を見る',スライド:'スライド',ツール:'ツールを開く'};
  if (topic.a === 'professional' || topic.a === 'general') {
    actions.append(make('span', 'ich-topic-audience', topic.a === 'professional' ? '医療者向け' : '一般向け'));
  }
  for (const link of links) {
    if (!/^https:\/\/(?:(?:blog|tools|check)\.ichisouzo-lab\.com\/|www\.youtube\.com\/watch\?v=[\w-]{11}$|ichisouzo-lab\.com\/)/.test(link.u)) continue;
    const duplicates = links.filter(other => other.k === link.k).length > 1;
    let label = labels[link.k] || link.k;
    if (link.p) label += '（' + link.p + '枚）';
    if (duplicates) label += '　' + (link.t || topic.t);
    const action = make('a', 'ich-topic-link', label);
    action.href = link.u;
    action.setAttribute('aria-label', (link.t || topic.t) + '　' + label);
    actions.append(action);
  }
  group.append(actions);
  return group;
}

export function setupTopicSearch(form, input){
  const nav = form.closest('.ich-nav-wrap');
  if (!nav) return;
  const panel = make('div', 'ich-topic-panel');
  panel.id = 'ich-topic-results';
  panel.hidden = true;
  const status = make('p', 'ich-topic-status');
  status.setAttribute('role', 'status');
  const content = make('div', 'ich-topic-content');
  const close = make('button', 'ich-topic-close', '閉じる');
  close.type = 'button';
  panel.append(close,status,content);
  nav.insertAdjacentElement('afterend',panel);
  input.placeholder = '知りたいことから探す';
  input.setAttribute('aria-label', '普段の言葉や病名で、記事・動画・ツールを検索');
  input.setAttribute('aria-controls', panel.id);
  input.autocomplete = 'off';
  let index, pending, failed = false, ignoreFocus = false;
  function show(open){
    panel.hidden = !open;
    input.setAttribute('aria-expanded', String(open));
  }
  function dismiss(){
    show(false);
    ignoreFocus = true;
    input.focus();
    ignoreFocus = false;
  }
  function draw(){
    const raw = input.value.trim();
    const query = normalize(raw);
    content.replaceChildren();
    if (!query) {
      status.textContent = '検索例';
      const list = make('div', 'ich-topic-examples');
      for (const example of examples) {
        const btn = make('button', 'ich-topic-example', example);
        btn.type = 'button';
        btn.addEventListener('click', () => { input.value = example; input.focus(); search(); });
        list.append(btn);
      }
      content.append(list);
      return;
    }
    if (index) {
      const results = rank(index, query.slice(0,256));
      status.textContent = results.length ? '「' + raw + '」の候補' : '一致するテーマが見つかりませんでした。';
      for (const row of results) content.append(topicCard(row,selectFormat(query)));
    } else {
      status.textContent = failed ? '候補を取得できませんでした。ブログの全文検索が使えます。' : '検索候補を読み込んでいます…';
    }
    const all = make('a', 'ich-topic-full', 'この言葉でブログ全文を検索');
    const url = new URL(form.action);
    url.searchParams.set(input.name, raw);
    all.href = url.href;
    content.append(all);
  }
  function search(){
    show(true);
    if (!index && !pending) {
      failed = false;
      pending = fetch(indexURL, {credentials:'omit'}).then(response => {
        if (!response.ok) throw Error('index');
        return response.json();
      }).then(rows => { index = prepare(rows); }).catch(() => { failed = true; }).finally(() => {
        pending = null;
        if (!panel.hidden) draw();
      });
    }
    draw();
  }
  form.addEventListener('submit', event => { event.preventDefault(); search(); });
  input.addEventListener('input', event => { if (!event.isComposing) search(); });
  input.addEventListener('compositionend', search);
  input.addEventListener('focus', () => { if (!ignoreFocus) search(); });
  input.addEventListener('click', () => { if (panel.hidden) search(); });
  input.addEventListener('keydown', event => {
    if (event.isComposing || event.keyCode === 229) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      if (panel.hidden) search();
      const first = content.querySelector('a, button');
      if (first) first.focus();
    } else if (event.key === 'Escape') { event.preventDefault(); show(false); }
  });
  panel.addEventListener('keydown', event => { if (event.key === 'Escape') dismiss(); });
  close.addEventListener('click', dismiss);
  document.addEventListener('click', event => {
    const path = event.composedPath();
    if (!path.includes(form) && !path.includes(panel)) show(false);
  });
  show(false);
  if (document.activeElement === input || input.value) search();
}
