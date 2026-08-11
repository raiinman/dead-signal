(()=>{
'use strict';

/*
  PLAYER v1.5.2 — persistence bridge
  The core planner (app.js) already owns the canonical build state and native
  calibration inputs. Newer weapon/calibration UI layers are presentation
  overlays with their own local sidecars. This bridge writes those visible
  controls back through the core's native DOM events before persistence, and
  carries Build Mode as a namespaced extension in save/export/share payloads.
*/

const STORAGE='dead-signal-community-planner-builds';
const SLOT_ORDER=['primary','secondary','melee'];
const EXT_KEY='dsExtension';
let syncing=false;
let queued=false;

const norm=v=>String(v??'').replace(/\s+/g,' ').trim();
const currentMode=()=>{
  if(window.DSBuildMode&&typeof window.DSBuildMode.get==='function')return window.DSBuildMode.get()==='god'?'god':'gear';
  try{return localStorage.getItem('dead-signal-build-mode')==='god'?'god':'gear';}catch(_){return 'gear';}
};
const slotForCard=card=>SLOT_ORDER[[...document.querySelectorAll('.weapon-card')].indexOf(card)]||null;
const cardForSlot=slot=>{
  const i=SLOT_ORDER.indexOf(slot);
  return i>=0?[...document.querySelectorAll('.weapon-card')][i]||null:null;
};
function ruleMatcher(ruleId){
  return ({
    weakspot:/weakspot/i,
    crit_rate:/crit\s*rate/i,
    elemental:/elemental/i,
    crit_dmg:/crit(?:ical)?\s*(?:dmg|damage)/i
  })[ruleId]||null;
}
function ruleIdFromLabel(label){
  const t=norm(label);
  if(/weakspot/i.test(t))return 'weakspot';
  if(/crit\s*rate/i.test(t))return 'crit_rate';
  if(/elemental/i.test(t))return 'elemental';
  if(/crit(?:ical)?\s*(?:dmg|damage)/i.test(t))return 'crit_dmg';
  return '';
}
function finiteValue(v){
  if(v===null||v===undefined||v==='')return null;
  const n=Number(v);return Number.isFinite(n)?n:null;
}
function captureVisibleCalibration(slot){
  const card=cardForSlot(slot);
  if(!card)return null;
  const attackControl=card.querySelector('[data-wm-roll-number]');
  const secondaryControl=card.querySelector('[data-cal-secondary-number]');
  return {
    hasAttackControl:!!attackControl,
    attack:finiteValue(attackControl?.value),
    secondaryId:card.querySelector('[data-cal-secondary-choice]')?.value||'',
    hasSecondaryValueControl:!!secondaryControl,
    secondaryValue:finiteValue(secondaryControl?.value)
  };
}
function dispatchChange(el){
  el.dispatchEvent(new Event('change',{bubbles:true}));
}
function syncSlotToCore(slot,captured){
  if(!captured)return;

  let card=cardForSlot(slot);
  if(!card)return;

  /* Secondary identity first because the core rerenders after every native change. */
  if(captured.secondaryId){
    let nativeSelect=card.querySelector(`[data-cal-bonus="${slot}"]`);
    const matcher=ruleMatcher(captured.secondaryId);
    if(nativeSelect&&matcher){
      const option=[...nativeSelect.options].find(o=>matcher.test(norm(o.textContent)));
      if(option&&nativeSelect.value!==option.value){
        nativeSelect.value=option.value;
        dispatchChange(nativeSelect);
      }
    }
  }

  card=cardForSlot(slot);
  if(!card)return;

  if(currentMode()==='gear'&&captured.hasAttackControl){
    const nativeAttack=card.querySelector(`[data-cal-attack="${slot}"]`);
    if(nativeAttack&&finiteValue(nativeAttack.value)!==captured.attack){
      nativeAttack.value=captured.attack===null?'':String(captured.attack);
      dispatchChange(nativeAttack);
    }
  }

  card=cardForSlot(slot);
  if(!card)return;

  if(currentMode()==='gear'&&captured.hasSecondaryValueControl){
    const nativeBonus=card.querySelector(`[data-cal-bonus-value="${slot}"]`);
    if(nativeBonus&&finiteValue(nativeBonus.value)!==captured.secondaryValue){
      nativeBonus.value=captured.secondaryValue===null?'':String(captured.secondaryValue);
      dispatchChange(nativeBonus);
    }
  }
}
function syncCalibrationUiToCore(){
  if(syncing)return;
  const snapshots=Object.fromEntries(SLOT_ORDER.map(slot=>[slot,captureVisibleCalibration(slot)]));
  syncing=true;
  try{
    for(const slot of SLOT_ORDER)syncSlotToCore(slot,snapshots[slot]);
  }finally{syncing=false;}
}
function syncSlotFromCore(slot){
  let card=cardForSlot(slot);
  if(!card)return;

  const nativeAttack=card.querySelector(`[data-cal-attack="${slot}"]`);
  const main=card.querySelector('[data-wm-roll-number]');
  if(nativeAttack&&main&&currentMode()==='gear'){
    const v=finiteValue(nativeAttack.value);
    if(v!==null&&finiteValue(main.value)!==v){
      main.value=String(v);
      dispatchChange(main);
    }
  }

  card=cardForSlot(slot);if(!card)return;
  const nativeSelect=card.querySelector(`[data-cal-bonus="${slot}"]`);
  const sideSelect=card.querySelector('[data-cal-secondary-choice]');
  if(nativeSelect&&sideSelect){
    const label=nativeSelect.selectedOptions?.[0]?.textContent||'';
    const ruleId=ruleIdFromLabel(label);
    if(ruleId&&sideSelect.value!==ruleId){
      sideSelect.value=ruleId;
      dispatchChange(sideSelect);
    }
  }

  card=cardForSlot(slot);if(!card)return;
  const nativeBonus=card.querySelector(`[data-cal-bonus-value="${slot}"]`);
  const sideNumber=card.querySelector('[data-cal-secondary-number]');
  if(nativeBonus&&sideNumber&&currentMode()==='gear'){
    const v=finiteValue(nativeBonus.value);
    if(v!==null&&finiteValue(sideNumber.value)!==v){
      sideNumber.value=String(v);
      dispatchChange(sideNumber);
    }
  }
}
function syncCoreToCalibrationUi(){
  if(syncing)return;
  syncing=true;
  try{
    for(const slot of SLOT_ORDER)syncSlotFromCore(slot);
  }finally{syncing=false;}
}

function augmentState(raw){
  if(!raw||typeof raw!=='object')return raw;
  raw[EXT_KEY]={...(raw[EXT_KEY]||{}),version:1,buildMode:currentMode()};
  return raw;
}
function modeFromState(raw){
  const m=raw?.[EXT_KEY]?.buildMode;
  return m==='god'?'god':m==='gear'?'gear':null;
}
function applyMode(mode){
  if(mode!=='gear'&&mode!=='god')return;
  if(window.DSBuildMode&&typeof window.DSBuildMode.set==='function'){
    window.DSBuildMode.set(mode,{confirmGod:false,persist:true});
  }else{
    try{localStorage.setItem('dead-signal-build-mode',mode);}catch(_){}
  }
}
function readSaved(){
  try{return JSON.parse(localStorage.getItem(STORAGE)||'[]')||[];}catch(_){return [];}
}
function writeSaved(list){
  try{localStorage.setItem(STORAGE,JSON.stringify(list));}catch(_){}
}
function augmentNewestSaved(){
  const list=readSaved();
  if(!list.length)return;
  let latest=0;
  for(let i=1;i<list.length;i++){
    if(String(list[i]?.updated||'')>String(list[latest]?.updated||''))latest=i;
  }
  if(list[latest]?.state)augmentState(list[latest].state);
  writeSaved(list);
}
function stateForSavedId(id){
  return readSaved().find(x=>String(x?.id)===String(id))?.state||null;
}

function decodeSharedState(url){
  try{
    const m=String(url||'').match(/#b=([^&]+)$/);
    if(!m)return null;
    let b=m[1].replace(/-/g,'+').replace(/_/g,'/');
    while(b.length%4)b+='=';
    const bin=atob(b);
    const bytes=Uint8Array.from(bin,c=>c.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes));
  }catch(_){return null;}
}
function encodeSharedState(raw){
  const bytes=new TextEncoder().encode(JSON.stringify(raw));
  let bin='';bytes.forEach(b=>bin+=String.fromCharCode(b));
  return btoa(bin).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}
function transformShareUrl(url){
  const raw=decodeSharedState(url);
  if(!raw)return url;
  augmentState(raw);
  return `${String(url).split('#')[0]}#b=${encodeSharedState(raw)}`;
}
function transformExportPart(part){
  if(typeof part!=='string')return part;
  try{
    const obj=JSON.parse(part);
    if(obj?.format!=='dead-signal-build'||!obj?.state)return part;
    augmentState(obj.state);
    return JSON.stringify(obj,null,2);
  }catch(_){return part;}
}

function wrapPersistenceButtons(){
  const save=document.getElementById('saveBtn');
  if(save&&save.onclick&&!save.dataset.dsPersistenceWrapped){
    const original=save.onclick;
    save.onclick=function(e){
      syncCalibrationUiToCore();
      const result=original.call(this,e);
      augmentNewestSaved();
      return result;
    };
    save.dataset.dsPersistenceWrapped='1';
  }

  const exportBtn=document.getElementById('exportBtn');
  if(exportBtn&&exportBtn.onclick&&!exportBtn.dataset.dsPersistenceWrapped){
    const original=exportBtn.onclick;
    exportBtn.onclick=function(e){
      syncCalibrationUiToCore();
      const NativeBlob=window.Blob;
      function DSBlob(parts,opts){
        const next=Array.isArray(parts)?parts.map(transformExportPart):parts;
        return new NativeBlob(next,opts);
      }
      DSBlob.prototype=NativeBlob.prototype;
      Object.setPrototypeOf(DSBlob,NativeBlob);
      window.Blob=DSBlob;
      try{return original.call(this,e);}
      finally{window.Blob=NativeBlob;}
    };
    exportBtn.dataset.dsPersistenceWrapped='1';
  }

  const share=document.getElementById('shareBtn');
  if(share&&share.onclick&&!share.dataset.dsPersistenceWrapped){
    const original=share.onclick;
    share.onclick=function(e){
      syncCalibrationUiToCore();

      const clipboard=navigator.clipboard;
      const originalWrite=clipboard?.writeText?.bind(clipboard);
      const originalPrompt=window.prompt;

      if(clipboard&&originalWrite){
        try{clipboard.writeText=url=>originalWrite(transformShareUrl(url));}catch(_){}
      }
      window.prompt=(message,value)=>originalPrompt.call(window,message,transformShareUrl(value));

      let result;
      try{result=original.call(this,e);}
      catch(err){
        if(clipboard&&originalWrite){try{clipboard.writeText=originalWrite;}catch(_){}}
        window.prompt=originalPrompt;
        throw err;
      }

      return Promise.resolve(result).finally(()=>{
        if(clipboard&&originalWrite){try{clipboard.writeText=originalWrite;}catch(_){}}
        window.prompt=originalPrompt;
      });
    };
    share.dataset.dsPersistenceWrapped='1';
  }
}

function applyLoadedStateExtensions(raw){
  const mode=modeFromState(raw);
  if(mode)applyMode(mode);
  setTimeout(syncCoreToCalibrationUi,30);
  setTimeout(syncCoreToCalibrationUi,180);
}

document.addEventListener('click',e=>{
  const load=e.target.closest?.('[data-load-id]');
  const clone=e.target.closest?.('[data-clone-id]');
  if(load||clone){
    const raw=stateForSavedId((load||clone).dataset[load?'loadId':'cloneId']);
    if(raw)setTimeout(()=>applyLoadedStateExtensions(raw),0);
  }
},true);

document.addEventListener('change',e=>{
  if(syncing)return;
  if(e.target.matches?.('[data-wm-roll-number],[data-cal-secondary-choice],[data-cal-secondary-number]')){
    const card=e.target.closest('.weapon-card');
    const slot=slotForCard(card);
    if(slot)setTimeout(()=>syncSlotToCore(slot,captureVisibleCalibration(slot)),0);
  }

  if(e.target.id==='importFile'){
    const file=e.target.files?.[0];
    if(file&&typeof file.text==='function'){
      file.text().then(text=>{
        try{
          const obj=JSON.parse(text),raw=obj?.state||obj;
          setTimeout(()=>applyLoadedStateExtensions(raw),80);
        }catch(_){}
      });
    }
  }
},true);

window.addEventListener('dead-signal:build-mode-change',()=>{
  /* Build Mode is captured into the native payload at each persistence boundary. */
});

function initFromHash(){
  const raw=decodeSharedState(location.href);
  if(raw)applyLoadedStateExtensions(raw);
}
function run(){
  wrapPersistenceButtons();
}
function queue(){
  if(queued)return;queued=true;
  requestAnimationFrame(()=>{queued=false;run();});
}

new MutationObserver(queue).observe(document.body,{childList:true,subtree:true});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>{run();initFromHash();},{once:true});
else{run();initFromHash();}
setTimeout(run,250);
setTimeout(run,800);
})();