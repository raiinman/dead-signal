"""Persistent, non-executing static PYC consumer index."""
from __future__ import annotations
import hashlib, json, marshal, os, re, sqlite3, time, types
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
TOKEN_RE = re.compile(rb"[A-Za-z_][A-Za-z0-9_./:-]{2,255}")
def _text(value): return str(value).encode('utf-8','backslashreplace').decode('utf-8')

def _now(): return datetime.now(timezone.utc).isoformat()
def _atomic(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)+'\n', encoding='utf-8'); os.replace(tmp,path)

def _walk(code: types.CodeType, parent: str | None=None):
    name = code.co_name if parent is None else f"{parent}.<locals>.{code.co_name}"
    yield name, parent, code
    for value in code.co_consts:
        if isinstance(value, types.CodeType): yield from _walk(value, name)

def inspect_pyc(raw: bytes) -> dict[str, Any]:
    fallback=sorted({m.group().decode('ascii','ignore') for m in TOKEN_RE.finditer(raw)})
    result={"marshal_compatible":False,"error":None,"scopes":[],"raw_tokens":fallback}
    try:
        root=marshal.loads(raw[16:])
        if not isinstance(root,types.CodeType): raise ValueError('marshal payload was not a code object')
        result['marshal_compatible']=True
        for qual,parent,code in _walk(root):
            strings=sorted({_text(v) for v in code.co_consts if isinstance(v,str) and len(v)<=1000})
            numbers=sorted({v for v in code.co_consts if isinstance(v,(int,float)) and not isinstance(v,bool)}, key=str)
            result['scopes'].append({"qualname":_text(qual),"parent":_text(parent) if parent else None,"filename":_text(code.co_filename),"names":sorted(_text(v) for v in code.co_names),"strings":strings,"numbers":numbers[:500]})
    except Exception as error: result['error']=f"{type(error).__name__}: {error}"
    return result

class ConsumerIndex:
    def __init__(self,database): self.database=Path(database)
    def _connect(self):
        c=sqlite3.connect(self.database); c.row_factory=sqlite3.Row; return c
    def initialize(self):
        self.database.parent.mkdir(parents=True,exist_ok=True)
        with closing(self._connect()) as c,c:
            c.executescript('''CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE IF NOT EXISTS files(layer TEXT,path TEXT,sha256 TEXT,size INTEGER,marshal_compatible INTEGER,error TEXT,first_seen TEXT,last_seen TEXT,PRIMARY KEY(layer,path)); CREATE TABLE IF NOT EXISTS scopes(layer TEXT,path TEXT,qualname TEXT,parent TEXT,filename TEXT,names_json TEXT,strings_json TEXT,numbers_json TEXT,PRIMARY KEY(layer,path,qualname)); CREATE TABLE IF NOT EXISTS tokens(layer TEXT,path TEXT,qualname TEXT,token TEXT,kind TEXT,PRIMARY KEY(layer,path,qualname,token,kind)); CREATE INDEX IF NOT EXISTS token_lookup ON tokens(token,qualname);''')
            old=c.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
            if old and old[0]!=str(SCHEMA_VERSION): c.executescript('DELETE FROM files; DELETE FROM scopes; DELETE FROM tokens;')
            c.execute("INSERT OR REPLACE INTO meta VALUES('schema_version',?)",(str(SCHEMA_VERSION),))
    def update(self,layers:dict[str,Path],activity=None):
        self.initialize(); activity=activity or (lambda x:None); start=time.perf_counter(); stats=Counter(); now=_now()
        with closing(self._connect()) as c,c:
            known={(r['layer'],r['path']):dict(r) for r in c.execute('SELECT * FROM files')}; seen=set()
            for layer in ('base','current'):
                root=Path(layers[layer]); files=sorted(root.rglob('*.pyc'),key=lambda p:p.as_posix().casefold()); activity(f'Consumer Index: {layer} layer has {len(files)} PYC files')
                for path in files:
                    rel=path.relative_to(root).as_posix(); key=(layer,rel); seen.add(key); stats['files_considered']+=1; raw=path.read_bytes(); sha=hashlib.sha256(raw).hexdigest()
                    if key in known and known[key]['sha256']==sha: stats['pycs_reused']+=1; c.execute('UPDATE files SET last_seen=? WHERE layer=? AND path=?',(now,layer,rel)); continue
                    info=inspect_pyc(raw); first=known.get(key,{}).get('first_seen',now); c.execute('DELETE FROM scopes WHERE layer=? AND path=?',(layer,rel)); c.execute('DELETE FROM tokens WHERE layer=? AND path=?',(layer,rel))
                    c.execute('INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?,?,?)',(layer,rel,sha,len(raw),int(info['marshal_compatible']),info['error'],first,now))
                    scope_occurrences=Counter()
                    for s in info['scopes']:
                        scope_occurrences[s['qualname']]+=1
                        qualname=s['qualname'] if scope_occurrences[s['qualname']]==1 else f"{s['qualname']}#{scope_occurrences[s['qualname']]}"
                        c.execute('INSERT INTO scopes VALUES(?,?,?,?,?,?,?,?)',(layer,rel,qualname,s['parent'],s['filename'],json.dumps(s['names']),json.dumps(s['strings']),json.dumps(s['numbers'])))
                        for kind,values in (('name',s['names']),('string',s['strings'])):
                            c.executemany('INSERT OR IGNORE INTO tokens VALUES(?,?,?,?,?)',((layer,rel,qualname,str(v),kind) for v in values))
                    if not info['marshal_compatible']:
                        for token in info['raw_tokens']: c.execute('INSERT OR IGNORE INTO tokens VALUES(?,?,?,?,?)',(layer,rel,'<raw-file>',token,'raw'))
                    stats['pycs_reindexed']+=1; stats['marshal_compatible']+=int(info['marshal_compatible']); stats['fallback_files']+=int(not info['marshal_compatible'])
            for key in set(known)-seen:
                for table in ('files','scopes','tokens'): c.execute(f'DELETE FROM {table} WHERE layer=? AND path=?',key)
                stats['files_removed']+=1
        stats['duration_seconds']=round(time.perf_counter()-start,6); return dict(stats)
    def find_scopes(self,tokens:list[str],same_scope=True):
        if not tokens:return []
        marks=','.join('?'*len(tokens)); group='layer,path,qualname' if same_scope else 'layer,path'
        sql=f'''SELECT layer,path,qualname,COUNT(DISTINCT token) matches FROM tokens WHERE token IN ({marks}) GROUP BY {group} HAVING matches=? ORDER BY layer,path,qualname'''
        with closing(self._connect()) as c: return [dict(r) for r in c.execute(sql,(*tokens,len(set(tokens))))]

def _source_root(tables:Path):
    try: return Path(json.loads((tables/'snapshot.json').read_text(encoding='utf-8'))['source_root'])
    except Exception: return tables
def run_consumer_index(base,current,output,reports,activity=None):
    db=Path(output)/'catalogs'/'dead-signal-consumer-index.sqlite'; index=ConsumerIndex(db); stats=index.update({'base':_source_root(Path(base)),'current':_source_root(Path(current))},activity)
    with closing(index._connect()) as c: counts={r['layer']:r['n'] for r in c.execute('SELECT layer,COUNT(*) n FROM files GROUP BY layer')}; scopes=c.execute('SELECT COUNT(*) FROM scopes').fetchone()[0]
    summary={'schema':'dead-signal-consumer-index-summary','schema_version':SCHEMA_VERSION,'generated_at':_now(),'database':str(db),'record_counts':{'files':sum(counts.values()),'base_files':counts.get('base',0),'current_files':counts.get('current',0),'scopes':scopes},'cache_statistics':stats,'policy':'Static marshal metadata and raw token indexing only; game bytecode is never imported or executed.'}; _atomic(Path(reports)/'consumer-index-summary.json',summary); return {'summary':summary,'database':str(db),'cache_statistics':stats}
