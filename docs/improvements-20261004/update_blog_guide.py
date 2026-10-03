"""既存のサイトガイドだけを照合・保存し、検収済み本文を冪等更新する。"""
from pathlib import Path
import argparse
import base64
import hashlib
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]
sys.path.insert(0, str(WORKSPACE / 'medical-content/blog/_scripts'))
import embed_video_in_existing_article as api

TARGET = 'https://blog.ichisouzo-lab.com/entrance'


def request(url, env, body=None):
    base = api.atom_base(env).rsplit('/entry', 1)[0] + '/page'
    if not (url == base or url.startswith(base + '/') or url.startswith(base + '?')):
        raise ValueError('固定ページAPIの送信先が一致しません')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            raise ValueError('認証付きリダイレクトを拒否しました')
    headers = {'User-Agent': 'Ichisouzo-Portal-Guide/1.0',
               'Authorization': 'Basic ' + base64.b64encode((env['HATENA_ID'] + ':' + env['HATENA_API_KEY']).encode()).decode()}
    if body is not None:
        headers['Content-Type'] = 'application/atom+xml; charset=utf-8'
    req = urllib.request.Request(url, headers=headers, data=body, method='PUT' if body is not None else 'GET')
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=45) as response:
        return response.read()


def links(root):
    return {node.get('rel'): node.get('href') for node in root.findall('atom:link', api.NS)}


def identity(root):
    return {'title': root.findtext('atom:title', namespaces=api.NS),
            'id': root.findtext('atom:id', namespaces=api.NS),
            'alternate': links(root).get('alternate'),
            'edit': links(root).get('edit'),
            'published': root.findtext('atom:published', namespaces=api.NS),
            'draft': root.findtext('app:control/app:draft', namespaces=api.NS)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['snapshot', 'apply', 'verify'])
    args = parser.parse_args()
    env = api.credentials(api.DEFAULT_ENV)
    original_path = HERE / 'guide-original.xml'
    if args.action == 'snapshot':
        base = api.atom_base(env).rsplit('/entry', 1)[0] + '/page'
        feed = ET.fromstring(request(base, env))
        candidates = [entry for entry in feed.findall('atom:entry', api.NS) if (links(entry).get('alternate') or '').rstrip('/') == TARGET]
        if len(candidates) != 1:
            raise ValueError('対象固定ページが一意に見つかりません')
        xml = request(links(candidates[0])['edit'], env)
        root = api.entry_root(xml)
        if identity(root)['alternate'].rstrip('/') != TARGET or identity(root)['draft'] != 'no':
            raise ValueError('対象URLまたは公開状態が一致しません')
        if original_path.exists() and original_path.read_bytes() != xml:
            raise ValueError('既存スナップショットを上書きしません')
        original_path.write_bytes(xml)
        (HERE / 'guide-original.html').write_text(api.body_of(root), encoding='utf-8')
        api.write_json(HERE / 'guide-identity.json', identity(root))
        print(json.dumps({'snapshot': identity(root), 'content_type': root.find('atom:content', api.NS).get('type'), 'characters': len(api.body_of(root))}, ensure_ascii=False))
        return
    original = api.entry_root(original_path.read_bytes())
    expected = (HERE / 'guide-revised.html').read_text(encoding='utf-8')
    live_xml = request(links(original)['edit'], env)
    live = api.entry_root(live_xml)
    if identity(live) != identity(original):
        raise ValueError('固定ページの同一性が変わっています')
    if api.body_of(live) == expected:
        print('[NO-OP] ガイド本文は更新済みです')
    elif args.action == 'verify':
        raise ValueError('公開本文と検収済み本文が一致しません')
    else:
        if api.body_of(live) != api.body_of(original):
            raise ValueError('スナップショット後に本文が変わっています')
        if api.metadata_hash(live) != api.metadata_hash(original):
            raise ValueError('スナップショット後にメタデータが変わっています')
        live.find('atom:content', api.NS).text = expected
        request(links(original)['edit'], env, ET.tostring(live, encoding='utf-8', xml_declaration=True))
        live_xml = request(links(original)['edit'], env)
        live = api.entry_root(live_xml)
        if identity(live) != identity(original) or api.body_of(live) != expected:
            raise ValueError('更新後の同一性または本文が一致しません')
        print('[OK] 対象ガイドの本文のみ更新・再取得検証済み')
    (HERE / 'guide-verified.xml').write_bytes(live_xml)
    api.write_json(HERE / 'guide-receipt.json', {'target': TARGET, 'identity': identity(live), 'body_sha256': api.sha(expected), 'verified': api.now()})


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'[ERROR] {type(exc).__name__}: {exc}', file=sys.stderr)
        sys.exit(1)
