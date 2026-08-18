"""Registry-backed Base/Current data and dependency diff."""
from __future__ import annotations
import json, os, sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from dead_signal_semantic_registry import DEFINITIONS

SCHEMA_VERSION=1
MAX_TABLE_DETAILS=500;MAX_RECORD_DETAILS=200;MAX_FIELD_DETAILS=100
def _now():return datetime.now(timezone.utc).isoformat()
def _atomic(path,payload):path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8');os.replace(tmp,path)
def _load(path):
 try:return json.loads(Path(path).read_text(encoding='utf-8-sig'))
 except Exception:return None
def _records(payload):
 if isinstance(payload,dict):
  for key in ('records','data','items','rows'):
   value=payload.get(key)
   if isinstance(value,dict):return {str(k):v for k,v in value.items()}
   if isinstance(value,list):return {str(i):v for i,v in enumerate(value)}
  if payload and all(isinstance(v,dict) for v in payload.values()):return {str(k):v for k,v in payload.items()}
  return {'$':payload}
 if isinstance(payload,list):return {str(i):v for i,v in enumerate(payload)}
 return {'$':payload}
def _field_changes(before,after):
 if not isinstance(before,dict) or not isinstance(after,dict):return [{'field':'$','before':before,'after':after}] if before!=after else []
 rows=[]
 for field in sorted(set(before)|set(after),key=str.casefold):
  if before.get(field)!=after.get(field):rows.append({'field':field,'before':before.get(field),'after':after.get(field),'change':'added' if field not in before else 'removed' if field not in after else 'changed'})
 return rows[:MAX_FIELD_DETAILS]
def structured_diff(base_path,current_path):
 before=_records(_load(base_path));after=_records(_load(current_path));added=sorted(set(after)-set(before));removed=sorted(set(before)-set(after));changed=[]
 for record_id in sorted(set(before)&set(after)):
  if before[record_id]!=after[record_id]:changed.append({'record_id':record_id,'fields':_field_changes(before[record_id],after[record_id])})
 return {'record_counts':{'base':len(before),'current':len(after),'added':len(added),'removed':len(removed),'changed':len(changed)},'added_record_ids':added[:MAX_RECORD_DETAILS],'removed_record_ids':removed[:MAX_RECORD_DETAILS],'changed_records':changed[:MAX_RECORD_DETAILS],'truncated':len(added)>MAX_RECORD_DETAILS or len(removed)>MAX_RECORD_DETAILS or len(changed)>MAX_RECORD_DETAILS}
def _registry_rows(database,table='tables',path_column='relative_path'):
 with closing(sqlite3.connect(database)) as c:
  c.row_factory=sqlite3.Row;return [dict(r) for r in c.execute(f'SELECT layer,{path_column} path,sha256 FROM {table}')]
def build_snapshot_diff(base,current,output,reports):
 output=Path(output);base=Path(base);current=Path(current);tables=_registry_rows(output/'catalogs/dead-signal-table-registry.sqlite');by={}
 for row in tables:by.setdefault(row['path'],{})[row['layer']]=row
 added=[];removed=[];changed=[];unchanged=[]
 for path,layers in sorted(by.items()):
  if 'base' not in layers:added.append(path)
  elif 'current' not in layers:removed.append(path)
  elif layers['base']['sha256']==layers['current']['sha256']:unchanged.append(path)
  else:changed.append(path)
 details=[]
 for path in changed[:MAX_TABLE_DETAILS]:details.append({'table':path,'diff':structured_diff(base/path,current/path)})
 pycs=_registry_rows(output/'catalogs/dead-signal-consumer-index.sqlite','files','path');pyc_by={}
 for row in pycs:pyc_by.setdefault(row['path'],{})[row['layer']]=row
 pyc_counts=Counter();pyc_paths={'added':[],'removed':[],'changed':[],'unchanged':[]}
 for path,layers in sorted(pyc_by.items()):
  state='added' if 'base' not in layers else 'removed' if 'current' not in layers else 'unchanged' if layers['base']['sha256']==layers['current']['sha256'] else 'changed';pyc_counts[state]+=1;pyc_paths[state].append(path)
 affected=[d.semantic_name for d in DEFINITIONS if d.source_table in set(changed+added)]
 impacted=[];graph_db=output/'catalogs/dead-signal-reference-graph.sqlite';changed_set=set(changed+added)
 if graph_db.is_file():
  with closing(sqlite3.connect(graph_db)) as c:
   c.row_factory=sqlite3.Row
   for row in c.execute('SELECT source_table,source_record_id,source_field,target_table,target_record_id,proof_state FROM edges'):
    if row['source_table'] in changed_set or row['target_table'] in changed_set:impacted.append(dict(row))
 report={'schema':'dead-signal-snapshot-data-diff','schema_version':SCHEMA_VERSION,'generated_at':_now(),'table_counts':{'added':len(added),'removed_or_patch_absent':len(removed),'changed':len(changed),'unchanged':len(unchanged)},'tables':{'added':added[:MAX_TABLE_DETAILS],'removed_or_patch_absent':removed[:MAX_TABLE_DETAILS],'changed':changed[:MAX_TABLE_DETAILS]},'changed_table_details':details,'pyc_counts':dict(pyc_counts),'pyc_paths':{k:v[:MAX_TABLE_DETAILS] for k,v in pyc_paths.items()},'affected_semantic_definitions':sorted(affected),'potentially_affected_website_records':impacted[:MAX_RECORD_DETAILS],'dependency_invalidation':{'changed_table_dependencies':len(changed)+len(added),'changed_pyc_dependencies':pyc_counts['changed']+pyc_counts['added'],'semantic_definitions_reevaluated':len(affected),'potentially_affected_website_records':len(impacted)},'policy':'Current is a patch layer. Base-only tables/records are reported as patch-absent and never asserted to be removed player-facing content.'};_atomic(Path(reports)/'snapshot-data-diff.json',report);return report
