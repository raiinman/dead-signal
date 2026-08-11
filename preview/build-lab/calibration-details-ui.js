(()=>{
'use strict';

const RULES=window.DS_CALIBRATION_RULES||{};
if(!RULES.main||!RULES.secondary)return;

const STATE_KEY='dead-signal-calibration-secondary-v1';
let state=readState();
let queued=false;

function norm(v){return String(v??'').replace(/\s+/g,' ').trim();}
function readState(){try{return JSON.parse(localStorage.getItem(STATE_KEY)||'{}')||{};}catch(_){return {};}}
function saveState(){try{localStorage.setItem(STATE_KEY,JSON.stringify(state));}catch(_){} }
function mode(){
  if(window.DSBuildMode&&typeof window.DSBuildMode.get==='function')return window.DSBuildMode.get();
  try{return localStorage.getItem('dead-signal-build-mode')==='god'?'god':'gear';}catch(_){return 'gear';}
}
function fmt(v){const n=Number(v);return Number.isFinite(n)?n.toFixed(1):'—';}
function rarityFromText(text){for(const q of ['Legendary','Epic','Rare'])if(new RegExp(`\\b${q}\\b`,'i').test(text))return q;return '';}
function canonicalRarity(value){const q=rarityFromText(norm(value));return RULES.main[q]&&RULES.secondary[q]?q:'';}
function isCalibrationCard(card){return /Calibration Blueprint/i.test(norm(card.textContent||''));}
function pickerCardRarity(card){
  const direct=[card.dataset?.rarity,card.dataset?.quality,card.dataset?.grade];
  for(const value of direct){const q=canonicalRarity(value);if(q)return q;}
  for(const el of card.querySelectorAll('[data-rarity],[data-quality],[data-grade],.rarity-badge,.quality-badge,[class*="rarity"],[class*="quality"]')){
    for(const value of [el.dataset?.rarity,el.dataset?.quality,el.dataset?.grade,el.textContent]){
      const q=canonicalRarity(value);if(q)return q;
    }
  }
  return canonicalRarity(card.textContent||'');
}
function hideLegacyCurrentLabel(card){
  for(const el of card.querySelectorAll('small,span,p,div')){
    if(norm(el.textContent)==='Current Calibration')el.classList.add('ds-calibration-legacy-current');
  }
}
function markCompatibilityCopy(card){
  const copy=card.querySelector('.pick-copy')||card;
  for(const el of copy.querySelectorAll('p,.pick-meta,.picker-effect,.effect,.subtle')){
    const text=norm(el.textContent||'');
    if((/Compatible with|Applicable to/i.test(text))&&!/Calibration Blueprint/i.test(text))el.classList.add('ds-calibration-compatibility');
  }
}
function enhancePickerCard(card){
  if(!isCalibrationCard(card)){
    card.classList.remove('ds-calibration-card');
    card.querySelector('.ds-calibration-facts')?.remove();
    return;
  }
  card.classList.add('ds-calibration-card');
  hideLegacyCurrentLabel(card);
  markCompatibilityCopy(card);

  const q=pickerCardRarity(card),main=RULES.main[q],sec=RULES.secondary[q];
  if(!main||!sec)return;

  const signature=q;
  let box=card.querySelector('.ds-calibration-facts');
  if(box?.dataset.signature===signature)return;
  if(!box){
    box=document.createElement('div');
    box.className='ds-calibration-facts';
    const copy=card.querySelector('.pick-copy')||card.querySelector('.pick-layout')?.lastElementChild||card;
    const title=copy.querySelector?.('.pick-title-row');
    if(title&&title.parentElement===copy)title.after(box);else copy.prepend(box);
  }
  box.innerHTML=`
    <div class="ds-cal-main">
      <small>CALIBRATION STAT</small>
      <strong>Weapon DMG <b>+${fmt(main[0])}–${fmt(main[1])}%</b></strong>
    </div>
    <div class="ds-cal-secondary">
      <small>ONE RANDOM SECONDARY</small>
      <div class="ds-cal-secondary-pool">${sec.map(s=>`<span><b>${s.name}</b><em>${fmt(s.min)}–${fmt(s.max)}%</em></span>`).join('')}</div>
    </div>`;
  box.dataset.signature=signature;
}

function selectedCalibrationInfo(card){
  const proxy=card.querySelector('.ds-wm-cal-picker'),native=card.querySelector('.ds-native-calibration-relocated'),calBox=card.querySelector('.ds-wm-cal');
  let rarity=norm(proxy?.dataset?.calibrationRarity||'');
  if(!RULES.secondary[rarity]){
    rarity='';
    for(const source of [native,calBox].filter(Boolean)){rarity=rarityFromText(norm(source.textContent||''));if(rarity)break;}
  }
  if(!rarity||!RULES.secondary[rarity])return null;
  let name=norm(proxy?.dataset?.calibrationName||proxy?.querySelector('.ds-wm-cal-picker-button strong')?.textContent||'');
  if(!name||/^Select Calibration Blueprint$/i.test(name))name=norm(native?.textContent||'').match(/Calibration Blueprint\s*-\s*[^\n]+/i)?.[0]||`Calibration ${rarity}`;
  return{rarity,name,secondary:RULES.secondary[rarity]};
}
function slotKey(card,info){const cards=[...document.querySelectorAll('.weapon-card')];return`${Math.max(0,cards.indexOf(card))}:${norm(info.name).toLowerCase()}:${info.rarity}`;}
function savedFor(k){return state[k]||{};}
function patchSaved(k,patch){state[k]={...(state[k]||{}),...patch};saveState();}
function optionFor(info,id){return info.secondary.find(x=>String(x.id)===String(id))||null;}
function signatureFor(info,buildMode,chosen,roll){return[info.rarity,info.name,buildMode,chosen?.id||'none',roll==null?'':Number(roll).toFixed(1)].join('|');}

function renderSecondary(card){
  const panel=card.querySelector('.ds-weapon-model');if(!panel)return;
  const old=panel.querySelector('.ds-cal-secondary-editor'),info=selectedCalibrationInfo(card);
  if(!info){old?.remove();return;}
  const calBox=panel.querySelector('.ds-wm-cal');if(!calBox){old?.remove();return;}

  const k=slotKey(card,info),saved=savedFor(k),buildMode=mode(),chosen=optionFor(info,saved.secondaryId);
  let roll=chosen?Number(saved.secondaryRoll):null;
  const hasRoll=chosen&&Number.isFinite(roll)&&roll>=chosen.min&&roll<=chosen.max;
  if(buildMode==='god'&&chosen)roll=chosen.max;
  const signature=signatureFor(info,buildMode,chosen,hasRoll||buildMode==='god'?roll:null);
  let box=old;
  if(box?.dataset.signature===signature)return;
  if(!box){box=document.createElement('section');box.className='ds-cal-secondary-editor ds-cal-roll-card';calBox.after(box);}

  const choices=info.secondary.map(s=>`<option value="${s.id}" ${chosen&&chosen.id===s.id?'selected':''}>${s.name} // ${fmt(s.min)}–${fmt(s.max)}%</option>`).join('');
  let control='';
  if(chosen){
    if(buildMode==='god'){
      control=`<div class="ds-cal-locked-value"><small>GOD ROLL VALUE</small><strong>${fmt(roll)}%</strong><p>Maximum legal ${chosen.name} roll.</p></div>`;
    }else{
      control=`<label class="ds-cal-number-field"><span>Exact ${chosen.name} roll</span><div><input data-cal-secondary-number type="number" min="${chosen.min}" max="${chosen.max}" step="0.1" value="${hasRoll?fmt(roll):''}" placeholder=""><b>%</b></div><small data-cal-secondary-status>${hasRoll?`Saved roll: ${fmt(roll)}%`:`Enter a value from ${fmt(chosen.min)}% to ${fmt(chosen.max)}%`}</small></label>`;
    }
  }else{
    control='<p class="ds-cal-secondary-help">Choose the secondary attribute shown on your actual Calibration Blueprint.</p>';
  }

  box.innerHTML=`
    <div class="ds-cal-roll-head"><span class="ds-cal-step">2</span><div><small>SECONDARY ROLL</small><strong>${chosen?chosen.name:'Choose the rolled attribute'}</strong></div><em>1 OF 4</em></div>
    <label class="ds-cal-secondary-select"><span>Attribute</span><select data-cal-secondary-choice><option value="">Choose…</option>${choices}</select></label>
    ${control}`;
  box.dataset.signature=signature;

  box.querySelector('[data-cal-secondary-choice]')?.addEventListener('change',e=>{patchSaved(k,{secondaryId:e.target.value||null,secondaryRoll:null});box.dataset.signature='';renderSecondary(card);});
  const number=box.querySelector('[data-cal-secondary-number]'),status=box.querySelector('[data-cal-secondary-status]');
  if(number&&chosen){
    const saveValid=v=>{
      v=Math.round(Number(v)*10)/10;
      if(!Number.isFinite(v)||v<chosen.min||v>chosen.max)return false;
      patchSaved(k,{secondaryId:chosen.id,secondaryRoll:v});
      number.value=fmt(v);
      if(status)status.textContent=`Saved roll: ${fmt(v)}%`;
      box.dataset.signature=signatureFor(info,buildMode,chosen,v);
      return true;
    };
    number.addEventListener('input',()=>{
      if(number.value===''){if(status)status.textContent=`Enter a value from ${fmt(chosen.min)}% to ${fmt(chosen.max)}%`;return;}
      const v=Number(number.value);
      if(Number.isFinite(v)&&v>=chosen.min&&v<=chosen.max){saveValid(v);}
      else if(status)status.textContent=`Allowed range: ${fmt(chosen.min)}%–${fmt(chosen.max)}%`;
    });
    number.addEventListener('change',()=>{
      if(number.value===''){patchSaved(k,{secondaryId:chosen.id,secondaryRoll:null});box.dataset.signature='';renderSecondary(card);return;}
      let v=Number(number.value);if(!Number.isFinite(v))return;
      v=Math.round(Math.min(chosen.max,Math.max(chosen.min,v))*10)/10;saveValid(v);
    });
  }
}

function run(){document.querySelectorAll('.pick-card').forEach(enhancePickerCard);document.querySelectorAll('.weapon-card').forEach(renderSecondary);}
function queue(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;run();});}
new MutationObserver(queue).observe(document.body,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['data-calibration-rarity','data-calibration-name','data-rarity','data-quality','data-grade']});
window.addEventListener('dead-signal:build-mode-change',()=>setTimeout(run,0));
document.addEventListener('change',e=>{if(e.target.closest?.('.weapon-card,#picker'))setTimeout(run,0);});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run,{once:true});else run();
setTimeout(run,180);setTimeout(run,650);
})();
