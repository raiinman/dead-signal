"""Concise semantic website delta for lean player-facing projections."""
from __future__ import annotations
import hashlib,json,os
from pathlib import Path
from typing import Any
FIELDS={'name':lambda r:r.get('name'),'rarity':lambda r:r.get('rarity'),'category':lambda r:r.get('category'),'tier_progression':lambda r:(r.get('progression') or {}).get('tiers'),'promoted_stats':lambda r:r.get('stats'),'firing_mode':lambda r:r.get('firing_mode'),'projectile_count':lambda r:(r.get('projectiles') or {}).get('count'),'description':lambda r:(r.get('description'),r.get('description_state')),'special_skill':lambda r:r.get('special_skill'),'acquisition':lambda r:r.get('acquisition'),'compatibility':lambda r:r.get('compatibility'),'image_reference':lambda r:r.get('image')}
def _hash(value):return hashlib.sha256(json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def build_site_delta(previous:dict[str,Any]|None,current:dict[str,Any],destination:Path|str):
 previous=previous or {'weapons':[]};before={str(r.get('blueprint_id')):r for r in previous.get('weapons',[]) if isinstance(r,dict)};after={str(r.get('blueprint_id')):r for r in current.get('weapons',[]) if isinstance(r,dict)};added=sorted(set(after)-set(before));removed=sorted(set(before)-set(after));changed=[]
 for bid in sorted(set(before)&set(after)):
  names=[name for name,getter in FIELDS.items() if getter(before[bid])!=getter(after[bid])]
  if names:changed.append({'blueprint_id':bid,'semantic_fields':names,'before_hash':_hash({n:FIELDS[n](before[bid]) for n in names}),'after_hash':_hash({n:FIELDS[n](after[bid]) for n in names})})
 report={'schema':'dead-signal-site-delta','schema_version':1,'before_hash':_hash(previous),'after_hash':_hash(current),'record_counts':{'added':len(added),'removed_or_unpublished':len(removed),'changed':len(changed)},'added_blueprint_ids':added,'removed_or_unpublished_blueprint_ids':removed,'changed':changed,'policy':'Removal from a projection is conservative publication state and does not by itself prove deleted game content.'};path=Path(destination);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8');os.replace(tmp,path);return report
