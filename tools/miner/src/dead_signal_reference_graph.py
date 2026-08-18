"""Durable typed relationship graph; exact candidates never auto-promote."""
from __future__ import annotations
import json, os, sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION=1
PROOF_STATES=('structural-candidate','exact-record-reference','typed-relationship-proven','consumer-confirmed','semantic-proven','rejected')
PROOF_RANK={value:index for index,value in enumerate(PROOF_STATES[:-1])}|{'rejected':-1}
def _now(): return datetime.now(timezone.utc).isoformat()
def _atomic(path,payload):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8');os.replace(tmp,path)

class ReferenceGraph:
 def __init__(self,database):self.database=Path(database)
 def _connect(self):c=sqlite3.connect(self.database);c.row_factory=sqlite3.Row;return c
 def initialize(self):
  self.database.parent.mkdir(parents=True,exist_ok=True)
  with closing(self._connect()) as c,c:
   c.executescript('''CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE IF NOT EXISTS edges(id INTEGER PRIMARY KEY,source_table TEXT NOT NULL,source_record_id TEXT NOT NULL,source_field TEXT NOT NULL,source_value_json TEXT NOT NULL,source_layer TEXT NOT NULL,target_table TEXT NOT NULL,target_record_id TEXT NOT NULL,relationship_kind TEXT NOT NULL,proof_state TEXT NOT NULL,scope TEXT NOT NULL,role TEXT NOT NULL,provenance_json TEXT NOT NULL,parent_field_path TEXT,first_seen_snapshot TEXT,last_seen_snapshot TEXT,UNIQUE(source_table,source_record_id,source_field,source_value_json,source_layer,target_table,target_record_id,relationship_kind,scope,role)); CREATE INDEX IF NOT EXISTS edge_source ON edges(source_table,source_record_id); CREATE INDEX IF NOT EXISTS edge_target ON edges(target_table,target_record_id);''')
   c.execute("INSERT OR REPLACE INTO meta VALUES('schema_version',?)",(str(SCHEMA_VERSION),))
 def add_edge(self,**edge):
  proof=edge['proof_state'];
  if proof not in PROOF_STATES:raise ValueError(f'unknown proof state: {proof}')
  self.initialize();value=json.dumps(edge.get('source_value'),ensure_ascii=True,sort_keys=True);prov=json.dumps(edge.get('provenance') or {},ensure_ascii=True,sort_keys=True);seen=str(edge.get('snapshot') or '')
  values=(str(edge['source_table']),str(edge['source_record_id']),str(edge['source_field']),value,str(edge.get('source_layer') or 'unknown'),str(edge['target_table']),str(edge['target_record_id']),str(edge['relationship_kind']),proof,str(edge.get('scope') or 'variant-local'),str(edge.get('role') or 'reference'),prov,edge.get('parent_field_path'),seen,seen)
  with closing(self._connect()) as c,c:
   old=c.execute('''SELECT id,proof_state FROM edges WHERE source_table=? AND source_record_id=? AND source_field=? AND source_value_json=? AND source_layer=? AND target_table=? AND target_record_id=? AND relationship_kind=? AND scope=? AND role=?''',(values[0],values[1],values[2],values[3],values[4],values[5],values[6],values[7],values[9],values[10])).fetchone()
   if old:
    chosen=proof if PROOF_RANK[proof]>=PROOF_RANK[old['proof_state']] else old['proof_state'];c.execute('UPDATE edges SET proof_state=?,provenance_json=?,parent_field_path=?,last_seen_snapshot=? WHERE id=?',(chosen,prov,values[12],seen,old['id']));return old['id']
   return c.execute('INSERT INTO edges(source_table,source_record_id,source_field,source_value_json,source_layer,target_table,target_record_id,relationship_kind,proof_state,scope,role,provenance_json,parent_field_path,first_seen_snapshot,last_seen_snapshot) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',values).lastrowid
 def query(self,*,source_table=None,source_record_id=None,target_table=None,target_record_id=None,min_proof=None):
  clauses=[];args=[]
  for column,value in (('source_table',source_table),('source_record_id',source_record_id),('target_table',target_table),('target_record_id',target_record_id)):
   if value is not None:clauses.append(column+'=?');args.append(str(value))
  sql='SELECT * FROM edges'+((' WHERE '+' AND '.join(clauses)) if clauses else '')+' ORDER BY source_table,source_record_id,source_field,target_table,target_record_id'
  with closing(self._connect()) as c:rows=[dict(r) for r in c.execute(sql,args)]
  return [r for r in rows if min_proof is None or PROOF_RANK[r['proof_state']]>=PROOF_RANK[min_proof]]

def seed_weapon_graph(graph,weapons,snapshot=''):
 count=0
 def add(**kwargs):
  nonlocal count;graph.add_edge(snapshot=snapshot,source_layer='published',provenance={'producer':'published/data/weapons.json','policy':'existing-exact-miner-output'},**kwargs);count+=1
 for weapon in weapons:
  bp=weapon.get('blueprint_id');item=weapon.get('item_id');proto=weapon.get('prototype_id')
  if bp in (None,''):continue
  if item not in (None,''):add(source_table='weapon_blueprint',source_record_id=bp,source_field='item_id',source_value=item,target_table='item',target_record_id=item,relationship_kind='blueprint-to-item',proof_state='typed-relationship-proven',scope='variant-local',role='owner')
  if proto not in (None,''):add(source_table='weapon_blueprint',source_record_id=bp,source_field='prototype_id',source_value=proto,target_table='game_common/data/weapon_prototype_data.json',target_record_id=proto,relationship_kind='blueprint-to-prototype',proof_state='typed-relationship-proven',scope='variant-local',role='producer')
  ranged=weapon.get('ranged_stats') or {};pattern=ranged.get('bullet_pattern_id')
  if pattern not in (None,''):add(source_table='weapon',source_record_id=bp,source_field='ranged_stats.bullet_pattern_id',source_value=pattern,target_table='client_data/bullet_pattern_data.json',target_record_id=pattern,relationship_kind='bullet-pattern',proof_state='semantic-proven' if ranged.get('projectile_count') not in (None,'') else 'typed-relationship-proven',scope='family-shared',role='producer')
  for tier in weapon.get('tiers') or []:
   gun=tier.get('gun_no');tier_item=tier.get('item_id')
   if gun not in (None,'') and tier_item not in (None,''):add(source_table='item',source_record_id=tier_item,source_field='gun_no',source_value=gun,target_table='game_common/data/gun_base_params_data.json',target_record_id=gun,relationship_kind='tier-item-to-gun',proof_state='typed-relationship-proven',scope='variant-local',role='owner')
  ammo=weapon.get('ammo_configuration') or {};source=ammo.get('source') or {}
  if ammo.get('resolution_status')=='proven-table-relationship' and source.get('slot_record_id'):
   add(source_table=source.get('item_to_gun_table','game_common/data/item_to_gun_mapping_data.json'),source_record_id=source.get('item_to_gun_record_id',item),source_field='accessory_slot',source_value=ammo.get('accessory_slot'),target_table=source.get('slot_table','game_common/data/gun_accessory_slot_params_data.json'),target_record_id=source['slot_record_id'],relationship_kind='item-gun-accessory-slot',proof_state='semantic-proven',scope='variant-local',role='consumer')
 return count

def run_reference_graph(weapons_path,output,reports):
 payload=json.loads(Path(weapons_path).read_text(encoding='utf-8'));db=Path(output)/'catalogs'/'dead-signal-reference-graph.sqlite';graph=ReferenceGraph(db);graph.initialize();seeded=seed_weapon_graph(graph,payload.get('weapons') or [],str(payload.get('snapshot_id') or ''))
 rows=graph.query();states=Counter(r['proof_state'] for r in rows);kinds=Counter(r['relationship_kind'] for r in rows);summary={'schema':'dead-signal-reference-graph-summary','schema_version':SCHEMA_VERSION,'generated_at':_now(),'database':str(db),'record_counts':{'edges':len(rows),'seed_operations':seeded},'proof_state_counts':dict(sorted(states.items())),'relationship_kind_counts':dict(sorted(kinds.items())),'policy':'Only existing typed Miner outputs seed proven edges. Structural candidates remain candidates and never auto-promote.'};_atomic(Path(reports)/'reference-graph-summary.json',summary);return {'summary':summary,'database':str(db)}
