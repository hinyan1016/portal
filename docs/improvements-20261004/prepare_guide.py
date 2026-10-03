"""公開済みガイドの説明と導線を現在のポータルに合わせる。"""
from pathlib import Path
import json
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
PORTAL = 'https://ichisouzo-lab.com/'
POLICY = 'https://blog.ichisouzo-lab.com/entry/2026/05/22/074937'
soup = BeautifulSoup((HERE / 'guide-original.html').read_text(encoding='utf-8'), 'html.parser')
for a in soup.find_all('a', href=True):
    a['href'] = a['href'].replace('https://hinyan1016.hatenablog.com', 'https://blog.ichisouzo-lab.com')
    if a['href'] == 'https://blog.ichisouzo-lab.com/entry/2025/05/27/033741':
        a['href'] = 'https://blog.ichisouzo-lab.com/archive/category/%E5%88%9D%E6%9C%9F%E7%A0%94%E4%BF%AE%E5%8C%BB'
        a.string = '初期研修医向け記事をまとめて読む'
heading = soup.select_one('.sg-header h1')
heading.name = 'h2'
guide_css = soup.style.string.replace('.sg-header h1', '.sg-header h2').replace('.sg-format-item h4', '.sg-format-item h3')
guide_css = guide_css.replace('.sg-formats { grid-template-columns: 1fr 1fr; }', '.sg-formats { grid-template-columns: 1fr; }')
# 公開テーマの本文インラインリンク規則より詳細度を上げ、ガイド内のボタンだけ守る。
soup.style.string = guide_css + '\n.site-guide img{max-width:100%;height:auto}.entry-content .site-guide .sg-formats a[href]{display:flex;align-items:center;justify-content:center;min-height:44px;box-sizing:border-box;color:#1a5276;font-weight:700}.entry-content .site-guide .sg-card a[href]{min-height:44px;max-width:100%;padding:6px 16px;box-sizing:border-box;display:inline-flex;align-items:center}.sg-section-title{scroll-margin-top:80px}.sg-header h2{color:#fff;border:0}a:focus-visible{outline:3px solid #1a5276;outline-offset:4px}\n'
intro = soup.select_one('.sg-intro')
intro.clear()
intro.append(BeautifulSoup('''<p>医知創造ラボは、脳神経内科専門医が編集する医療と健康のメディアです。一般の方・ご家族には理解の手がかりを、医療従事者・研修医には知識を整理する場を提供しています。記事・図解・動画・スライド・ツールを、目的や対象読者に合わせて選べます。知りたいことから検索できます。</p><p><a href="https://ichisouzo-lab.com/guide.html">はじめての方へ：目的別の使い方</a> ／ <a href="https://ichisouzo-lab.com/#library">コンテンツを横断検索</a></p><p>案内更新：2026年10月4日</p>''', 'html.parser'))
banner = soup.select_one('.sg-header p')
intro.insert_after(banner.extract())
purpose = BeautifulSoup('''<section><h2 class="sg-section-title">🧭 何を知りたいですか？</h2><div class="sg-cards"><div class="sg-card"><h3>病気・薬・からだのことを理解したい</h3><p>一般の方・ご家族向けの内容を、記事・図解・動画から選べます。検索欄には「もの忘れ」などの日常の言葉でも入力できます。</p><a href="https://ichisouzo-lab.com/?audience=general#library">一般の方・ご家族向けに探す →</a></div><div class="sg-card"><h3>診療や学習の疑問を整理したい</h3><p>医療従事者・研修医向けの解説やスライド、診断支援ツールを探せます。</p><a href="https://ichisouzo-lab.com/?audience=professional#library">医療従事者向けに探す →</a></div><div class="sg-card"><h3>症状を整理したい</h3><p>一般向けの症状セルフチェックと、医療従事者向けの診断支援ツールは、利用対象が異なります。目的に合う入口を選んでください。</p><a href="https://ichisouzo-lab.com/#tools">ツールの入口を選ぶ →</a></div></div></section>''', 'html.parser')
purpose.find('h2').string = '🧭 目的から探す'
for link, label in zip(purpose.find_all('a'), ['一般の方・ご家族向け', '医療従事者向け', 'ツールを選ぶ']):
    link.string = label
intro.insert_after(purpose)
soup.style.string += '\n@supports(word-break:auto-phrase){.site-guide h2,.site-guide h3{text-wrap:balance;word-break:auto-phrase}}\n'
format_heading = next(x for x in soup.find_all('h2') if 'コンテンツの形式' in x.get_text())
format_intro = format_heading.find_next_sibling('p')
format_intro.string = '同じテーマに複数の形式がある場合は、トップページのカードから選べます。テーマによって用意されている形式は異なります。'
formats = soup.select_one('.sg-formats')
formats.clear()
for icon, title, desc, url in [
    ('📖', '記事', '背景や根拠まで、じっくり読む', PORTAL+'?kind=記事#library'),
    ('🖼️', '図解', '一枚の図で全体像をつかむ', 'https://tools.ichisouzo-lab.com/infographics/'),
    ('🎬', '動画', '説明を聞きながら理解する', PORTAL+'?kind=動画#library'),
    ('📊', 'スライド', '要点を順に読み、学習や復習に使う', 'https://tools.ichisouzo-lab.com/slides/'),
    ('🧰', 'ツール', '医療従事者向けの診断支援・計算を使う', 'https://tools.ichisouzo-lab.com/'),
]:
    node = soup.new_tag('div', attrs={'class':'sg-format-item'})
    span = soup.new_tag('span', attrs={'class':'sg-emoji'}); span.string=icon; node.append(span)
    h=soup.new_tag('h3'); h.string=title; node.append(h)
    p=soup.new_tag('p'); p.string=desc; node.append(p)
    a=soup.new_tag('a', href=url); a.string=title+'を探す →'; node.append(a)
    formats.append(node)
new_badge = soup.select_one('.sg-pick-tag.new')
if new_badge: new_badge.string='医学情報'
notice = soup.select_one('.sg-disclaimer')
notice.clear()
notice.append(BeautifulSoup('''<strong>ご利用にあたって</strong>：掲載情報は医学教育・参考情報であり、個別の診断や治療に代わるものではありません。AIは文章や図表などの制作を補助し、医学的な内容と公開可否は専門医が確認します。根拠の確認方法、監修体制、訂正の方針は<a href="https://blog.ichisouzo-lab.com/entry/2026/05/22/074937">編集方針</a>で公開しています。''', 'html.parser'))
faq=[('ログインは必要ですか？','トップページの検索や、あとで読む機能はログインせずに利用できます。保存はそのブラウザー内だけで、別の端末とは同期しません。'),('記事と動画を同じテーマで探せますか？','トップページでは同じテーマの形式をまとめて選べます。形式の絞り込みを使うと、記事や動画などの形式ごとにも探せます。'),('シリーズはどこから読み始められますか？','トップページのシリーズ入口から、読む順が用意されたシリーズを第1回からたどれます。その他のテーマも横断検索で探せます。')]
section=soup.new_tag('section')
h=soup.new_tag('h2',attrs={'class':'sg-section-title'});h.string='よくある質問';section.append(h)
for question,answer in faq:
    details=soup.new_tag('details'); summary=soup.new_tag('summary');summary.string=question;details.append(summary);p=soup.new_tag('p');p.string=answer;details.append(p);section.append(details)
notice.insert_before(section)
schema={'@context':'https://schema.org','@type':'FAQPage','mainEntity':[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':a}} for q,a in faq]}
script=soup.new_tag('script', type='application/ld+json');script.string=json.dumps(schema,ensure_ascii=False);soup.append(script)
soup.append(BeautifulSoup('''<div class="author-box" style="margin-top:24px;padding:18px;border-top:1px solid #ddd"><strong>監修：今村久司</strong><p>脳神経内科・総合内科・てんかんの専門医・指導医。<a href="https://blog.ichisouzo-lab.com/entry/2026/05/22/074937">監修者紹介・編集方針</a></p></div><!-- NO_VIDEO_ARTICLE --><!-- NO_INFOGRAPHIC_ARTICLE --><!-- NON_MEDICAL_ARTICLE: サイトの利用案内 -->''','html.parser'))
toc = soup.new_tag('nav', attrs={'class':'table-of-contents', 'aria-label':'目次'})
toc_list = soup.new_tag('ul')
for number, section_heading in enumerate(soup.select('.sg-section-title'), 1):
    section_heading['id'] = 'guide-section-' + str(number)
    item = soup.new_tag('li')
    link = soup.new_tag('a', href='#' + section_heading['id'])
    link.string = section_heading.get_text()
    item.append(link); toc_list.append(item)
toc.append(toc_list)
intro.insert_after(toc)
(HERE/'guide-revised.html').write_text(str(soup)+'\n',encoding='utf-8')
(HERE/'guide-preview.html').write_text('<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>医知創造ラボの歩き方：更新確認</title><style>body{margin:0;padding:20px;background:#fafafa;font-family:sans-serif}.preview-wrap{max-width:900px;margin:auto}h1{font-size:28px}a{overflow-wrap:anywhere}details{padding:12px 0}summary{cursor:pointer;font-weight:bold}</style></head><body><main class="preview-wrap"><h1>医知創造ラボの歩き方</h1>'+str(soup)+'</main></body></html>',encoding='utf-8')
print('Prepared existing guide revision:',len(soup.get_text()),'visible characters')
