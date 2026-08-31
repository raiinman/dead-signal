(()=>{
'use strict';

const STORAGE='dead-signal-community-planner-builds';
const SLOT_LABELS=['Primary','Secondary','Melee'];
let queued=false;

const norm=v=>String(v??'').replace(/\s+/g,' ').trim();
const mode=()=>{
  if(window.DSBuildMode&&typeof window.DSBuildMode.get==='function')return window.DSBuildMode.get()==='god'?'god':'gear';
  try{return localStorage.getItem('dead-signal-build-mode')==='god'?'god':'gear';}catch(_){return 'gear';}
};
function savedBuilds(){try{return JSON.parse(localStorage.getItem(STORAGE)||'[]')||[];}catch(_){return [];}}
function savedMode(raw){const m=raw?.state?.dsExtension?.buildMode;return m==='god'?'god':'gear';}

function decorateSavedBuilds(){
  const byId=new Map(savedBuilds().map(x=>[String(x?.id||''),x]));
  document.querySelectorAll('#savedList .saved-entry').forEach(entry=>{
    const action=entry.querySelector('[data-load-id],[data-clone-id],[data-delete-id]');
    if(!action)return;
    const id=action.dataset.loadId||action.dataset.cloneId||action.dataset.deleteId||'';
    const record=byId.get(String(id));
    if(!record)return;
    const buildMode=savedMode(record);
    entry.dataset.dsSavedBuildMode=buildMode;
    let badge=entry.querySelector('.ds-saved-mode-badge');
    if(!badge){
      badge=document.createElement('span');
      badge.className='ds-saved-mode-badge';
      const name=entry.querySelector(':scope > div:first-child > b');
      if(name)name.insertAdjacentElement('afterend',badge);
      else entry.firstElementChild?.prepend(badge);
    }
    badge.dataset.mode=buildMode;
    badge.textContent=buildMode==='god'?'GOD ROLL':'MY GEAR';
    badge.title=buildMode==='god'?'Theoretical maximum build':'Actual owned-gear build';
  });
}

function selectedCalibration(card){
  const proxy=card.querySelector('.ds-wm-cal-picker');
  const name=norm(proxy?.dataset?.calibrationName||proxy?.querySelector('.ds-wm-cal-picker-button strong')?.textContent||'');
  return !!name&&!/^Select Calibration Blueprint$/i.test(name);
}
function cardWarnings(card,index){
  if(!card.classList.contains('filled'))return [];
  if(index===2)return [];
  if(!selectedCalibration(card))return [];
  if(mode()==='god')return [];

  const label=SLOT_LABELS[index]||`Weapon ${index+1}`;
  const out=[];
  const attack=card.querySelector('[data-wm-roll-number]');
  if(!attack)out.push(`${label}: Calibration Weapon DMG input is unavailable; re-select the Calibration Blueprint.`);
  else if(attack.value==='')out.push(`${label}: enter the exact Calibration Weapon DMG roll.`);

  const secondary=card.querySelector('[data-cal-secondary-choice]');
  if(!secondary){
    out.push(`${label}: Calibration secondary input is unavailable; re-select the Calibration Blueprint.`);
    return out;
  }
  if(secondary.value===''){
    out.push(`${label}: choose the Calibration secondary attribute.`);
    return out;
  }

  const secondaryValue=card.querySelector('[data-cal-secondary-number]');
  if(!secondaryValue)out.push(`${label}: secondary roll input is unavailable; re-select the Calibration Blueprint.`);
  else if(secondaryValue.value==='')out.push(`${label}: enter the exact secondary roll.`);
  return out;
}
function ensureIntegrityCard(){
  const completion=document.getElementById('completion');
  if(!completion)return null;
  let card=document.getElementById('dsBuildIntegrity');
  if(!card){
    card=document.createElement('section');
    card.id='dsBuildIntegrity';
    card.className='ds-build-integrity';
    completion.insertAdjacentElement('afterend',card);
  }
  return card;
}
function renderIntegrity(){
  const host=ensureIntegrityCard();if(!host)return;
  const buildMode=mode();
  const warnings=[...document.querySelectorAll('.weapon-card')].flatMap((card,index)=>cardWarnings(card,index));
  const signature=`${buildMode}|${warnings.join('|')}`;
  if(host.dataset.signature===signature)return;
  host.dataset.signature=signature;
  host.dataset.mode=buildMode;

  if(buildMode==='god'){
    host.innerHTML='<div class="ds-integrity-head"><small>BUILD DATA INTEGRITY</small><strong>THEORYCRAFT MODE</strong><span class="ds-integrity-state theory">GOD ROLL</span></div><p>Legal maximum Calibration RNG values are assumed. Save, export and share payloads retain the theoretical-build flag.</p>';
    return;
  }
  if(warnings.length){
    host.innerHTML=`<div class="ds-integrity-head"><small>BUILD DATA INTEGRITY</small><strong>NEEDS PLAYER INPUT</strong><span class="ds-integrity-state warn">${warnings.length} OPEN</span></div><p>Dead Signal will preserve blanks instead of inventing account-specific RNG values. Missing controls are treated as incomplete rather than silently marked ready.</p><ul>${warnings.map(x=>`<li>${x}</li>`).join('')}</ul>`;
    return;
  }
  host.innerHTML='<div class="ds-integrity-head"><small>BUILD DATA INTEGRITY</small><strong>READY TO SAVE / SHARE</strong><span class="ds-integrity-state ok">READY</span></div><p>Selected Calibration inputs are present and internally consistent for the current build mode.</p>';
}

function run(){decorateSavedBuilds();renderIntegrity();}
function queue(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;run();});}

new MutationObserver(queue).observe(document.body,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['class','data-calibration-name','data-calibration-rarity']});
document.addEventListener('input',e=>{if(e.target.closest?.('.weapon-card'))queue();});
document.addEventListener('change',e=>{if(e.target.closest?.('.weapon-card')||e.target.matches?.('[data-ds-mode-choice]'))queue();});
document.addEventListener('click',e=>{if(e.target.closest?.('#loadBtn,#saveBtn,#cloneBtn,#resetBtn,[data-load-id],[data-clone-id],[data-delete-id],[data-template]'))setTimeout(run,0);});
window.addEventListener('dead-signal:build-mode-change',()=>setTimeout(run,0));
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run,{once:true});else run();
setTimeout(run,250);setTimeout(run,800);
})();