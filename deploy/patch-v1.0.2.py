#!/usr/bin/env python3
from pathlib import Path
import re, sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
app=root/'app.js'; data=root/'data/community-data.js'; index=root/'index.html'
s=app.read_text()
s=s.replace("const SCHEMA=10, PLANNER_VERSION='1.0.0', MAX_CRADLES=8;", "const SCHEMA=12, PLANNER_VERSION='1.0.2', MAX_CRADLES=8;")
s=s.replace('const sourcePills=x=>(x?.sources||[]).map(s=>`<a class="source-pill" href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.site)}</a>`).join(\'\');','const sourcePills=x=>(x?.sources||[]).map(s=>`<span class="source-pill" title="Community data provenance">Source: ${esc(s.site)}</span>`).join(\'\');')
s=s.replace("const defaultWeaponConfig=()=>({tier:5,stars:6,ammo:null,weaponMod:null,calibration:null,calibrationProfile:null,calibrationRolls:[],attachments:{muzzle:null,optic:null,tactical:null,magazine:null}});", "const defaultWeaponConfig=()=>({tier:5,stars:1,ammo:null,weaponMod:null,calibration:null,calibrationAttack:null,calibrationBonusStat:'elementalDamage',calibrationBonusValue:null,attachments:{muzzle:null,optic:null,tactical:null,magazine:null}});")
s=s.replace("const defaultArmorConfig=()=>({tier:5,stars:6});", "const defaultArmorConfig=()=>({tier:5,stars:1});")
legacy='''      if(c.calibration&&raw.mechanics){
        const cal=byId(D.calibrations,c.calibration),prefix=`calProfile_${slot}_${c.calibration}`;c.calibrationProfile=raw.mechanics[prefix]||cal?.rollProfiles?.[0]?.id||null;
        const prof=cal?.rollProfiles?.find(x=>x.id===c.calibrationProfile);c.calibrationRolls=(prof?.rolls||[]).map((r,i)=>{
          const k=`calRoll_${slot}_${c.calibration}_${c.calibrationProfile}_${i}`;return Number.isFinite(Number(raw.mechanics[k]))?Number(raw.mechanics[k]):mid(r.min,r.max);
        });
      }
'''
s=s.replace(legacy,'')
s=s.replace('  n.schema=SCHEMA;n.plannerVersion=PLANNER_VERSION;return n;','''  for(const [slot] of weaponSlots){
    const c=n.weaponConfig[slot],w=byId(D.weapons,n.weapons[slot]);clampProgression(c,w);
    if(c.calibration){
      const cal=byId(D.calibrations,c.calibration),attack=cal?.attackRoll,bonus=calBonus(cal,c);
      if(attack&&!Number.isFinite(Number(c.calibrationAttack)))c.calibrationAttack=mid(attack.min,attack.max);
      if(!bonus){const first=(cal?.bonusAttributes||[]).find(x=>x.id==='elementalDamage')||(cal?.bonusAttributes||[])[0];c.calibrationBonusStat=first?.id||null;c.calibrationBonusValue=first?mid(first.min,first.max):null;}
      else if(!Number.isFinite(Number(c.calibrationBonusValue)))c.calibrationBonusValue=mid(bonus.min,bonus.max);
    }
    delete c.calibrationProfile;delete c.calibrationRolls;
  }
  for(const slot of armorSlots){const c=n.armorConfig[slot]||(n.armorConfig[slot]=defaultArmorConfig()),a=byId(D.armor,n.armor[slot]);clampProgression(c,a);}
  n.schema=SCHEMA;n.plannerVersion=PLANNER_VERSION;return n;''')
needle="function pct(v){return `${Number(v)>=0?'+':''}${Number(v)}%`}\n"
s=s.replace(needle,needle+'''function maxStarsForRarity(rarity){
  const r=String(rarity||'').toLowerCase();
  if(r==='legendary'||r==='gold')return 6;
  if(r==='epic'||r==='purple')return 5;
  if(r==='rare'||r==='blue'||r==='fine')return 4;
  if(r==='uncommon'||r==='green'||r==='common')return 3;
  return 6;
}
function clampProgression(cfg,item){
  cfg.tier=Math.min(5,Math.max(1,Number(cfg.tier)||5));
  cfg.stars=Math.min(maxStarsForRarity(item?.rarity),Math.max(1,Number(cfg.stars)||1));
  return cfg;
}
function calBonus(cal,c){return (cal?.bonusAttributes||[]).find(x=>x.id===c.calibrationBonusStat)||(cal?.bonusAttributes||[])[0]||null}
function initCurrentCalibration(slot,id){
  const c=state.weaponConfig[slot],cal=byId(D.calibrations,id),attack=cal?.attackRoll,bonus=(cal?.bonusAttributes||[]).find(x=>x.id==='elementalDamage')||(cal?.bonusAttributes||[])[0];
  c.calibrationAttack=attack?mid(attack.min,attack.max):null;
  c.calibrationBonusStat=bonus?.id||null;
  c.calibrationBonusValue=bonus?mid(bonus.min,bonus.max):null;
  delete c.calibrationProfile;delete c.calibrationRolls;
}
''')
a=s.index('function progressionRow('); b=s.index('\nfunction renderWeapons()',a)
s=s[:a]+'''function progressionRow(scope,slot,cfg,rarity){
  const tier=[1,2,3,4,5].map(n=>`<option value="${n}" ${Number(cfg.tier)===n?'selected':''}>Tier ${['','I','II','III','IV','V'][n]}</option>`).join('');
  const max=maxStarsForRarity(rarity);if(Number(cfg.stars)>max)cfg.stars=max;
  const stars=Array.from({length:max},(_,i)=>i+1).map(n=>`<option value="${n}" ${Number(cfg.stars)===n?'selected':''}>${n}★</option>`).join('');
  return `<div class="progression"><label><span>Gear Tier</span><select data-${scope}-tier="${esc(slot)}">${tier}</select></label><label><span>Blueprint Stars</span><select data-${scope}-stars="${esc(slot)}">${stars}</select><small>${esc(rarity||'Unknown')} max ${max}★</small></label></div>`;
}
'''+s[b:]
s=s.replace("${progressionRow('weapon',slot,c)}", "${progressionRow('weapon',slot,c,w?.rarity)}").replace("${progressionRow('armor',slot,cfg)}", "${progressionRow('armor',slot,cfg,a?.rarity)}")
a=s.index('function renderCalibrationInstance('); b=s.index('\nfunction renderArmor()',a)
s=s[:a]+'''function renderCalibrationInstance(slot,cal,c){
  const attack=cal.attackRoll,bonus=calBonus(cal,c);
  if(!attack||!bonus)return `<div class="calibration-box"><b>${esc(cal.name)}</b><small>Current calibration ranges are not loaded for this community record yet.</small></div>`;
  let attackValue=Number(c.calibrationAttack);if(!Number.isFinite(attackValue)){attackValue=mid(attack.min,attack.max);c.calibrationAttack=attackValue}
  let bonusValue=Number(c.calibrationBonusValue);if(!Number.isFinite(bonusValue)){bonusValue=mid(bonus.min,bonus.max);c.calibrationBonusValue=bonusValue}
  return `<div class="calibration-box">
    <div class="cal-head"><div><span>CURRENT CALIBRATION BLUEPRINT</span><b>${esc(cal.name)}</b><small>${esc(cal.style||'')} · ${esc(cal.rarity||'')}</small></div><div>${sourcePills(cal)}</div></div>
    <div class="summary-notice">Current 2.3.1+ system: the blueprint is chosen while crafting the weapon. It keeps its style, always has one RNG Attack roll, and one RNG bonus attribute.</div>
    <div class="roll-grid">
      <div class="roll-card"><div><b>Attack</b><small>RNG ${attack.min}% – ${attack.max}% · ${esc(attack.provenance||'')}</small></div><div class="roll-line"><input type="number" min="${attack.min}" max="${attack.max}" step="${attack.step||0.1}" value="${attackValue}" data-cal-attack="${slot}"><span>%</span></div><div class="roll-buttons"><button data-cal-preset="${slot}" data-cal-target="attack" data-roll-value="${attack.min}">MIN</button><button data-cal-preset="${slot}" data-cal-target="attack" data-roll-value="${mid(attack.min,attack.max)}">MID</button><button data-cal-preset="${slot}" data-cal-target="attack" data-roll-value="${attack.max}">MAX</button></div></div>
      <div class="roll-card"><label class="profile-select"><span>RNG bonus attribute</span><select data-cal-bonus="${slot}">${(cal.bonusAttributes||[]).map(x=>`<option value="${esc(x.id)}" ${x.id===bonus.id?'selected':''}>${esc(x.label)}</option>`).join('')}</select></label><div><small>RNG ${bonus.min}% – ${bonus.max}% · ${esc(bonus.provenance||'')}</small></div><div class="roll-line"><input type="number" min="${bonus.min}" max="${bonus.max}" step="${bonus.step||0.1}" value="${bonusValue}" data-cal-bonus-value="${slot}"><span>%</span></div><div class="roll-buttons"><button data-cal-preset="${slot}" data-cal-target="bonus" data-roll-value="${bonus.min}">MIN</button><button data-cal-preset="${slot}" data-cal-target="bonus" data-roll-value="${mid(bonus.min,bonus.max)}">MID</button><button data-cal-preset="${slot}" data-cal-target="bonus" data-roll-value="${bonus.max}">MAX</button></div></div>
    </div>
  </div>`;
}
'''+s[b:]
a=s.index('function weaponReport('); b=s.index('\nfunction armorReport()',a)
s=s[:a]+'''function weaponReport(slot,label){
  const w=byId(D.weapons,state.weapons[slot]);if(!w)return '';
  const c=state.weaponConfig[slot],cal=byId(D.calibrations,c.calibration),bonus=calBonus(cal,c);
  const parts=[];
  if(c.ammo)parts.push(['Ammo',byId(D.ammo,c.ammo)]);if(c.weaponMod)parts.push(['Mod',byId(D.mods,c.weaponMod)]);if(cal)parts.push(['Calibration',cal]);
  for(const a of attachmentSlots)if(c.attachments[a])parts.push([cap(a),byId(D.attachments,c.attachments[a])]);
  const calRolls=cal&&bonus?`<div class="report-row"><span>Calibration RNG</span><div><b>Attack ${pct(c.calibrationAttack)}</b><small>${esc(bonus.label)} ${pct(c.calibrationBonusValue)}</small><small>${esc(cal.style||'')}</small></div></div>`:'';
  return `<div class="report-card"><div class="report-head"><span>${esc(label.toUpperCase())}</span><b>${esc(w.name)}</b><small>Gear Tier ${['','I','II','III','IV','V'][c.tier]||c.tier} · Blueprint ${c.stars}★ · ${esc(w.type)}</small></div>${parts.map(([k,x])=>`<div class="report-row"><span>${esc(k)}</span><div><b>${esc(x?.name||'—')}</b>${x?.variant?` <small>&lt;${esc(x.variant)}&gt;</small>`:''}${effectText(x)?`<small>${esc(effectText(x))}</small>`:''}</div></div>`).join('')}${calRolls}</div>`;
}
'''+s[b:]
s=s.replace("${esc(a.setName||'Standalone')} · Tier ${['','I','II','III','IV','V'][cfg?.tier]||cfg?.tier} · ${cfg?.stars}★", "${esc(a.setName||'Standalone')} · Gear Tier ${['','I','II','III','IV','V'][cfg?.tier]||cfg?.tier} · Blueprint ${cfg?.stars}★")
s=s.replace("  if(type==='weapon'){state.weapons[slot]=id;state.weaponConfig[slot]=defaultWeaponConfig()}\n  else if(type==='armor'){state.armor[slot]=id;state.armorMods[slot]=null}", "  if(type==='weapon'){state.weapons[slot]=id;state.weaponConfig[slot]=defaultWeaponConfig();clampProgression(state.weaponConfig[slot],byId(D.weapons,id))}\n  else if(type==='armor'){state.armor[slot]=id;state.armorMods[slot]=null;state.armorConfig[slot]=defaultArmorConfig();clampProgression(state.armorConfig[slot],byId(D.armor,id))}")
s=s.replace("function initCalibration(slot,id){const c=state.weaponConfig[slot],cal=byId(D.calibrations,id),p=cal?.rollProfiles?.[0];c.calibrationProfile=p?.id||null;c.calibrationRolls=(p?.rolls||[]).map(r=>mid(r.min,r.max))}", "function initCalibration(slot,id){initCurrentCalibration(slot,id)}")
s=s.replace("if(subslot==='calibration'){state.weaponConfig[slot].calibrationProfile=null;state.weaponConfig[slot].calibrationRolls=[]}", "if(subslot==='calibration'){state.weaponConfig[slot].calibrationAttack=null;state.weaponConfig[slot].calibrationBonusStat='elementalDamage';state.weaponConfig[slot].calibrationBonusValue=null}")
s=s.replace("  const roll=e.target.closest('[data-roll-preset]');if(roll){const slot=roll.dataset.rollPreset,i=Number(roll.dataset.rollIndex);state.weaponConfig[slot].calibrationRolls[i]=Number(roll.dataset.rollValue);render();return}\n", "  const roll=e.target.closest('[data-cal-preset]');if(roll){const slot=roll.dataset.calPreset,target=roll.dataset.calTarget,v=Number(roll.dataset.rollValue),c=state.weaponConfig[slot];if(target==='attack')c.calibrationAttack=v;else c.calibrationBonusValue=v;render();return}\n")
needle="const ammo=byId(D.ammo,c.ammo);if(ammo)push(`${label} ammo: ${ammo.name}`,effectText(ammo));"
s=s.replace(needle,needle+"const cal=byId(D.calibrations,c.calibration),bonus=calBonus(cal,c);if(cal&&bonus){push(`${label} calibration: ${cal.name}`,`Attack ${pct(c.calibrationAttack)} · ${bonus.label} ${pct(c.calibrationBonusValue)} · ${cal.style}`)};")
a=s.index("$('weapons').addEventListener('change',e=>{"); b=s.index("$('armor').addEventListener('change'",a)
s=s[:a]+'''$('weapons').addEventListener('change',e=>{
  if(e.target.dataset.weaponTier)state.weaponConfig[e.target.dataset.weaponTier].tier=Math.min(5,Math.max(1,Number(e.target.value)));
  if(e.target.dataset.weaponStars){const slot=e.target.dataset.weaponStars,c=state.weaponConfig[slot],w=byId(D.weapons,state.weapons[slot]);c.stars=Math.min(maxStarsForRarity(w?.rarity),Math.max(1,Number(e.target.value)));}
  if(e.target.dataset.calBonus){const slot=e.target.dataset.calBonus,c=state.weaponConfig[slot],cal=byId(D.calibrations,c.calibration),bonus=(cal?.bonusAttributes||[]).find(x=>x.id===e.target.value);c.calibrationBonusStat=bonus?.id||null;c.calibrationBonusValue=bonus?mid(bonus.min,bonus.max):null;}
  if(e.target.dataset.calAttack){const slot=e.target.dataset.calAttack,c=state.weaponConfig[slot],cal=byId(D.calibrations,c.calibration),r=cal?.attackRoll;let v=Number(e.target.value);if(r)v=Math.max(Number(r.min),Math.min(Number(r.max),v));c.calibrationAttack=v;}
  if(e.target.dataset.calBonusValue){const slot=e.target.dataset.calBonusValue,c=state.weaponConfig[slot],cal=byId(D.calibrations,c.calibration),r=calBonus(cal,c);let v=Number(e.target.value);if(r)v=Math.max(Number(r.min),Math.min(Number(r.max),v));c.calibrationBonusValue=v;}
  render();
});
'''+s[b:]
s=s.replace("$('armor').addEventListener('change',e=>{if(e.target.dataset.armorTier)state.armorConfig[e.target.dataset.armorTier].tier=Number(e.target.value);if(e.target.dataset.armorStars)state.armorConfig[e.target.dataset.armorStars].stars=Number(e.target.value);renderSummary()});", "$('armor').addEventListener('change',e=>{if(e.target.dataset.armorTier)state.armorConfig[e.target.dataset.armorTier].tier=Math.min(5,Math.max(1,Number(e.target.value)));if(e.target.dataset.armorStars){const slot=e.target.dataset.armorStars,a=byId(D.armor,state.armor[slot]);state.armorConfig[slot].stars=Math.min(maxStarsForRarity(a?.rarity),Math.max(1,Number(e.target.value)))}render();});")
app.write_text(s)

d=data.read_text(); a=d.index('  calibrations: ['); b=d.index('  attachments: [',a)
cal='''  calibrations: [
    {id:"precision-assault-rifle",name:"Precision Assault Rifle",style:"Precision Style",rarity:"Legendary",compatible:["Assault Rifle"],system:"2.3.1-current",attackRoll:{stat:"attack",label:"Attack",min:33,max:50,step:0.1,provenance:"Once Human Official"},bonusAttributes:[{id:"critRate",stat:"critRate",label:"Crit Rate",min:12,max:16,step:0.1,provenance:"Community-derived from legacy roll bands under the official 2.3.1 merge rule"},{id:"critDamage",stat:"critDamage",label:"Crit DMG",min:30,max:40,step:0.1,provenance:"Community-derived from legacy roll bands under the official 2.3.1 merge rule"},{id:"elementalDamage",stat:"elementalDamage",label:"Elemental DMG",min:15,max:20,step:0.1,provenance:"Once Human Official 2.3.1 example"},{id:"weakspotDamage",stat:"weakspotDamage",label:"Weakspot DMG",min:18,max:24,step:0.1,provenance:"Community-derived from legacy roll bands under the official 2.3.1 merge rule"}],attributes:["Current system: style attribute + RNG Attack + one RNG bonus attribute."],sources:[{site:"Once Human Official"},{site:"Wikily"}]},
    {id:"rapid-assault-rifle",name:"Rapid Assault Rifle",style:"Rapid Shot Style",rarity:"Legendary",compatible:["Assault Rifle"],system:"2.3.1-current",attackRoll:{stat:"attack",label:"Attack",min:33,max:50,step:0.1,provenance:"Once Human Official"},bonusAttributes:[{id:"critRate",stat:"critRate",label:"Crit Rate",min:12,max:16,step:0.1,provenance:"Community-derived from legacy roll bands under the official 2.3.1 merge rule"},{id:"critDamage",stat:"critDamage",label:"Crit DMG",min:30,max:40,step:0.1,provenance:"Community-derived from legacy roll bands under the official 2.3.1 merge rule"},{id:"elementalDamage",stat:"elementalDamage",label:"Elemental DMG",min:15,max:20,step:0.1,provenance:"Once Human Official 2.3.1 example"},{id:"weakspotDamage",stat:"weakspotDamage",label:"Weakspot DMG",min:18,max:24,step:0.1,provenance:"Community-derived from legacy roll bands under the official 2.3.1 merge rule"}],attributes:["Current system: style attribute + RNG Attack + one RNG bonus attribute."],sources:[{site:"Once Human Official"},{site:"Wikily"}]}
  ],
'''
d=d[:a]+cal+d[b:]
d=re.sub(r',url:"[^"]*"','',d).replace('version: "1.0.0-community"','version: "1.0.2-community"').replace('note: "Community-only planner corpus. Used to develop and validate the Ultimate Planner workflow before any mined-game database is introduced."','note: "Community-only planner corpus. Used to develop and validate the Ultimate Planner workflow before any mined-game database is introduced. Provenance is shown by source name only; Dead Signal does not link back to external source sites."')
data.write_text(d)
i=index.read_text().replace('COMMUNITY v1.0','COMMUNITY v1.0.2'); index.write_text(i)
