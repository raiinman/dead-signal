"""Cross-stage consistency diagnostics and field-level publication blockers."""
from __future__ import annotations
import json,os,sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path
from typing import Any
from dead_signal_semantic_registry import DEFINITIONS
def build_self_diagnostics(output:Path|str,projection:dict[str,Any],reports:Path|str):
 output=Path(output);findings=[]
 names=[d.semantic_name for d in DEFINITIONS]
 for name,count in Counter(names).items():
  if count>1:findings.append({'severity':'BLOCKER','code':'duplicate-semantic-definition','semantic_field':name,'message':f'{count} definitions conflict'})
 registry=output/'catalogs/dead-signal-table-registry.sqlite';known=set()
 if registry.is_file():
  with closing(sqlite3.connect(registry)) as c:known={row[0] for row in c.execute('SELECT DISTINCT relative_path FROM tables')}
 pattern='client_data/bullet_pattern_data.json';pattern_exists=pattern in known
 expected=sum(1 for w in projection.get('weapons',[]) if ((w.get('ranged_stats') or {}).get('bullet_pattern_id')))
 resolved=sum(1 for w in projection.get('weapons',[]) if ((w.get('ranged_stats') or {}).get('projectile_count')) not in (None,''))
 if pattern_exists and expected and not resolved:findings.append({'severity':'BLOCKER','code':'known-target-zero-resolution','semantic_field':'projectile_count','message':'Bullet-pattern target exists in registry but projection resolved zero projectile counts.'})
 for weapon in projection.get('weapons',[]):
  family=weapon.get('ballistic_family') or {};allowed=set(family.get('allowed_inherited_groups') or [])
  disallowed=allowed-{'projectiles','bullet_speed','falloff'}
  if disallowed:findings.append({'severity':'BLOCKER','code':'disallowed-family-leakage','semantic_field':sorted(disallowed)[0],'blueprint_id':weapon.get('blueprint_id'),'message':'Ballistic family declares a disallowed inherited group.'})
 if not registry.is_file():findings.append({'severity':'INFO','code':'registry-unavailable','message':'Table registry unavailable; locator consistency checks skipped.'})
 blockers=sorted({f.get('semantic_field') for f in findings if f['severity']=='BLOCKER' and f.get('semantic_field')})
 report={'schema':'dead-signal-self-diagnostics','schema_version':1,'record_counts':dict(Counter(f['severity'] for f in findings)),'findings':findings,'publication_blocked_fields':blockers,'policy':'BLOCKER findings suppress only affected semantic fields; unrelated Miner harvest output remains available.'};path=Path(reports)/'dead-signal-self-diagnostics.json';path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8');os.replace(tmp,path);return report
def apply_publication_blocks(projection:dict[str,Any],blocked:list[str]):
 blocked=set(blocked)
 for weapon in projection.get('weapons',[]):
  handling=weapon.get('handling') or {}
  for field in blocked:(handling.get('semantic') or {}).pop(field,None)
  if 'projectile_count' in blocked and isinstance(weapon.get('ranged_stats'),dict):weapon['ranged_stats']['projectile_count']=None
 return projection
