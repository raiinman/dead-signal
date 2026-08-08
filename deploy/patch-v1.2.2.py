#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
app_path=root/'app.js'; css_path=root/'styles.css'; index_path=root/'index.html'; data_path=root/'data/community-data.js'
app=app_path.read_text(encoding='utf-8')
css=css_path.read_text(encoding='utf-8')
index=index_path.read_text(encoding='utf-8')
data=data_path.read_text(encoding='utf-8')

app=app.replace("const SCHEMA=14, PLANNER_VERSION='1.2.1', MAX_CRADLES=8;","const SCHEMA=14, PLANNER_VERSION='1.2.2', MAX_CRADLES=8;")

start=app.index('function weaponReport(slot,label){')
end=app.index('function renderEffectsBoard()', start)
replacement="""function statCell(label,value){
  if(value===null||value===undefined||value==='')return '';
  return `<div><b>${esc(value)}</b><span>${esc(label)}</span></div>`;
}
function weaponStatsReport(w){
  const s=w?.stats||{};
  const cells=[
    statCell('DMG',s.damage),statCell('RPM',s.rpm),statCell('MAG',s.magazine),
    statCell('RELOAD',s.reload!=null?`${s.reload}s`:null),
    statCell('CRIT RATE',s.critRate!=null?`${s.critRate}%`:null),
    statCell('CRIT DMG',s.critDamage!=null?`${s.critDamage}%`:null),
    statCell('WEAKSPOT',s.weakspot!=null?`${s.weakspot}%`:null),
    statCell('RANGE',s.range),statCell('EFFECTIVE',s.effectiveRange),
    statCell('MOBILITY',s.mobility),statCell('PELLETS',s.pellets)
  ].filter(Boolean).join('');
  return cells?`<div class=\"report-stat-block\"><div class=\"report-stat-title\"><span>INDEXED ITEM STATS</span><small>Raw known record values · Tier/Star scaling not calculated</small></div><div class=\"report-stat-grid\">${cells}</div></div>`:`<div class=\"report-stat-block pending\"><span>INDEXED ITEM STATS</span><small>Detailed numeric stats are still pending verification for this record.</small></div>`;
}
function armorStatsInline(a){
  if(!a)return '';
  const cells=[statCell('HP',a.hp),statCell('POLLUTION',a.pollution)].filter(Boolean).join('');
  return cells?`<div class=\"report-stat-grid armor-stats\">${cells}</div>`:`<div class=\"report-stat-pending\">Base defensive stats pending verification.</div>`;
}
function equipmentDetail(x){
  if(!x)return '';
  const bits=[];
  if(Number.isFinite(Number(x.damageModifier))&&x.damageModifier!==null&&x.damageModifier!=='')bits.push(`Damage Modifier ${Number(x.damageModifier)>=0?'+':''}${x.damageModifier}%`);
  if(Array.isArray(x.effects))bits.push(...x.effects.filter(Boolean));
  else if(x.effect)bits.push(x.effect);
  else if(x.description)bits.push(x.description);
  return [...new Set(bits)].map(t=>`<small>${esc(t)}</small>`).join('');
}
function weaponReport(slot,label){
  const w=byId(D.weapons,state.weapons[slot]);if(!w)return '';
  const c=state.weaponConfig[slot],cal=byId(D.calibrations,c.calibration),bonus=calBonus(cal,c);
  const parts=[];
  if(c.ammo)parts.push(['Ammo',byId(D.ammo,c.ammo)]);if(c.weaponMod){const m=byId(D.mods,c.weaponMod);parts.push([`Mod · ${modInstanceText(m,c.weaponModConfig)}`,m])}if(cal)parts.push(['Calibration',cal]);
  for(const a of attachmentSlots)if(c.attachments[a])parts.push([cap(a),byId(D.attachments,c.attachments[a])]);
  const calRolls=cal&&bonus?`<div class=\"report-row\"><span>Calibration RNG</span><div><b>Attack ${pct(c.calibrationAttack)}</b><small>${esc(bonus.label)} ${pct(c.calibrationBonusValue)}</small><small>${esc(cal.style||'')}</small></div></div>`:'';
  const weaponEffect=w.feature?`<div class=\"report-row\"><span>Weapon Effect</span><div><small>${esc(w.feature)}</small></div></div>`:'';
  return `<div class=\"report-card\"><div class=\"report-head\"><span>${esc(label.toUpperCase())}</span><b>${esc(w.name)}</b><small>Gear Tier ${['','I','II','III','IV','V'][c.tier]||c.tier} · Blueprint Stars ${c.stars}★ · ${esc(w.type)}</small></div>${weaponStatsReport(w)}${weaponEffect}${parts.map(([k,x])=>`<div class=\"report-row\"><span>${esc(k)}</span><div><b>${esc(x?.name||'—')}</b>${x?.variant?` <small>&lt;${esc(x.variant)}&gt;</small>`:''}${equipmentDetail(x)}</div></div>`).join('')}${calRolls}</div>`;
}

function armorReport(){return `<div class=\"armor-report\">${armorSlots.map(slot=>{const a=byId(D.armor,state.armor[slot]),m=byId(D.mods,state.armorMods[slot]),cfg=state.armorConfig[slot],mcfg=state.armorModConfig[slot];return `<div class=\"armor-report-row\"><span>${slot}</span><div><b>${esc(a?.name||'—')}</b>${a?`<small>${esc(a.setName||'Standalone')} · Gear Tier ${['','I','II','III','IV','V'][cfg?.tier]||cfg?.tier} · Blueprint Stars ${cfg?.stars}★</small>${armorStatsInline(a)}`:''}${m?`<small class=\"armor-mod-line\"><b>Mod:</b> ${esc(m.name)}${m.variant?` &lt;${esc(m.variant)}&gt;`:''} · ${esc(modInstanceText(m,mcfg))}</small>${effectText(m)?`<small>${esc(effectText(m))}</small>`:''}`:''}${a?.feature?`<small class=\"key-effect\">${esc(a.feature)}</small>`:''}</div></div>`}).join('')}</div>`}
"""
app=app[:start]+replacement+app[end:]

old="""function renderBuildSystemsReport(){
  const dev=byId(D.deviations,state.deviation);const cons=Object.entries(state.consumables).map(([k,id])=>[k,byId(D.consumables,id)]).filter(([,x])=>x);
  return `<div class=\"system-report\">${dev?`<div><span>Deviation</span><b>${esc(dev.name)}</b></div>`:''}${cons.map(([k,x])=>`<div><span>${cap(k)}</span><b>${esc(x.name)}</b></div>`).join('')}<div><span>Cradles</span><b>${state.cradles.length}/${MAX_CRADLES}</b></div>${state.cradles.map(id=>{const x=byId(D.cradles,id);return x?`<p><b>${esc(x.name)}</b> — ${esc(x.effect)}</p>`:''}).join('')}</div>`;
}
"""
new="""function renderBuildSystemsReport(){
  const dev=byId(D.deviations,state.deviation);const cons=Object.entries(state.consumables).map(([k,id])=>[k,byId(D.consumables,id)]).filter(([,x])=>x);
  return `<div class=\"system-report\">${dev?`<div class=\"system-detail\"><span>Deviation</span><b>${esc(dev.name)}</b>${dev.abilities?.length?`<small>${esc(dev.abilities.join(' · '))}</small>`:''}${dev.description?`<small>${esc(dev.description)}</small>`:''}</div>`:''}${cons.map(([k,x])=>`<div class=\"system-detail\"><span>${cap(k)}</span><b>${esc(x.name)}</b>${equipmentDetail(x)}</div>`).join('')}<div><span>Cradles</span><b>${state.cradles.length}/${MAX_CRADLES}</b></div>${state.cradles.map(id=>{const x=byId(D.cradles,id);return x?`<p><b>${esc(x.name)}</b> — ${esc(x.effect)}</p>`:''}).join('')}</div>`;
}
"""
if old not in app: raise RuntimeError('Expected v1.2.1 build systems block not found')
app=app.replace(old,new)
app=app.replace('<div class=\"summary-section\"><h3>Weapons</h3>${weaponReport', '<div class=\"summary-section\"><h3>Weapons</h3><div class=\"summary-notice\">Equipped item stats are shown exactly as indexed. Final Tier/Star scaling and derived combat math remain intentionally deferred.</div>${weaponReport')
app=app.replace('<div class=\"summary-section\"><h3>Armor</h3>${armorReport()', '<div class=\"summary-section\"><h3>Armor</h3><div class=\"summary-notice\">Armor rows show every known indexed defensive stat plus equipped mod and key-armor effects.</div>${armorReport()')

index=index.replace('1.2.1','1.2.2')
data=data.replace('\"version\":\"1.2.1-community\"','\"version\":\"1.2.2-community\"',1)
marker='/* v1.2.2 loadout report: equipped raw stats without derived combat math */'
if marker not in css:
    css += """

/* v1.2.2 loadout report: equipped raw stats without derived combat math */
.report-stat-block{padding:9px 10px;border-top:1px solid rgba(255,255,255,.04);background:#090b0f}.report-stat-block.pending{display:grid;gap:3px;color:var(--muted)}.report-stat-title{display:flex;justify-content:space-between;gap:8px;align-items:baseline;margin-bottom:7px}.report-stat-title>span,.report-stat-block.pending>span{font-size:9px;letter-spacing:.1em;color:#d2d6de;font-weight:900}.report-stat-title>small,.report-stat-block.pending>small{font-size:8px;color:#777f8d;text-align:right}.report-stat-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px}.report-stat-grid>div{padding:6px 7px;border:1px solid rgba(255,255,255,.05);border-radius:6px;background:#0d1015;min-width:0}.report-stat-grid b{display:block;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.report-stat-grid span{display:block;margin-top:1px;font-size:8px;color:#7f8793;font-weight:800;letter-spacing:.06em}.report-stat-grid.armor-stats{grid-template-columns:repeat(2,minmax(0,92px));margin-top:5px}.report-stat-pending{font-size:8px;color:#747c88;margin-top:4px}.armor-mod-line{margin-top:6px!important;color:#c9cdd5!important}.armor-mod-line b{font-size:9px!important}.key-effect{color:#d8bd83!important}.system-report .system-detail{display:grid;grid-template-columns:64px 1fr;column-gap:8px;align-items:start}.system-report .system-detail>span{grid-row:1/4}.system-report .system-detail>small{grid-column:2;font-size:9px;color:#aeb4c0;line-height:1.35;margin-top:2px}.system-report .system-detail>b{grid-column:2}
@media(max-width:760px){.report-stat-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.report-stat-title{display:grid}.report-stat-title>small{text-align:left}}
"""

app_path.write_text(app,encoding='utf-8'); css_path.write_text(css,encoding='utf-8'); index_path.write_text(index,encoding='utf-8'); data_path.write_text(data,encoding='utf-8')
print('Dead Signal v1.2.2 loadout stats patch applied')
