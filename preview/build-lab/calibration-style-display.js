(()=>{
'use strict';
// PLAYER v1.5.1 — exact player-facing Calibration Style descriptions mined from
// Once Human buff_level_data + current English localization by Dead Signal Miner v1.5.7.4.
const ROWS=[["12-Gauge","R","Fire Rate +15%, Draw Speed +35%, Attack -7.5%"],["12-Gauge","E","Fire Rate +20%, Draw Speed +50%, Attack -10%"],["12-Gauge","L","Fire Rate +25%, Draw Speed +50%, Attack -10%"],["16-Gauge","R","Reload Speed +24%, Magazine Capacity -17%"],["16-Gauge","E","Reload Speed +32%, Magazine Capacity -25%"],["16-Gauge","L","Reload Speed +40%, Magazine Capacity -25%"],["20-Gauge","R","Magazine Capacity +36%, Reload Speed -7%"],["20-Gauge","E","Magazine Capacity +48%, Reload Speed -10%"],["20-Gauge","L","Magazine Capacity +60%, Reload Speed -10%"],["Assault Machine Gun","R","Attack +15%, Magazine Capacity -20%, Accuracy -35"],["Assault Machine Gun","E","Attack +20%, Magazine Size -30%, Accuracy -50"],["Assault Machine Gun","L","Attack +25%, Magazine Size -30%, Accuracy -50"],["Assault SMG","R","Attack +15%, Magazine Capacity -20%, Accuracy -35%"],["Assault SMG","E","Attack +17.5%, Magazine Capacity -25%, Accuracy -50%"],["Assault SMG","L","Attack +20%, Magazine Capacity -25%, Accuracy -50%"],["Boost Pistol","E","After reloading, the next shot's keyword gains Trigger Chance +32%. Fire Rate -12%."],["Boost Pistol","L","After reloading, the next shot's keyword gains Trigger Chance +40%. Fire Rate -12%."],["Boost Shotgun","E","After reloading, the next shot's keyword gains Trigger Chance +32%. Fire Rate -12%."],["Boost Shotgun","L","After reloading, the next shot's keyword gains Trigger Chance +40%. Fire Rate -12%."],["Capacity Expander","R","Magazine Capacity +60%, Mobility -35%"],["Capacity Expander","E","Magazine Capacity +80%, Mobility (Movement Speed while aiming) -50%"],["Capacity Expander","L","Magazine Capacity +100%, Mobility -50%"],["Energy Rifle","E","After taking damage, automatically reload 1 bullet (cooldown: 0.3s). Attack +8%."],["Energy Rifle","L","After taking damage, automatically reload 1 bullet (cooldown: 0.3s). Attack +10%."],["Energy SMG","E","After taking damage, automatically reload 1 bullet (cooldown: 0.3s). Attack +8%."],["Energy SMG","L","After taking damage, automatically reload 1 bullet (cooldown: 0.3s). Attack +10%."],["Frugal Pistol","E","After missing a shot, automatically reload 1 ammo. The next shot that hits gains Attack +12%."],["Frugal Pistol","L","After missing a shot, automatically reload 1 ammo. The next shot that hits gains Attack +15%."],["Frugal Sniper Rifle","E","After missing a shot, automatically reload 1 ammo. The next shot that hits gains Attack +12%."],["Frugal Sniper Rifle","L","After missing a shot, automatically reload 1 ammo. The next shot that hits gains Attack +15%."],["Heavy Assault Rifle","R","Magazine Capacity +45%, Reload Speed -7%"],["Heavy Assault Rifle","E","Magazine Capacity +60%, Reload Speed -10%"],["Heavy Assault Rifle","L","Magazine Capacity +75%, Reload Speed -10%"],["Heavy Melee","R","Heavy Attack DMG +20%, Melee Stamina Cost -15%"],["Heavy Melee","E","Heavy Attack DMG +30%, Melee Stamina Cost -25%"],["Heavy Melee","L","Heavy Attack DMG +40%, Melee Stamina Cost -25%"],["Heavy SMG","R","Magazine Capacity +36%, Reload Speed -7%"],["Heavy SMG","E","Magazine Capacity +48%, Reload Speed -10%"],["Heavy SMG","L","Magazine Capacity +60%, Reload Speed -10%"],["Light SMG","R","Reload Speed +24%, Magazine Capacity -17%"],["Light SMG","E","Reload Speed +32%, Magazine Capacity -25%"],["Light SMG","L","Reload Speed +40%, Magazine Capacity -25%"],["Overflow Machine Gun","E","When reloading, load extra ammo equal to 50% of the shots fired within 20 seconds from the last magazine. The extra ammo gains Attack +8%. (Extra ammo cannot exceed 100% of magazine capacity.)"],["Overflow Machine Gun","L","When reloading, load extra ammo equal to 50% of the shots fired within 20 seconds from the last magazine. The extra ammo gains Attack +10%. (Extra ammo cannot exceed 100% of magazine capacity.)"],["Overflow Pistol","E","When reloading, load extra ammo equal to 50% of the shots fired within 10 seconds from the last magazine. The extra ammo gains Attack +8%. (Extra ammo cannot exceed 100% of magazine capacity.)"],["Overflow Pistol","L","When reloading, load extra ammo equal to 50% of the shots fired within 10 seconds from the last magazine. The extra ammo gains Attack +10%. (Extra ammo cannot exceed 100% of magazine capacity.)"],["P 22","R","Fire Rate +15%, Magazine Capacity +24%, Attack -10%"],["P 22","E","Fire Rate +20%, Magazine Capacity +32%, Attack -15%"],["P 22","L","Fire Rate +25%, Magazine Capacity +40%, Attack -15%"],["Portable Crossbow","R","Mobility (Movement Speed while aiming) +30%, Bow Draw Speed +30%, Weapon Switching Speed +35%, Movement Speed while holding the weapon +7.5%"],["Portable Crossbow","E","Mobility (Movement Speed while aiming) +40%, Bow Draw Speed +40%, Weapon Switching Speed +50%, Movement Speed while holding the weapon +10%"],["Portable Crossbow","L","Mobility (Movement Speed while aiming) +50%, Bow Draw Speed +50%, Weapon Switching Speed +50%, Movement Speed while holding the weapon +12.5%"],["Portable Pistol","R","Mobility +35%, Movement Speed while Holding Gun +7.5%, Weapon Switching Speed +35%"],["Portable Pistol","E","Mobility +50%, Movement Speed while Holding Gun +10%, Weapon Switching Speed +50%"],["Portable Pistol","L","Mobility (Movement Speed while aiming) +50%, Movement Speed while Holding Gun +12.5%, Weapon Switching Speed +50%"],["Portable Sniper","R","Mobility (Movement Speed while aiming) +30%, Movement Speed while Holding Gun +7.5%, Speed while Holding Gun +37.5%"],["Portable Sniper","E","Mobility (Movement Speed while aiming) +40%, Movement Speed while Holding Gun +10%, Speed while Holding Gun +50%"],["Portable Sniper","L","Mobility (Movement Speed while aiming) +50%, Movement Speed while Holding Gun +12.5%, Speed while Holding Gun +50%"],["Precision Assault Rifle","R","Attack +15%, Range +30%, Fire Rate -7.5%"],["Precision Assault Rifle","E","Attack +20%, Range +40%, Fire Rate -10%"],["Precision Assault Rifle","L","Attack +25%, Range +40%, Fire Rate -10%"],["Precision Crossbow","R","Attack +7.5%, Range +15%, Reload Efficiency -12%"],["Precision Crossbow","E","Attack +10%, Range +20%, Reload Efficiency -15%"],["Precision Crossbow","L","Attack +12.5%, Range +20%, Reload Efficiency -15%"],["Precision Pistol","R","Attack +15%, Range +30%, Fire Rate -7.5%"],["Precision Pistol","E","Attack +20%, Range +40%, Fire Rate -10%"],["Precision Pistol","L","Attack +25%, Range +40%, Fire Rate -10%"],["Rapid Assault Rifle","R","Fire Rate +10%, Reload Speed +7.5%, Attack -7.5%"],["Rapid Assault Rifle","E","Fire Rate +15%, Reload Speed +10%, Attack -10%"],["Rapid Assault Rifle","L","Fire Rate +20%, Reload Speed +10%, Attack -10%"],["Rapid Machine Gun","R","Fire Rate +5%, Accuracy -35%, Fire Rate +5% after continuous fire for 2s"],["Rapid Machine Gun","E","Fire Rate +7.5%, Accuracy -50%, Fire Rate +7.5% after continuous fire for 2s"],["Rapid Machine Gun","L","Fire Rate +10%, Accuracy -50%, Fire Rate +10% after continuous fire for 2s"],["Rapid Sniper","R","Bolt-pulling Speed +30%, Post-Fire Delay -30%, Reload Efficiency +10%, Attack -7.5%."],["Rapid Sniper","E","Bolt-pulling Speed +40%, Post-Fire Delay -40%, Reload Efficiency +15%, Attack -10%."],["Rapid Sniper","L","Bolt-pulling Speed +50%, Post-Fire Delay -50%, Reload Efficiency +15%, Attack -10%."],["Speed Melee","R","Movement Speed +7.5%, Light strikes continuously increase Melee Attack Speed, up to +30%."],["Speed Melee","E","Movement Speed +10%, Light strikes continuously increase Melee Attack Speed, up to +30%."],["Speed Melee","L","Movement Speed +12.5%, Light strikes continuously increase Melee Attack Speed, up to +30%."],["Steady Machine Gun","R","Stability +20%, Stability +20% when crouching"],["Steady Machine Gun","E","Stability +30%, Stability +40% when crouching"],["Steady Machine Gun","L","Stability +40%, Stability +60% when crouching"],["Steady Sniper","R","Stability +25%, significant aim shake reduction"],["Steady Sniper","E","Stability +50%, significant aim shake reduction"],["Steady Sniper","L","Stability +75%, significant aim shake reduction"],["Structural Destruction","R","Building DMG +30%, Attack -15%"],["Structural Destruction","E","Building DMG +40%, Attack -20%"],["Structural Destruction","L","Building DMG +50%, Attack -20%"],["Vanguard Machine Gun","E","After reloading from empty, the next shot is guaranteed to trigger its keyword effect. DMG -5%."],["Vanguard Machine Gun","L","After reloading from empty, the next shot is guaranteed to trigger its keyword effect."],["Vanguard Rifle","E","After reloading from empty, the next shot is guaranteed to trigger its keyword effect. DMG -5%."],["Vanguard Rifle","L","After reloading from empty, the next shot is guaranteed to trigger its keyword effect."],["Vanguard SMG","E","After reloading from empty, the next shot is guaranteed to trigger its keyword effect. DMG -5%."],["Vanguard SMG","L","After reloading from empty, the next shot is guaranteed to trigger its keyword effect."]];
const rarityCode={Rare:'R',Epic:'E',Legendary:'L'};
const norm=v=>String(v??'').replace(/\s+/g,' ').trim();
const esc=v=>String(v??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const key=(name,rarity)=>`${norm(name).replace(/^Calibration Blueprint\s*-\s*/i,'').toLowerCase()}|${rarityCode[rarity]||rarity}`;
const DATA=new Map(ROWS.map(r=>[`${r[0].toLowerCase()}|${r[1]}`,r[2]]));
let queued=false;

function rarityFrom(el){
  if(!el)return '';
  const values=[el.dataset?.rarity,el.dataset?.quality,el.dataset?.grade,el.textContent];
  for(const node of el.querySelectorAll?.('[data-rarity],[data-quality],[data-grade],.rarity-badge,.quality-badge,[class*="rarity"],[class*="quality"]')||[]){
    values.push(node.dataset?.rarity,node.dataset?.quality,node.dataset?.grade,node.textContent);
  }
  for(const value of values){
    const text=norm(value);
    for(const q of ['Legendary','Epic','Rare'])if(new RegExp(`\\b${q}\\b`,'i').test(text))return q;
  }
  return '';
}
function blueprintFromCard(card){
  const hinted=norm(card.dataset?.dsCalibrationBlueprint||'');
  if(hinted)return hinted;
  const strong=card.querySelector('.pick-title-row strong');
  const text=norm(strong?.textContent||card.textContent||'');
  const m=text.match(/Calibration Blueprint\s*-\s*(.+?)(?=\s+(?:Legendary|Epic|Rare)\b|$)/i);
  return norm(m?.[1]||text.replace(/^Calibration Blueprint\s*-\s*/i,''));
}
function descriptionFor(name,rarity){return DATA.get(key(name,rarity))||'';}

function enhancePickerCard(card){
  if(!/Calibration Blueprint/i.test(norm(card.textContent||'')))return;
  const descText=descriptionFor(blueprintFromCard(card),rarityFrom(card));
  let desc=card.querySelector(':scope > .ds-cal-mined-description');
  if(!descText){desc?.remove();return;}
  if(!desc){desc=document.createElement('p');desc.className='ds-cal-mined-description';card.append(desc);}
  if(norm(desc.textContent)!==norm(descText))desc.textContent=descText;
}
function enhanceWeapon(card){
  const panel=card.querySelector('.ds-weapon-model');
  const proxy=panel?.querySelector('.ds-wm-cal-picker');
  let effect=panel?.querySelector('.ds-cal-style-effect');
  if(!panel||!proxy){effect?.remove();return;}
  const name=norm(proxy.dataset?.calibrationName||proxy.querySelector('.ds-wm-cal-picker-button strong')?.textContent||'');
  const rarity=norm(proxy.dataset?.calibrationRarity||'')||rarityFrom(proxy);
  const descText=name&&!/^Select Calibration Blueprint$/i.test(name)?descriptionFor(name,rarity):'';
  if(!descText){effect?.remove();return;}
  if(!effect){effect=document.createElement('section');effect.className='ds-cal-style-effect';}
  if(effect.dataset.description!==descText){
    effect.innerHTML=`<small>FIXED CALIBRATION STYLE EFFECT</small><p>${esc(descText)}</p>`;
    effect.dataset.description=descText;
  }
  if(proxy.nextElementSibling!==effect)proxy.after(effect);
}
function run(){
  document.querySelectorAll('#picker .pick-card').forEach(enhancePickerCard);
  document.querySelectorAll('.weapon-card').forEach(enhanceWeapon);
}
function queue(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;run();});}

new MutationObserver(queue).observe(document.body,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['data-calibration-name','data-calibration-rarity','data-rarity','data-quality','data-grade','class']});
document.addEventListener('change',e=>{if(e.target.closest?.('.weapon-card,#picker'))setTimeout(run,0);});
document.addEventListener('click',e=>{if(e.target.closest?.('.weapon-card,#picker'))setTimeout(run,0);});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run,{once:true});else run();
setTimeout(run,180);setTimeout(run,650);
})();
