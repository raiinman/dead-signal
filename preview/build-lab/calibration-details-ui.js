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
function fmt(v){
  const n=Number(v);
  return Number.isFinite(n)?(Number.isInteger(n)?String(n):n.toFixed(1)):'—';
}
function rarityFromText(text){
  for(const q of ['Legendary','Epic','Rare'])if(new RegExp(`\\b${q}\\b`,'i').test(text))return q;
  return '';
}
function isCurrentCalibrationCard(card){
  const text=norm(card.textContent||'');
  return /Calibration Blueprint/i.test(text)&&/Current Calibration/i.test(text);
}
function enhancePickerCard(card){
  if(!isCurrentCalibrationCard(card)){
    card.querySelector('.ds-calibration-facts')?.remove();
    return;
  }
  const q=rarityFromText(norm(card.textContent||''));
  const main=RULES.main[q];
  const sec=RULES.secondary[q];
  if(!main||!sec)return;

  const signature=q;
  let box=card.querySelector('.ds-calibration-facts');
  if(box?.dataset.signature===signature)return;
  if(!box){
    box=document.createElement('div');
    box.className='ds-calibration-facts';
    const copy=card.querySelector('.pick-copy');
    if(copy)copy.append(box); else card.append(box);
  }
  box.innerHTML=`
    <div class="ds-cal-main"><small>MAIN CALIBRATION ROLL</small><strong>Weapon DMG ${fmt(main[0])}–${fmt(main[1])}%</strong></div>
    <div class="ds-cal-secondary"><small>ONE RANDOM SECONDARY</small><span>${sec.map(s=>`${s.name} ${fmt(s.min)}–${fmt(s.max)}%`).join(' · ')}</span></div>
    <div class="ds-cal-style-status">Fixed Style effect is linked in mined data; exact in-game wording is the remaining description bridge.</div>`;
  box.dataset.signature=signature;
}

function selectedCalibrationInfo(card){
  const proxy=card.querySelector('.ds-wm-cal-picker');
  const native=card.querySelector('.ds-native-calibration-relocated');
  const calBox=card.querySelector('.ds-wm-cal');
  const sources=[proxy,native,calBox].filter(Boolean);
  let rarity='';
  for(const source of sources){
    rarity=rarityFromText(norm(source.textContent||''));
    if(rarity)break;
  }
  if(!rarity||!RULES.secondary[rarity])return null;

  let name=norm(proxy?.querySelector('.ds-wm-cal-picker-button strong')?.textContent||'');
  if(!name||/^Select Calibration Blueprint$/i.test(name)){
    name=norm(native?.textContent||'').match(/Calibration Blueprint\s*-\s*[^\n]+/i)?.[0]||`Calibration ${rarity}`;
  }
  return {rarity,name,secondary:RULES.secondary[rarity]};
}
function slotKey(card,info){
  const cards=[...document.querySelectorAll('.weapon-card')];
  return `${Math.max(0,cards.indexOf(card))}:${norm(info.name).toLowerCase()}:${info.rarity}`;
}
function savedFor(k){return state[k]||{};}
function patchSaved(k,patch){state[k]={...(state[k]||{}),...patch};saveState();}
function optionFor(info,id){return info.secondary.find(x=>String(x.id)===String(id))||null;}

function renderSecondary(card){
  const panel=card.querySelector('.ds-weapon-model');
  if(!panel)return;
  const old=panel.querySelector('.ds-cal-secondary-editor');
  const info=selectedCalibrationInfo(card);
  if(!info){old?.remove();return;}
  const calBox=panel.querySelector('.ds-wm-cal');
  if(!calBox){old?.remove();return;}

  const k=slotKey(card,info);
  const saved=savedFor(k);
  const buildMode=mode();
  const chosen=optionFor(info,saved.secondaryId);
  const signature=[info.rarity,info.name,buildMode,chosen?.id||'none',saved.secondaryRoll??''].join('|');
  let box=old;
  if(box?.dataset.signature===signature)return;
  if(!box){box=document.createElement('div');box.className='ds-cal-secondary-editor';calBox.after(box);}

  const choices=info.secondary.map(s=>`<option value="${s.id}" ${chosen&&chosen.id===s.id?'selected':''}>${s.name} // ${fmt(s.min)}–${fmt(s.max)}%</option>`).join('');
  let control='';
  if(chosen){
    let roll=Number(saved.secondaryRoll);
    const hasRoll=Number.isFinite(roll)&&roll>=chosen.min&&roll<=chosen.max;
    if(buildMode==='god'){
      roll=chosen.max;
      control=`<div class="ds-cal-secondary-roll ds-cal-secondary-god"><input type="range" min="${chosen.min}" max="${chosen.max}" step="0.1" value="${roll}" disabled><output>${fmt(roll)}%</output><p>God Roll uses the maximum legal ${chosen.name} roll.</p></div>`;
    }else{
      control=`<div class="ds-cal-secondary-roll"><div class="ds-cal-secondary-inputs"><input data-cal-secondary-range type="range" min="${chosen.min}" max="${chosen.max}" step="0.1" value="${hasRoll?roll:chosen.min}"><label><input data-cal-secondary-number type="number" min="${chosen.min}" max="${chosen.max}" step="0.1" value="${hasRoll?fmt(roll):''}" placeholder="Exact roll"><b>%</b></label></div><div class="ds-cal-secondary-range"><span>${fmt(chosen.min)}%</span><span>${hasRoll?`Your roll: ${fmt(roll)}%`:'Enter the roll on your blueprint'}</span><span>${fmt(chosen.max)}%</span></div></div>`;
    }
  }else{
    control='<p class="ds-cal-secondary-help">Choose the secondary attribute shown on your actual dropped Calibration Blueprint. Only one secondary is active.</p>';
  }

  box.innerHTML=`
    <div class="ds-cal-secondary-head"><div><small>SECONDARY CALIBRATION RNG</small><strong>${chosen?chosen.name:'Choose your rolled attribute'}</strong></div><span>1 ATTRIBUTE</span></div>
    <label class="ds-cal-secondary-select"><span>Secondary Attribute</span><select data-cal-secondary-choice><option value="">Choose…</option>${choices}</select></label>
    ${control}`;
  box.dataset.signature=signature;

  box.querySelector('[data-cal-secondary-choice]')?.addEventListener('change',e=>{
    patchSaved(k,{secondaryId:e.target.value||null,secondaryRoll:null});
    box.dataset.signature='';
    renderSecondary(card);
  });
  const range=box.querySelector('[data-cal-secondary-range]');
  const number=box.querySelector('[data-cal-secondary-number]');
  if(range&&number&&chosen){
    range.addEventListener('input',()=>{
      const v=Math.round(Number(range.value)*10)/10;
      patchSaved(k,{secondaryId:chosen.id,secondaryRoll:v});
      number.value=fmt(v);
      box.dataset.signature='';
      renderSecondary(card);
    });
    number.addEventListener('input',()=>{
      if(number.value==='')return;
      let v=Number(number.value); if(!Number.isFinite(v))return;
      v=Math.round(Math.min(chosen.max,Math.max(chosen.min,v))*10)/10;
      patchSaved(k,{secondaryId:chosen.id,secondaryRoll:v});
      range.value=String(v);
      box.dataset.signature='';
      renderSecondary(card);
    });
    number.addEventListener('change',()=>{
      if(number.value===''){
        patchSaved(k,{secondaryId:chosen.id,secondaryRoll:null});
        box.dataset.signature='';
        renderSecondary(card);
      }
    });
  }
}

function run(){
  document.querySelectorAll('.pick-card').forEach(enhancePickerCard);
  document.querySelectorAll('.weapon-card').forEach(renderSecondary);
}
function queue(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;run();});}
new MutationObserver(queue).observe(document.body,{childList:true,subtree:true,characterData:true});
window.addEventListener('dead-signal:build-mode-change',()=>setTimeout(run,0));
document.addEventListener('change',e=>{if(e.target.closest?.('.weapon-card,#picker'))setTimeout(run,0);});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run,{once:true});else run();
setTimeout(run,180);setTimeout(run,650);
})();
