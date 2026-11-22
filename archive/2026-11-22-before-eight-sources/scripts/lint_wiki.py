#!/usr/bin/env python3
"""Offline structural lint. Does NOT assess scientific fidelity or safety."""
import argparse, json, re, sys
from pathlib import Path
from urllib.parse import urlparse
ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = {'發酵的基本原理','常見發酵食品介紹','發酵食品與健康','自製發酵食品','食品安全與保存'}
REQUIRED = ['AGENTS.md','README.md','sources.json','wiki/index.md','wiki/log.md','raw','wiki/articles','wiki/review','templates','reports']

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--strict',action='store_true',help='require >=5 approved unique sources and >=1 approved article')
    args=parser.parse_args()
    errors=[]; warnings=[]
    for name in REQUIRED:
        if not (ROOT/name).exists(): errors.append('missing path: '+name)
    try: sources=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))
    except Exception as exc: errors.append('sources.json invalid: '+str(exc)); sources=[]
    if not isinstance(sources,list): errors.append('sources.json must be a list'); sources=[]
    ids=set(); urls=set(); by_id={}; approved_sources=set()
    for idx,s in enumerate(sources,1):
        if not isinstance(s,dict): errors.append(f'source #{idx} is not an object'); continue
        sid=s.get('source_id'); url=s.get('url'); status=s.get('status')
        if not isinstance(sid,str) or not re.fullmatch(r'S\d{3,}',sid): errors.append(f'bad source_id in #{idx}: {sid}')
        elif sid in ids: errors.append('duplicate source_id: '+sid)
        else: ids.add(sid);by_id[sid]=s
        for field in ['title','authors','year','url','source_type','raw_path','accessed_on','status']:
            if field not in s: errors.append(f'{sid} missing field: {field}')
        if not isinstance(s.get('title'),str) or not s['title'].strip(): errors.append(f'{sid} empty title')
        if not isinstance(s.get('authors'),list) or not s['authors']: errors.append(f'{sid} missing authors/organization (use ["unknown"] with note if necessary)')
        if s.get('year') is not None and not isinstance(s.get('year'),int): errors.append(f'{sid} year must be int or null')
        if not isinstance(url,str) or urlparse(url).scheme not in ('https','http') or not urlparse(url).netloc: errors.append(f'{sid} invalid URL')
        elif url in urls: errors.append('duplicate source URL: '+url)
        else: urls.add(url)
        if s.get('source_type') not in ('academic','government','professional','education','guide'): errors.append(f'{sid} invalid source_type')
        if status not in ('pending','draft','approved','blocked','needs_human_review'): errors.append(f'{sid} invalid status')
        if status=='approved': approved_sources.add(sid)
        raw_path=s.get('raw_path')
        if isinstance(raw_path,str):
            p=(ROOT/raw_path).resolve()
            if ROOT not in p.parents or not raw_path.startswith('raw/') or not p.is_file(): errors.append(f'{sid} raw_path unavailable/unsafe: {raw_path}')
        else: errors.append(f'{sid} raw_path missing')
    articles=sorted((ROOT/'wiki/articles').glob('*.md'))
    article_ids=set();approved_articles=0;referenced_approved=set()
    for p in articles:
        content=p.read_text(encoding='utf-8')
        if not content.startswith('---\n') or '\n---\n' not in content[4:]: errors.append(f'{p.name}: missing YAML-like front matter');continue
        meta,body=content[4:].split('\n---\n',1)
        fields={}
        for line in meta.splitlines():
            if ':' in line:
                k,v=line.split(':',1);fields[k.strip()]=v.strip()
        aid=fields.get('article_id','')
        if not re.fullmatch(r'W\d{3,}',aid): errors.append(f'{p.name}: invalid article_id')
        if aid in article_ids: errors.append(f'duplicate article ID {aid}')
        article_ids.add(aid)
        if fields.get('category') not in CATEGORIES: errors.append(f'{p.name}: unknown category')
        state=fields.get('status')
        if state not in ('draft','approved','blocked','needs_human_review'): errors.append(f'{p.name}: invalid status')
        if not re.search(r'^#\s+\S',body,re.M):errors.append(f'{p.name}: missing H1 title')
        for token in ['**摘要：**','**關鍵字：**','## 正文','## 來源']:
            if token not in body: errors.append(f'{p.name}: missing {token}')
        declared=set(re.findall(r'S\d{3,}',fields.get('source_ids','')))
        cited=set(re.findall(r'\[(S\d{3,})\]',body))
        if not declared: errors.append(f'{p.name}: missing source_ids')
        if not cited: errors.append(f'{p.name}: no source citations')
        for ref in declared|cited:
            if ref not in ids: errors.append(f'{p.name}: unknown source {ref}')
        for ref in cited-declared: errors.append(f'{p.name}: citation {ref} not declared in metadata')
        if state=='approved':
            approved_articles+=1;referenced_approved |= declared
            for ref in declared:
                if ref not in approved_sources: errors.append(f'{p.name}: approved article refers to non-approved source {ref}')
    if not sources: warnings.append('0 source records; no ingest performed yet')
    if not articles: warnings.append('0 wiki articles; this is a project scaffold')
    if args.strict:
        if len(approved_sources)<5:errors.append(f'strict: approved sources {len(approved_sources)}/5')
        if approved_articles<1:errors.append('strict: no approved Wiki article')
        if len(referenced_approved)<5:errors.append(f'strict: approved articles cite {len(referenced_approved)}/5 approved sources')
    print('Wiki Lint | mode='+('strict' if args.strict else 'scaffold'))
    print(f'Sources: {len(sources)} | approved sources: {len(approved_sources)} | articles: {len(articles)} | approved articles: {approved_articles}')
    for w in warnings:print('WARNING:',w)
    for e in errors:print('ERROR:',e)
    print('RESULT:', 'PASS' if not errors else 'FAIL', f'({len(errors)} errors, {len(warnings)} warnings)')
    return 1 if errors else 0
if __name__=='__main__':sys.exit(main())
