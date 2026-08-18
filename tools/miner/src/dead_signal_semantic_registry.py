"""Declarative registry of proven player-facing field semantics."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any
import json, os
from pathlib import Path

@dataclass(frozen=True)
class SemanticDefinition:
 semantic_name:str; domain:str; owner_type:str; source_table:str; source_field:str
 relationship_prerequisite:tuple[str,...]; scope:str; precedence:int; raw_display:str
 normalization:str|None; required_proof_level:str; publication_state:str; version:int
 first_proven_snapshot:str; notes:str=''

GUN_BASE_TABLE='game_common/data/gun_base_params_data.json'
DEFINITIONS=(
 SemanticDefinition('ads_time','Weapons','tier_one_gun',GUN_BASE_TABLE,'ads_time',('exact-owner-record',),'variant-local',2,'display',None,'typed-relationship-proven','resolved-installed-game',1,'v1.5.14.61'),
 SemanticDefinition('bullet_speed','Weapons','tier_one_gun',GUN_BASE_TABLE,'bullet_speed',('exact-owner-record',),'variant-local',2,'display',None,'typed-relationship-proven','resolved-installed-game',1,'v1.5.14.61'),
 SemanticDefinition('reload_score','Weapons','tier_one_gun',GUN_BASE_TABLE,'reload_loop_affix_value',('exact-owner-record',),'variant-local',2,'display',None,'typed-relationship-proven','resolved-installed-game',1,'v1.5.14.61'),
 SemanticDefinition('reload_time_seconds','Weapons','tier_one_gun',GUN_BASE_TABLE,'reload_loop_time',('exact-owner-record',),'variant-local',2,'display',None,'typed-relationship-proven','resolved-installed-game',1,'v1.5.14.61'),
 SemanticDefinition('magazine','Weapons','tier_one_gun',GUN_BASE_TABLE,'weapon_magazine_size_affix_value',('exact-owner-record',),'variant-local',2,'display',None,'typed-relationship-proven','resolved-installed-game',1,'v1.5.14.61','Internal score remains distinct from final aggregated magazine semantics.'),
 SemanticDefinition('mobility','Weapons','tier_one_gun',GUN_BASE_TABLE,'weapon_mobility',('exact-owner-record',),'variant-local',2,'display',None,'typed-relationship-proven','resolved-installed-game',1,'v1.5.14.61'),
 SemanticDefinition('effective_range','Weapons','tier_one_gun',GUN_BASE_TABLE,'weapon_range_affix_value',('exact-owner-record',),'variant-local',2,'display',None,'typed-relationship-proven','resolved-installed-game',1,'v1.5.14.61'),
 SemanticDefinition('range_score','Weapons','tier_one_gun',GUN_BASE_TABLE,'weapon_range_value',('exact-owner-record',),'variant-local',2,'raw',None,'typed-relationship-proven','resolved-installed-game',1,'v1.5.14.61'),
 SemanticDefinition('fire_rate_display_rpm','Weapons','tier_one_gun',GUN_BASE_TABLE,'weapon_rpm_affix_value',('exact-owner-record',),'variant-local',2,'display',None,'typed-relationship-proven','resolved-installed-game',1,'v1.5.14.61'),
 SemanticDefinition('firing_mode','Weapons','tier_one_gun',GUN_BASE_TABLE,'default_shoot_mode',('exact-owner-record','static-enum'),'variant-local',2,'display','installed-ShootMode-map','consumer-confirmed','resolved-installed-game',1,'v1.5.14.61'),
 SemanticDefinition('projectile_count','Weapons','bullet_pattern', 'client_data/bullet_pattern_data.json','bullet_num',('exact-owner-record',),'family-shared',1,'display',None,'semantic-proven','resolved-installed-game',1,'v1.5.14.61'),
 SemanticDefinition('weapon_description','Weapons','weapon_prototype', 'game_common/data/weapon_prototype_data.json','prototype_desc',('exact-owner-record','english-translation'),'family-shared',1,'display','exact-English-translation','semantic-proven','resolved-installed-game',1,'v1.5.14.61'),
)
BY_NAME={definition.semantic_name:definition for definition in DEFINITIONS}
def get_semantic(name:str)->SemanticDefinition: return BY_NAME[name]
def list_semantics(domain:str|None=None)->list[dict[str,Any]]: return [asdict(d) for d in DEFINITIONS if domain is None or d.domain==domain]
def write_semantic_registry_report(reports:Path|str)->dict[str,Any]:
 definitions=list_semantics();payload={'schema':'dead-signal-semantic-registry','schema_version':1,'record_counts':{'definitions':len(definitions)},'definitions':definitions,'policy':'Definitions describe proven semantics; publication still requires every declared proof prerequisite.'};path=Path(reports)/'semantic-registry.json';path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8');os.replace(tmp,path);return payload
