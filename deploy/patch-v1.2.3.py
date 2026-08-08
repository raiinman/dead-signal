#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
app_path=root/'app.js'; index_path=root/'index.html'; data_path=root/'data/community-data.js'
app=app_path.read_text(encoding='utf-8')
index=index_path.read_text(encoding='utf-8')
data=data_path.read_text(encoding='utf-8')
app=app.replace("const SCHEMA=14, PLANNER_VERSION='1.2.2', MAX_CRADLES=8;","const SCHEMA=14, PLANNER_VERSION='1.2.3', MAX_CRADLES=8;")
needle="function renderEffectsBoard(){const list=gatherEffects();"
insert="function effectCategory(text){\n  const t=String(text||'').toLowerCase();\n  if(/hp|healing|heal |shield|damage reduction|dmg reduction|defen[sc]e|resistance|damage taken|surviv/.test(t))return 'Survivability';\n  if(/burn|frost|vortex|power surge|shock|blaze|unstable bomber|status|element|deviant energy|psi intensity/.test(t))return 'Status / Element';\n  if(/reload|magazine|ammo|movement|move speed|sprint|stamina|cooldown|duration|range|accuracy|stability|handling/.test(t))return 'Utility';\n  if(/damage|dmg|crit|weakspot|attack|weapon/.test(t))return 'Offense';\n  return 'Special / Conditional';\n}\nfunction gatherEffects(){\n  const out=[],seen=new Set();\n  const add=(source,text,cat=null)=>{\n    text=String(text||'').trim();if(!text)return;\n    const key=`${source}::${text}`;if(seen.has(key))return;seen.add(key);\n    out.push({source:String(source||'Effect'),text,cat:cat||effectCategory(text)});\n  };\n  for(const [slot,label] of weaponSlots){\n    const w=byId(D.weapons,state.weapons[slot]),c=state.weaponConfig[slot];if(!w)continue;\n    add(`${label} · ${w.name}`,w.feature);\n    const ammo=byId(D.ammo,c?.ammo);if(ammo)add(`Ammo · ${ammo.name}`,effectText(ammo));\n    const mod=byId(D.mods,c?.weaponMod);if(mod)add(`Weapon Mod · ${mod.name}${mod.variant?` <${mod.variant}>`:''}`,effectText(mod));\n    const cal=byId(D.calibrations,c?.calibration);if(cal)add(`Calibration · ${cal.name}`,effectText(cal));\n    for(const a of attachmentSlots){const x=byId(D.attachments,c?.attachments?.[a]);if(x)add(`${cap(a)} · ${x.name}`,effectText(x));}\n  }\n  const counts=setCounts();\n  for(const [id,count] of Object.entries(counts)){\n    const set=setOf(id);for(const b of setBonusEntries(set)){if(count>=Number(b.pieces))add(`${set?.name||id} · ${b.pieces}pc`,b.text);}\n  }\n  for(const slot of armorSlots){\n    const a=byId(D.armor,state.armor[slot]);if(a)add(`${slot} · ${a.name}`,a.feature);\n    const m=byId(D.mods,state.armorMods[slot]);if(m)add(`${slot} Mod · ${m.name}${m.variant?` <${m.variant}>`:''}`,effectText(m));\n  }\n  const dev=byId(D.deviations,state.deviation);if(dev){\n    for(const a of (dev.abilities||[]))add(`Deviation · ${dev.name}`,a);\n    add(`Deviation · ${dev.name}`,dev.description);\n  }\n  for(const id of state.cradles){const x=byId(D.cradles,id);if(x)add(`Cradle · ${x.name}`,x.effect);}\n  for(const [kind,id] of Object.entries(state.consumables)){const x=byId(D.consumables,id);if(x)add(`${cap(kind)} · ${x.name}`,effectText(x));}\n  return out;\n}\n\n"
if 'function gatherEffects(){' not in app:
    if needle not in app: raise RuntimeError('renderEffectsBoard anchor not found')
    app=app.replace(needle,insert+needle,1)
index=index.replace('1.2.2','1.2.3')
data=data.replace('\"version\":\"1.2.2-community\"','\"version\":\"1.2.3-community\"',1)
app_path.write_text(app,encoding='utf-8')
index_path.write_text(index,encoding='utf-8')
data_path.write_text(data,encoding='utf-8')
print('Dead Signal v1.2.3 report crash fix applied')
