"""Typed family inheritance policy with local evidence precedence."""
from __future__ import annotations
FAMILY_RULES={'shared-prototype':{'allowed':{'weapon_description'},'precedence':1},'bullet-pattern':{'allowed':{'projectiles','projectile_count','bullet_speed','falloff'},'precedence':1}}
def inherit(family_type,semantic_group,*,local=None,shared=None):
 rule=FAMILY_RULES.get(family_type)
 if local is not None:return {'accepted':True,'value':local,'scope':'variant-local','precedence':2,'reason':'variant-local-overrides-family-shared'}
 if not rule:return {'accepted':False,'value':None,'scope':None,'precedence':0,'reason':'unknown-family-type'}
 if semantic_group not in rule['allowed']:return {'accepted':False,'value':None,'scope':'family-shared','precedence':rule['precedence'],'reason':'semantic-group-not-allowed'}
 if shared is None:return {'accepted':False,'value':None,'scope':'family-shared','precedence':rule['precedence'],'reason':'shared-evidence-missing'}
 return {'accepted':True,'value':shared,'scope':'family-shared','precedence':rule['precedence'],'reason':'typed-family-inheritance'}
