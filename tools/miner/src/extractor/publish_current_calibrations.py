from __future__ import annotations
from collections import defaultdict
import json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_CURRENT_COUNT=94
EXPECTED_MAIN_RANGES={"Rare":(18.0,25.0),"Epic":(26.0,33.0),"Legendary":(34.0,50.0)}
EXPECTED_SECONDARIES={
"Rare":(("Weakspot DMG",frozenset({"E0300"}),12.0,18.0),("Crit Rate",frozenset({"E0100"}),8.0,12.0),("Elemental DMG",frozenset({"E3200","E3300","E3400","E3800"}),12.0,18.0),("Crit DMG",frozenset({"E0200"}),20.0,30.0)),
"Epic":(("Weakspot DMG",frozenset({"E0300"}),15.0,21.0),("Crit Rate",frozenset({"E0100"}),10.0,14.0),("Elemental DMG",frozenset({"E3200","E3300","E3400","E3800"}),12.0,18.0),("Crit DMG",frozenset({"E0200"}),25.0,35.0)),
"Legendary":(("Weakspot DMG",frozenset({"E0300"}),18.0,24.0),("Crit Rate",frozenset({"E0100"}),12.0,16.0),("Elemental DMG",frozenset({"E3200","E3300","E3400","E3800"}),15.0,20.0),("Crit DMG",frozenset({"E0200"}),30.0,40.0)),}
EXPECTED_SECONDARY_WEIGHTS=[200,200,200,200]

def utc_now(): return datetime.now(timezone.utc).isoformat()
def _numeric(v): return isinstance(v,(int,float)) and not isinstance(v,bool)
def _same(a,b): return math.isclose(float(a),float(b),rel_tol=0.0,abs_tol=1e-9)
def _buff_key(row):
    v=row.get("buff_id")
    return f"{v[0]}:{v[1]}" if isinstance(v,(list,tuple)) and len(v)==2 and v[0] not in (None,"") and v[1] not in (None,"") else None

def is_current_variant(row):
    if not bool(row.get("is_valid",True)): return False
    exp=EXPECTED_MAIN_RANGES.get(str(row.get("rarity") or "").strip())
    roll=row.get("roll_range")
    if exp is None or not isinstance(roll,dict): return False
    lo,hi=roll.get("minimum_percent"),roll.get("maximum_percent")
    return _numeric(lo) and _numeric(hi) and _same(lo,exp[0]) and _same(hi,exp[1])

def _candidate_term(affix):
    terms=affix.get("terms")
    if not isinstance(terms,list): return None
    candidates=[]
    for term in terms:
        if not isinstance(term,dict): continue
        ids=frozenset(str(v) for v in term.get("affix_ids") or [] if str(v))
        lo,hi=term.get("min_val"),term.get("max_val")
        if ids and _numeric(lo) and _numeric(hi): candidates.append((ids,float(lo)*100.0,float(hi)*100.0))
    return candidates[0] if len(candidates)==1 else None

def secondary_roll_candidates(row):
    rarity=str(row.get("rarity") or "").strip(); expected=EXPECTED_SECONDARIES.get(rarity)
    weights=row.get("affix_ids_weight"); affixes=row.get("affixes")
    if expected is None or list(weights or [])!=EXPECTED_SECONDARY_WEIGHTS or not isinstance(affixes,list) or len(affixes)!=4: return None
    actual=[]
    for i,affix in enumerate(affixes):
        if not isinstance(affix,dict): return None
        term=_candidate_term(affix)
        if term is None: return None
        ids,lo,hi=term; actual.append({"affix_id":affix.get("affix_id"),"stat_ids":ids,"minimum_percent":lo,"maximum_percent":hi,"weight":int(weights[i])})
    result=[]; used=set()
    for label,ids,lo,hi in expected:
        matches=[(i,c) for i,c in enumerate(actual) if i not in used and c["stat_ids"]==ids and _same(c["minimum_percent"],lo) and _same(c["maximum_percent"],hi)]
        if len(matches)!=1: return None
        i,c=matches[0]; used.add(i); result.append({"label":label,"affix_id":c["affix_id"],"stat_ids":sorted(c["stat_ids"]),"minimum_percent":lo,"maximum_percent":hi,"weight":c["weight"]})
    return result if len(used)==4 else None

def _normalized_variants(payload):
    out={}
    if not isinstance(payload,dict): return out
    for row in payload.get("calibrations") or []:
        if isinstance(row,dict) and row.get("item_id") not in (None,""): out[str(row.get("item_id"))]=row
    return out

def project(payload,normalized_payload=None):
    if payload.get("schema")!="dead-signal-calibrations": raise ValueError("Expected dead-signal-calibrations compact contract")
    source=payload.get("families")
    if not isinstance(source,list): raise ValueError("Calibration compact contract must contain families")
    normalized=_normalized_variants(normalized_payload); grouped=defaultdict(list); unkeyed=[]
    for family in source:
        if not isinstance(family,dict): continue
        for src in family.get("variants",[]):
            if not isinstance(src,dict): continue
            row=dict(src); norm=normalized.get(str(row.get("item_id")))
            if norm: row["affix_ids_weight"]=norm.get("affix_ids_weight") or []
            key=_buff_key(row)
            (grouped[key] if key is not None else unkeyed).append(row)
    current=[]; review=list(unkeyed); ambiguous=[f"missing-buff-id:{r.get('item_id')}" for r in unkeyed]; failures=[]
    for key,variants in sorted(grouped.items()):
        selected_rows=[r for r in variants if is_current_variant(r)]; non=[r for r in variants if r not in selected_rows]
        if len(selected_rows)!=1: ambiguous.append(f"buff:{key}"); review.extend(variants); continue
        selected=dict(selected_rows[0]); secondaries=secondary_roll_candidates(selected)
        if secondaries is None: failures.append(f"buff:{key}"); review.extend(variants); continue
        selected["secondary_roll_candidates"]=secondaries; selected["secondary_roll_rule"]="exactly-one-candidate-selected; equal observed source weight 200 each"
        item_id=selected.get("item_id") or selected.get("id")
        current.append({"canonical_id":f"ds-cal-{item_id}" if item_id not in (None,"") else f"ds-cal-buff-{key.replace(':','-')}","family_key":f"buff:{key}","name":selected.get("name") or "Unnamed","variant_count":1,"variant_status":"current-system-selected-from-shared-buff-identity-and-proven-main-plus-secondary-rolls","variants":[selected]}); review.extend(non)
    ids=[r.get("canonical_id") for r in current]; dup=sorted({v for v in ids if v and ids.count(v)>1}); ready=len(current)==EXPECTED_CURRENT_COUNT and not ambiguous and not failures and not dup and all(ids)
    return {"schema":"dead-signal-calibrations","schema_version":2,"generated_utc":utc_now(),"source_generated_utc":payload.get("source_generated_utc") or payload.get("generated_utc"),"record_counts":{"current_families":len(current),"legacy_or_noncurrent_variants":len(review),"ambiguous_families":len(ambiguous),"secondary_pool_failures":len(failures)},"publication_status":"ready-current-system" if ready else "blocked-current-system-classification","current_system_rule":"shared mined buff_id identity plus exactly one valid Rare/Epic/Legendary variant with its proven Weapon DMG RNG range and exact one-of-four secondary pool","main_roll_semantics":{"label":"Weapon DMG","stat_id":"D0102","aggregation":"same additive Attack-ratio bucket as D0101","rarity_ranges_percent":{n:list(v) for n,v in EXPECTED_MAIN_RANGES.items()}},"secondary_roll_semantics":{"selection_count":1,"observed_candidate_weights":EXPECTED_SECONDARY_WEIGHTS,"weight_interpretation":"equal observed source weights; no probability percentage is invented","rarity_candidates":{rarity:[{"label":label,"stat_ids":sorted(ids),"minimum_percent":lo,"maximum_percent":hi} for label,ids,lo,hi in candidates] for rarity,candidates in EXPECTED_SECONDARIES.items()}},"expected_current_families":EXPECTED_CURRENT_COUNT,"duplicate_canonical_ids":dup,"ambiguous_family_ids":sorted(ambiguous),"secondary_pool_failure_ids":sorted(failures),"families":sorted(current,key=lambda r:(str(r.get("name") or "").casefold(),str(r.get("canonical_id") or ""))),"legacy_or_noncurrent_review":review}
def project_file(path,normalized_path=None):
    path=Path(path); payload=json.loads(path.read_text(encoding="utf-8")); normalized_payload=json.loads(Path(normalized_path).read_text(encoding="utf-8")) if normalized_path is not None and Path(normalized_path).is_file() else None; projected=project(payload,normalized_payload); tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(json.dumps(projected,ensure_ascii=False,indent=2),encoding="utf-8"); tmp.replace(path); return projected
