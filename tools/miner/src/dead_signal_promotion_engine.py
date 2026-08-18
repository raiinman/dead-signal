"""Auditable semantic promotion evaluator."""
from __future__ import annotations
from dataclasses import asdict
from typing import Any
from dead_signal_semantic_registry import SemanticDefinition,get_semantic

def promote(definition:SemanticDefinition|str,*,raw_value:Any,evidence:set[str]|list[str]|tuple[str,...],scope:str,provenance:dict[str,Any]|None=None)->dict[str,Any]:
 if isinstance(definition,str):definition=get_semantic(definition)
 evidence=set(evidence);missing=[item for item in definition.relationship_prerequisite if item not in evidence];reasons=[]
 if missing:reasons.append('missing-required-evidence: '+', '.join(missing))
 if scope!=definition.scope:reasons.append(f'scope-mismatch: expected {definition.scope}, got {scope}')
 if raw_value in (None,''):reasons.append('source-value-missing')
 state=definition.publication_state if not reasons else 'unresolved'
 return {'value':raw_value if not reasons else None,'raw_value':raw_value,'state':state,'scope':scope,'precedence':definition.precedence,'provenance':provenance,'semantic_definition_version':definition.version,'semantic_name':definition.semantic_name,'reasons_not_promoted':reasons}
