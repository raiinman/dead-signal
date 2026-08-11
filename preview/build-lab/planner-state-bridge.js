(()=>{
'use strict';

/*
  PLAYER v1.5.2 — persistence bridge

  The recovered core app owns the canonical build payload, while the newer
  calibration presentation layers keep UI state in localStorage sidecars.
  This compatibility bridge keeps those layers isolated per build until the
  recovered core app is vendored and the extension fields can move directly
  into its schema.
*/

const STORAGE='dead-signal-community-planner-builds';
const SLOT_ORDER=['primary','secondary','melee'];
const EXT_KEY='dsExtension';
const EXT_VERSION=2;
let syncing=false;
let queued=false;

const norm=v=>String(v??'').replace(/\s+/g,' ').trim();
const finiteValue=v=>{
  if(v===null||v===undefined||v==='')return null;
  const n=Number(v);return Number.isFinite(n)?n:null;
};
const currentMode=()=>{
  if(window.DSBuildMode&&typeof window.DSBuildMode.get==='function')return window.DSBuildMode.get()==='god'?'god':'gear';
  try{return localStorage.getItem('dead-signal-build-mode')==='god'?'god':'gear';}catch(_){return 'gear';}
};
const cardForSlot=slot=>{
  const i=SLOT_ORDER.indexOf(slot);
  return i>=0?[...document.querySelectorAll('.weapon-card')][i]||null:null;
};
const slotForCard=card=>SLOT_ORDER[[...document.querySelectorAll('.weapon-card')].indexOf(card)]||null;

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
function dispatchChange(el){el.dispatchEvent(new Event('change',{bubbles:true}));}

function captureVisibleCalibration(slot){
  const card=cardForSlot(slot);
  if(!card)return null;
  const proxy=card.querySelector('.ds-wm-cal-picker');
  const attack=card.querySelector('[data-wm-roll-number]');
  const secondary=card.querySelector('[data-cal-secondary-number]');
  return {
    calibrationName:norm(proxy?.dataset?.calibrationName||''),
    calibrationRarity:norm(proxy?.dataset?.calibrationRarity||''),
    hasAttackControl:!!attack,
    attack:finiteValue(attack?.value),
    secondaryId:card.querySelector('[data-cal-secondary-choice]')?.value||'',
    hasSecondaryValueControl:!!secondary,
    secondaryValue:finiteValue(secondary?.value)
  };
}
function captureExtension(){
  return {
    version:EXT_VERSION,
    buildMode:currentMode(),
    calibration:Object.fromEntries(SLOT_ORDER.map(slot=>[slot,captureVisibleCalibration(slot)]))
  };
}

function syncSlotToCore(slot,captured){
  if(!captured)return;
  let card=cardForSlot(slot);if(!card)return;

  if(captured.secondaryId){
    const nativeSelect=card.querySelector(`[data-cal-bonus="${slot}"]`);
    const matcher=ruleMatcher(captured.secondaryId);
    if(nativeSelect&&matcher){
      const option=[...nativeSelect.options].find(o=>matcher.test(norm(o.textContent)));
      if(option&&nativeSelect.value!==option.value){nativeSelect.value=option.value;dispatchChange(nativeSelect);}
    }
  }

  card=cardForSlot(slot);if(!card)return;
  if(currentMode()==='gear'&&captured.hasAttackControl){
    const nativeAttack=card.querySelector(`[data-cal-attack="${slot}"]`);
    if(nativeAttack&&finiteValue(nativeAttack.value)!==captured.attack){
      nativeAttack.value=captured.attack===null?'':String(captured.attack);
      dispatchChange(nativeAttack);
    }
  }

  card=cardForSlot(slot);if(!card)return;
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
  try{for(const slot of SLOT_ORDER)syncSlotToCore(slot,snapshots[slot]);}
  finally{syncing=false;}
}

function setSideNumber(el,value){
  if(!el)return;
  const next=value===null?'':String(value);
  if(el.value!==next){el.value=next;dispatchChange(el);}
}
function restoreSlotFromExtension(slot,saved){
  if(!saved)return false;
  let card=cardForSlot(slot);if(!card)return false;

  const sideSelect=card.querySelector('[data-cal-secondary-choice]');
  if(sideSelect){
    const next=saved.secondaryId||'';
    if(sideSelect.value!==next){sideSelect.value=next;dispatchChange(sideSelect);}
  }

  card=cardForSlot(slot);if(!card)return false;
  if(currentMode()==='gear'){
    if(saved.hasAttackControl)setSideNumber(card.querySelector('[data-wm-roll-number]'),saved.attack);
    card=cardForSlot(slot);if(!card)return false;
    if(saved.hasSecondaryValueControl)setSideNumber(card.querySelector('[data-cal-secondary-number]'),saved.secondaryValue);
  }
  return true;
}
function syncSlotFromCore(slot){
  let card=cardForSlot(slot);if(!card)return;

  const nativeAttack=card.querySelector(`[data-cal-attack="${slot}"]`);
  const main=card.querySelector('[data-wm-roll-number]');
  if(nativeAttack&&main&&currentMode()==='gear'){
    const v=finiteValue(nativeAttack.value);
    if(v!==null&&finiteValue(main.value)!==v){main.value=String(v);dispatchChange(main);}
  }

  card=cardForSlot(slot);if(!card)return;
  const nativeSelect=card.querySelector(`[data-cal-bonus="${slot}"]`);
  const sideSelect=card.querySelector('[data-cal-secondary-choice]');
  if(nativeSelect&&sideSelect){
    const ruleId=ruleIdFromLabel(nativeSelect.selectedOptions?.[0]?.textContent||'');
    if(ruleId&&sideSelect.value!==ruleId){sideSelect.value=ruleId;dispatchChange(sideSelect);}
  }

  card=cardForSlot(slot);if(!card)return;
  const nativeBonus=card.querySelector(`[data-cal-bonus-value="${slot}"]`);
  const sideNumber=card.querySelector('[data-cal-secondary-number]');
  if(nativeBonus&&sideNumber&&currentMode()==='gear'){
    const v=finiteValue(nativeBonus.value);
    if(v!==null&&finiteValue(sideNumber.value)!==v){sideNumber.value=String(v);dispatchChange(sideNumber);}
  }
}
function syncCoreToCalibrationUi(){
  if(syncing)return;
  syncing=true;
  try{for(const slot of SLOT_ORDER)syncSlotFromCore(slot);}
  finally{syncing=false;}
}

function augmentState(raw){
  if(!raw||typeof raw!=='object')return raw;
  raw[EXT_KEY]=captureExtension();
  return raw;
}
function extensionFromState(raw){
  const ext=raw?.[EXT_KEY];
  return ext&&typeof ext==='object'?ext:null;
}
function applyMode(mode){
  if(mode!=='gear'&&mode!=='god')return;
  if(window.DSBuildMode&&typeof window.DSBuildMode.set==='function')window.DSBuildMode.set(mode,{confirmGod:false,persist:true});
  else try{localStorage.setItem('dead-signal-build-mode',mode);}catch(_){}
}
function readSaved(){try{return JSON.parse(localStorage.getItem(STORAGE)||'[]')||[];}catch(_){return [];}}
function writeSaved(list){try{localStorage.setItem(STORAGE,JSON.stringify(list));}catch(_){} }
function augmentNewestSaved(){
  const list=readSaved();if(!list.length)return;
  let latest=0;
  for(let i=1;i<list.length;i++)if(String(list[i]?.updated||'')>String(list[latest]?.updated||''))latest=i;
  if(list[latest]?.state)augmentState(list[latest].state);
  writeSaved(list);
}
function stateForSavedId(id){return readSaved().find(x=>String(x?.id)===String(id))?.state||null;}

function decodeSharedState(url){
  try{
    const m=String(url||'').match(/#b=([^&]+)$/);if(!m)return null;
    let b=m[1].replace(/-/g,'+').replace(/_/g,'/');while(b.length%4)b+='=';
    const bin=atob(b),bytes=Uint8Array.from(bin,c=>c.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes));
  }catch(_){return null;}
}
function encodeSharedState(raw){
  const bytes=new TextEncoder().encode(JSON.stringify(raw));let bin='';
  bytes.forEach(b=>bin+=String.fromCharCode(b));
  return btoa(bin).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}
function transformShareUrl(url){
  const raw=decodeSharedState(url);if(!raw)return url;
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
    save.onclick=function(e){syncCalibrationUiToCore();const result=original.call(this,e);augmentNewestSaved();return result;};
    save.dataset.dsPersistenceWrapped='1';
  }

  const exportBtn=document.getElementById('exportBtn');
  if(exportBtn&&exportBtn.onclick&&!exportBtn.dataset.dsPersistenceWrapped){
    const original=exportBtn.onclick;
    exportBtn.onclick=function(e){
      syncCalibrationUiToCore();
      const NativeBlob=window.Blob;
      function DSBlob(parts,opts){return new NativeBlob(Array.isArray(parts)?parts.map(transformExportPart):parts,opts);}
      DSBlob.prototype=NativeBlob.prototype;Object.setPrototypeOf(DSBlob,NativeBlob);window.Blob=DSBlob;
      try{return original.call(this,e);}finally{window.Blob=NativeBlob;}
    };
    exportBtn.dataset.dsPersistenceWrapped='1';
  }

  const share=document.getElementById('shareBtn');
  if(share&&share.onclick&&!share.dataset.dsPersistenceWrapped){
    const original=share.onclick;
    share.onclick=function(e){
      syncCalibrationUiToCore();
      const clipboard=navigator.clipboard,originalWrite=clipboard?.writeText?.bind(clipboard),originalPrompt=window.prompt;
      let patchedClipboard=false;
      if(clipboard&&originalWrite){try{clipboard.writeText=url=>originalWrite(transformShareUrl(url));patchedClipboard=true;}catch(_){} }
      window.prompt=(message,value)=>originalPrompt.call(window,message,transformShareUrl(value));
      let result;
      try{result=original.call(this,e);}catch(err){
        if(patchedClipboard)try{clipboard.writeText=originalWrite;}catch(_){}
        window.prompt=originalPrompt;throw err;
      }
      return Promise.resolve(result).finally(()=>{
        if(patchedClipboard)try{clipboard.writeText=originalWrite;}catch(_){}
        window.prompt=originalPrompt;
      });
    };
    share.dataset.dsPersistenceWrapped='1';
  }
}

function applyLoadedStateExtensions(raw){
  const ext=extensionFromState(raw);
  if(ext?.buildMode)applyMode(ext.buildMode);
  const restore=()=>{
    if(syncing)return;
    syncing=true;
    try{
      for(const slot of SLOT_ORDER){
        if(!restoreSlotFromExtension(slot,ext?.calibration?.[slot]))syncSlotFromCore(slot);
      }
    }finally{syncing=false;}
  };
  setTimeout(restore,30);setTimeout(restore,180);setTimeout(restore,500);
}

document.addEventListener('click',e=>{
  const load=e.target.closest?.('[data-load-id]'),clone=e.target.closest?.('[data-clone-id]');
  if(load||clone){
    const raw=stateForSavedId((load||clone).dataset[load?'loadId':'cloneId']);
    if(raw)setTimeout(()=>applyLoadedStateExtensions(raw),0);
  }
},true);

document.addEventListener('change',e=>{
  if(syncing)return;
  if(e.target.matches?.('[data-wm-roll-number],[data-cal-secondary-choice],[data-cal-secondary-number]')){
    const slot=slotForCard(e.target.closest('.weapon-card'));
    if(slot)setTimeout(()=>syncSlotToCore(slot,captureVisibleCalibration(slot)),0);
  }
  if(e.target.id==='importFile'){
    const file=e.target.files?.[0];
    if(file&&typeof file.text==='function')file.text().then(text=>{
      try{const obj=JSON.parse(text);setTimeout(()=>applyLoadedStateExtensions(obj?.state||obj),80);}catch(_){}
    });
  }
},true);

function initFromHash(){const raw=decodeSharedState(location.href);if(raw)applyLoadedStateExtensions(raw);}
function run(){wrapPersistenceButtons();}
function queue(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;run();});}

new MutationObserver(queue).observe(document.body,{childList:true,subtree:true});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>{run();initFromHash();},{once:true});
else{run();initFromHash();}
setTimeout(run,250);setTimeout(run,800);
})();