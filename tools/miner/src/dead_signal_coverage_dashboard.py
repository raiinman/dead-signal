"""Post-promotion field/state coverage for the existing Miner UI."""
from __future__ import annotations
import json,os
from collections import Counter
from pathlib import Path

STATES=('published/resolved','exact evidence located but semantic proof pending','partial','unresolved evidence state','unresolved','not applicable')
def _row(name,states,report):
 counts=Counter(states);applicable=len(states)-counts['not applicable'];resolved=counts['published/resolved'];return {'field':name,'resolved':resolved,'applicable':applicable,'display':f'{resolved}/{applicable}' if applicable else 'N/A','states':{state:counts[state] for state in STATES},'evidence_report':report}
def build_coverage_dashboard(projection:dict,reports:Path|str):
 reports=Path(reports);weapons=projection.get('weapons') or [];lean={}
 try:lean={str(w.get('blueprint_id')):w for w in json.loads((reports.parent/'site'/'weapons.json').read_text(encoding='utf-8')).get('weapons',[])}
 except (OSError,ValueError,TypeError):lean={}
 def public(w):return lean.get(str(w.get('blueprint_id')),w)
 rows=[]
 rows.append(_row('Weapons',['published/resolved']*len(weapons),'published/site/weapons.json'))
 rows.append(_row('Rarity',['published/resolved' if (w.get('rarity') or {}).get('state')=='resolved-installed-game' else 'unresolved' for w in weapons],'published/site/weapon-evidence.json'))
 rows.append(_row('Descriptions',['published/resolved' if str(public(w).get('description_state','')).startswith('resolved-installed-game') else 'unresolved evidence state' if public(w).get('description') else 'unresolved' for w in weapons],'published/reports/weapon-description-prototype-projection.json'))
 ranged=[w for w in weapons if isinstance(w.get('ranged_stats'),dict)]
 rows.append(_row('Tier-I ranged gun stats',['published/resolved' if (w.get('handling') or {}).get('state')=='resolved-installed-game' else 'exact evidence located but semantic proof pending' if (w.get('handling') or {}).get('state')=='exact-record-located' else 'unresolved' for w in ranged],'published/reports/weapon-corpus-audit.json'))
 rows.append(_row('Firing mode',['published/resolved' if str((public(w).get('firing_mode') or {}).get('label_state','')).startswith('resolved-installed-game') else 'exact evidence located but semantic proof pending' if (w.get('firing_mode') or {}).get('raw_code') is not None else 'unresolved' for w in ranged],'published/reports/weapon-launch-gap-trace.json'))
 rows.append(_row('Projectile semantics',['published/resolved' if (((public(w).get('stats') or {}).get('projectile_count') if str(w.get('blueprint_id')) in lean else (w.get('ranged_stats') or {}).get('projectile_count'))) is not None else 'unresolved' for w in ranged],'published/reports/weapon-launch-gap-trace.json'))
 rows.append(_row('Cradle compatibility',['published/resolved' if ((w.get('compatibility') or {}).get('cradle') or {}).get('state','').startswith('resolved') else 'exact evidence located but semantic proof pending' if ((w.get('compatibility') or {}).get('cradle') or {}).get('candidate_count') else 'unresolved' for w in weapons],'published/reports/weapon-cradle-applicability.json'))
 rows.append(_row('Special Skill',['published/resolved' if (w.get('special_skill') or {}).get('text') else 'unresolved evidence state' if (w.get('special_skill') or {}).get('resolution') else 'unresolved' for w in weapons],'research/schema-trace-all-weapons.json'))
 blockers=sum(row['states']['exact evidence located but semantic proof pending']+row['states']['unresolved evidence state']+row['states']['unresolved'] for row in rows)
 payload={'schema':'dead-signal-coverage-dashboard','schema_version':1,'record_counts':{'fields':len(rows),'weapons':len(weapons),'blocker_slots':blockers},'fields':rows,'state_definitions':list(STATES)};path=reports/'dead-signal-coverage-dashboard.json';path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8');os.replace(tmp,path);return payload
