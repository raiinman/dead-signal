#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
app_path=root/'app.js'; css_path=root/'styles.css'; index_path=root/'index.html'; data_path=root/'data/community-data.js'
app=app_path.read_text(encoding='utf-8'); css=css_path.read_text(encoding='utf-8'); index=index_path.read_text(encoding='utf-8'); data=data_path.read_text(encoding='utf-8')

app=app.replace("const SCHEMA=14, PLANNER_VERSION='1.2.4', MAX_CRADLES=8;","const SCHEMA=14, PLANNER_VERSION='1.2.5', MAX_CRADLES=8;")
helper="""const gameRarityKey=r=>{\n  const v=String(r||'').trim().toLowerCase();\n  if(v==='normal'||v==='white')return 'normal';\n  if(v==='common'||v==='green'||v==='uncommon')return 'common';\n  if(v==='rare'||v==='blue'||v==='fine')return 'rare';\n  if(v==='epic'||v==='purple')return 'epic';\n  if(v==='legendary'||v==='gold')return 'legendary';\n  if(v==='mythic'||v==='red')return 'mythic';\n  return '';\n};\nconst rarityClass=x=>{const k=gameRarityKey(x?.rarity);return k?`has-rarity rarity-${k}`:''};\nconst rarityBadge=x=>{const k=gameRarityKey(x?.rarity);return k?`<span class=\"rarity-badge rarity-${k}\"><i></i>${esc(x.rarity)}</span>`:''};\n"""
anchor="const effectText=x=>x?.effect||x?.description||fmtList(x?.effects)||fmtList(x?.attributes)||(Number.isFinite(x?.damageModifier)?`Damage Modifier +${x.damageModifier}%`:'');\n"
if helper not in app:
    if anchor not in app: raise RuntimeError('rarity helper anchor missing')
    app=app.replace(anchor,anchor+helper)

app=app.replace('<article class="weapon-card ${w?\'filled\':\'\'}">','<article class="weapon-card ${w?\'filled\':\'\'} ${rarityClass(w)}">')
app=app.replace('<div class="subtle">${w?esc(`${w.type} · ${w.rarity}`):\'Choose a weapon\'}</div>${w?coverageBadge(w):\'\'}', '<div class="subtle">${w?esc(w.type):\'Choose a weapon\'}</div>${w?`${rarityBadge(w)}${coverageBadge(w)}`:\'\'}')
app=app.replace('<article class="gear-card ${a?\'filled\':\'\'}">','<article class="gear-card ${a?\'filled\':\'\'} ${rarityClass(a)}">')
app=app.replace('<div class="subtle">${a?esc(`${a.setName||\'Standalone\'} · ${a.rarity||\'\'}`):\'Choose armor\'}</div>${quality}', '<div class="subtle">${a?esc(a.setName||\'Standalone\'):\'Choose armor\'}</div>${a?rarityBadge(a):\'\'}${quality}')

old="function partButton(type,label,slot,key,x){\n  return `<div class=\"mini-select\"><button data-pick=\"${type}\" data-slot=\"${slot}\" data-subslot=\"${key}\"><span><b>${esc(label)}</b><small>${esc(x?([x.variant,x.style,x.rarity].filter(Boolean).join(' · ')):'')}</small></span><span class=\"choice\">${esc(x?.name||'Select')} <i>›</i></span></button>${x&&effectText(x)?`<div class=\"effect\">${esc(effectText(x))}</div>`:''}</div>`;\n}\n"
new="function partButton(type,label,slot,key,x){\n  return `<div class=\"mini-select ${rarityClass(x)}\"><button data-pick=\"${type}\" data-slot=\"${slot}\" data-subslot=\"${key}\"><span><b>${esc(label)}</b><small>${esc(x?([x.variant,x.style].filter(Boolean).join(' · ')):'')}</small></span><span class=\"choice\"><span>${esc(x?.name||'Select')}${x?rarityBadge(x):''}</span> <i>›</i></span></button>${x&&effectText(x)?`<div class=\"effect\">${esc(effectText(x))}</div>`:''}</div>`;\n}\n"
if old not in app: raise RuntimeError('partButton block missing')
app=app.replace(old,new)
app=app.replace('return `<div class="mod-instance"><div class="mod-instance-head">','return `<div class="mod-instance ${rarityClass(mod)}"><div class="mod-instance-head">')
app=app.replace('<b>${esc(mod.name)}${mod.variant?` &lt;${esc(mod.variant)}&gt;`:\'\'}</b></div><small>Fixed sub-attributes', '<b>${esc(mod.name)}${mod.variant?` &lt;${esc(mod.variant)}&gt;`:\'\'}</b>${rarityBadge(mod)}</div><small>Fixed sub-attributes')
app=app.replace('return `<div class="calibration-box">\n    <div class="cal-head">', 'return `<div class="calibration-box ${rarityClass(cal)}">\n    <div class="cal-head">')
app=app.replace('<small>${esc(cal.style||\'\')} · ${esc(cal.rarity||\'\')}</small></div><div>${coverageBadge(cal)}', '<small>${esc(cal.style||\'\')}</small>${rarityBadge(cal)}</div><div>${coverageBadge(cal)}')
app=app.replace('<div class="mini-select"><button data-pick="armorMod" data-slot="${slot}">', '<div class="mini-select ${rarityClass(m)}"><button data-pick="armorMod" data-slot="${slot}">')
app=app.replace('<span><b>${slot} Mod</b><small>${esc(m?.variant||\'\')}</small></span><span class="choice">${esc(m?.name||\'Select\')} <i>›</i></span>', '<span><b>${slot} Mod</b><small>${esc(m?.variant||\'\')}</small></span><span class="choice"><span>${esc(m?.name||\'Select\')}${m?rarityBadge(m):\'\'}</span> <i>›</i></span>')

old="function systemCard(label,x,type,subslot,desc){return `<article class=\"system-card ${x?'filled':''}\"><div class=\"slot-label\">${label}</div><div class=\"item-name\">${esc(x?.name||'Empty')}</div><div class=\"subtle\">${esc(desc)}</div>${x?`<div>${sourcePills(x)}</div>`:''}<button class=\"select-button\" data-pick=\"${type}\" ${subslot?`data-subslot=\"${subslot}\"`:''}>${x?'Change':'Select'}</button></article>`}\n"
new="function systemCard(label,x,type,subslot,desc){return `<article class=\"system-card ${x?'filled':''} ${rarityClass(x)}\"><div class=\"slot-label\">${label}</div><div class=\"item-name\">${esc(x?.name||'Empty')}</div>${x?rarityBadge(x):''}<div class=\"subtle\">${esc(desc)}</div>${x?`<div>${sourcePills(x)}</div>`:''}<button class=\"select-button\" data-pick=\"${type}\" ${subslot?`data-subslot=\"${subslot}\"`:''}>${x?'Change':'Select'}</button></article>`}\n"
if old not in app: raise RuntimeError('systemCard missing')
app=app.replace(old,new)
app=app.replace('<div><b>${esc(set?.name||id)}</b>${quality}</div><span>${count}/${total}</span>', '<div><b>${esc(set?.name||id)}</b>${set?rarityBadge(set):\'\'}${quality}</div><span>${count}/${total}</span>')
app=app.replace('return `<div class="report-card"><div class="report-head">', 'return `<div class="report-card ${rarityClass(w)}"><div class="report-head">')
app=app.replace('<b>${esc(w.name)}</b><small>Gear Tier', '<b>${esc(w.name)}</b>${rarityBadge(w)}<small>Gear Tier')
app=app.replace('<div class="report-row"><span>${esc(k)}</span><div><b>${esc(x?.name||\'—\')}</b>${x?.variant?', '<div class="report-row ${rarityClass(x)}"><span>${esc(k)}</span><div><b>${esc(x?.name||\'—\')}</b>${x?rarityBadge(x):\'\'}${x?.variant?')
start=app.index('function armorReport(){')
end=app.index('function effectCategory', start)
armor_fn="""function armorReport(){return `<div class=\"armor-report\">${armorSlots.map(slot=>{const a=byId(D.armor,state.armor[slot]),m=byId(D.mods,state.armorMods[slot]),cfg=state.armorConfig[slot],mcfg=state.armorModConfig[slot];return `<div class=\"armor-report-row ${rarityClass(a)}\"><span>${slot}</span><div><b>${esc(a?.name||'—')}</b>${a?`${rarityBadge(a)}<small>${esc(a.setName||'Standalone')} · Gear Tier ${['','I','II','III','IV','V'][cfg?.tier]||cfg?.tier} · Blueprint Stars ${cfg?.stars}★</small>${armorStatsInline(a)}`:''}${m?`<small class=\"armor-mod-line ${rarityClass(m)}\"><b>Mod:</b> ${esc(m.name)}${rarityBadge(m)}${m.variant?` &lt;${esc(m.variant)}&gt;`:''} · ${esc(modInstanceText(m,mcfg))}</small>${effectText(m)?`<small>${esc(effectText(m))}</small>`:''}`:''}${a?.feature?`<small class=\"key-effect\">${esc(a.feature)}</small>`:''}</div></div>`}).join('')}</div>`}\n"""
app=app[:start]+armor_fn+app[end:]
start=app.index('function renderBuildSystemsReport(){')
end=app.index('\nfunction dataPool()', start)
systems_fn="""function renderBuildSystemsReport(){\n  const dev=byId(D.deviations,state.deviation);const cons=Object.entries(state.consumables).map(([k,id])=>[k,byId(D.consumables,id)]).filter(([,x])=>x);\n  return `<div class=\"system-report\">${dev?`<div class=\"system-detail ${rarityClass(dev)}\"><span>Deviation</span><b>${esc(dev.name)}</b>${rarityBadge(dev)}${dev.abilities?.length?`<small>${esc(dev.abilities.join(' · '))}</small>`:''}${dev.description?`<small>${esc(dev.description)}</small>`:''}</div>`:''}${cons.map(([k,x])=>`<div class=\"system-detail ${rarityClass(x)}\"><span>${cap(k)}</span><b>${esc(x.name)}</b>${rarityBadge(x)}${equipmentDetail(x)}</div>`).join('')}<div><span>Cradles</span><b>${state.cradles.length}/${MAX_CRADLES}</b></div>${state.cradles.map(id=>{const x=byId(D.cradles,id);return x?`<p><b>${esc(x.name)}</b> — ${esc(x.effect)}</p>`:''}).join('')}</div>`;\n}\n"""
app=app[:start]+systems_fn+app[end:]
old="function pickerCard(x){const fk=favoriteKey(pick.type,x.id),fav=favorites.has(fk),facts=pickerFacts(x);return `<div class=\"pick-card\"><button class=\"fav ${fav?'active':''}\" data-fav-type=\"${pick.type}\" data-fav-id=\"${esc(x.id)}\" title=\"Favorite\">★</button><button class=\"pick\" data-select=\"${esc(x.id)}\"><strong>${esc(x.name)}</strong><span>${esc([x.type,x.slot,x.setName,x.rarity,x.style,x.category].filter(Boolean).join(' · '))}</span>${coverageBadge(x)}${facts?`<div class=\"picker-facts\">${esc(facts)}</div>`:''}${x.feature?`<div class=\"effect feature\">${esc(x.feature)}</div>`:''}${effectText(x)&&!x.feature?`<div class=\"effect\">${esc(effectText(x))}</div>`:''}<div>${sourcePills(x)}</div></button></div>`}\n"
new="function pickerCard(x){const fk=favoriteKey(pick.type,x.id),fav=favorites.has(fk),facts=pickerFacts(x);return `<div class=\"pick-card ${rarityClass(x)}\"><button class=\"fav ${fav?'active':''}\" data-fav-type=\"${pick.type}\" data-fav-id=\"${esc(x.id)}\" title=\"Favorite\">★</button><button class=\"pick\" data-select=\"${esc(x.id)}\"><strong>${esc(x.name)}</strong>${rarityBadge(x)}<span>${esc([x.type,x.slot,x.setName,x.style,x.category].filter(Boolean).join(' · '))}</span>${coverageBadge(x)}${facts?`<div class=\"picker-facts\">${esc(facts)}</div>`:''}${x.feature?`<div class=\"effect feature\">${esc(x.feature)}</div>`:''}${effectText(x)&&!x.feature?`<div class=\"effect\">${esc(effectText(x))}</div>`:''}<div>${sourcePills(x)}</div></button></div>`}\n"
if old not in app: raise RuntimeError('pickerCard missing')
app=app.replace(old,new)
start=app.index('function renderModGroups(arr){')
end=app.index('\nfunction clearPick()', start)
mod_fn="""function renderModGroups(arr){\n  const groups={};arr.forEach(x=>(groups[x.name]||(groups[x.name]=[])).push(x));const entries=Object.entries(groups).sort((a,b)=>a[0].localeCompare(b[0]));if(!entries.length)return '<div class=\"empty\">No compatible community mods found.</div>';\n  return entries.map(([name,xs])=>`<div class=\"mod-group ${rarityClass(xs[0])}\"><div class=\"mod-group-head\"><div><b>${esc(name)}</b>${rarityBadge(xs[0])}</div><span>${xs.length} variant${xs.length===1?'':'s'}</span></div><div class=\"effect\">${esc(effectText(xs[0]))}</div><div class=\"variant-grid\">${xs.map(x=>{const fav=favorites.has(favoriteKey(pick.type,x.id));return `<div class=\"variant-choice ${rarityClass(x)}\"><button class=\"fav ${fav?'active':''}\" data-fav-type=\"${pick.type}\" data-fav-id=\"${esc(x.id)}\">★</button><button data-select=\"${esc(x.id)}\"><b>${esc(x.variant||'General')}</b>${rarityBadge(x)}</button></div>`}).join('')}</div><div>${sourcePills(xs[0])}</div></div>`).join('')}\n"""
app=app[:start]+mod_fn+app[end:]
index=index.replace('1.2.4','1.2.5')
data=data.replace('"version":"1.2.4-community"','"version":"1.2.5-community"',1)
css_marker='/* v1.2.5 rarity visual language */'
if css_marker not in css:
    css += r'''

/* v1.2.5 rarity visual language */
:root{--rarity-normal:#e3e6eb;--rarity-common:#63d27f;--rarity-rare:#4ea7ff;--rarity-epic:#b66cff;--rarity-legendary:#f0b84b;--rarity-mythic:#f05262}
.rarity-normal{--rarity-color:var(--rarity-normal);--rarity-glow:rgba(227,230,235,.10)}
.rarity-common{--rarity-color:var(--rarity-common);--rarity-glow:rgba(99,210,127,.12)}
.rarity-rare{--rarity-color:var(--rarity-rare);--rarity-glow:rgba(78,167,255,.13)}
.rarity-epic{--rarity-color:var(--rarity-epic);--rarity-glow:rgba(182,108,255,.14)}
.rarity-legendary{--rarity-color:var(--rarity-legendary);--rarity-glow:rgba(240,184,75,.14)}
.rarity-mythic{--rarity-color:var(--rarity-mythic);--rarity-glow:rgba(240,82,98,.15)}
.weapon-card.has-rarity,.gear-card.has-rarity,.system-card.has-rarity,.pick-card.has-rarity .pick,.mod-group.has-rarity,.calibration-box.has-rarity,.report-card.has-rarity,.armor-report-row.has-rarity{border-color:color-mix(in srgb,var(--rarity-color) 48%,#2b3038);box-shadow:inset 3px 0 0 var(--rarity-color),0 0 0 1px rgba(255,255,255,.01)}
.weapon-card.has-rarity,.gear-card.has-rarity,.system-card.has-rarity,.report-card.has-rarity,.armor-report-row.has-rarity,.mod-group.has-rarity,.calibration-box.has-rarity{background-image:linear-gradient(105deg,var(--rarity-glow),transparent 34%)}
.has-rarity>.slot-head .item-name,.system-card.has-rarity>.item-name,.pick-card.has-rarity .pick>strong,.report-card.has-rarity .report-head>b,.armor-report-row.has-rarity>div>b,.mod-group.has-rarity .mod-group-head b,.calibration-box.has-rarity .cal-head b{color:var(--rarity-color)}
.rarity-badge{display:inline-flex;align-items:center;gap:5px;width:max-content;margin:5px 5px 2px 0;padding:2px 6px;border:1px solid color-mix(in srgb,var(--rarity-color) 55%,transparent);border-radius:999px;background:var(--rarity-glow);color:var(--rarity-color);font-size:8px!important;font-weight:900!important;line-height:1.35;letter-spacing:.07em;text-transform:uppercase;vertical-align:middle}
.rarity-badge i{display:block;width:6px;height:6px;border-radius:50%;background:var(--rarity-color);box-shadow:0 0 8px var(--rarity-color)}
.rarity-badge.rarity-normal{--rarity-color:var(--rarity-normal);--rarity-glow:rgba(227,230,235,.10)}.rarity-badge.rarity-common{--rarity-color:var(--rarity-common);--rarity-glow:rgba(99,210,127,.12)}.rarity-badge.rarity-rare{--rarity-color:var(--rarity-rare);--rarity-glow:rgba(78,167,255,.13)}.rarity-badge.rarity-epic{--rarity-color:var(--rarity-epic);--rarity-glow:rgba(182,108,255,.14)}.rarity-badge.rarity-legendary{--rarity-color:var(--rarity-legendary);--rarity-glow:rgba(240,184,75,.14)}.rarity-badge.rarity-mythic{--rarity-color:var(--rarity-mythic);--rarity-glow:rgba(240,82,98,.15)}
.mini-select.has-rarity button{border-color:color-mix(in srgb,var(--rarity-color) 40%,#333842);box-shadow:inset 2px 0 0 var(--rarity-color)}
.mini-select.has-rarity .choice>span{min-width:0;display:flex;flex-wrap:wrap;align-items:center;gap:3px}.mini-select.has-rarity .choice .rarity-badge{margin:2px 0 0}
.mod-instance.has-rarity{border-color:color-mix(in srgb,var(--rarity-color) 42%,#2d323a);box-shadow:inset 2px 0 0 var(--rarity-color)}
.mod-instance.has-rarity .mod-instance-head b,.variant-choice.has-rarity>button:last-child>b,.armor-mod-line.has-rarity>b{color:var(--rarity-color)}
.variant-choice.has-rarity>button:last-child{border-color:color-mix(in srgb,var(--rarity-color) 38%,#333842);box-shadow:inset 2px 0 0 var(--rarity-color)}
.report-row.has-rarity{box-shadow:inset 2px 0 0 var(--rarity-color)}.report-row.has-rarity>div>b,.system-detail.has-rarity>b{color:var(--rarity-color)}
.system-detail.has-rarity{border-left:2px solid var(--rarity-color);padding-left:7px}
.set-progress-head .rarity-badge{margin-left:6px}
@supports not (color:color-mix(in srgb,red 50%,black)){.weapon-card.has-rarity,.gear-card.has-rarity,.system-card.has-rarity,.pick-card.has-rarity .pick,.mod-group.has-rarity,.calibration-box.has-rarity,.report-card.has-rarity,.armor-report-row.has-rarity,.mini-select.has-rarity button,.mod-instance.has-rarity,.variant-choice.has-rarity>button:last-child{border-color:var(--rarity-color)}}
'''
app_path.write_text(app,encoding='utf-8'); css_path.write_text(css,encoding='utf-8'); index_path.write_text(index,encoding='utf-8'); data_path.write_text(data,encoding='utf-8')
print('Dead Signal v1.2.5 rarity visual system applied')
