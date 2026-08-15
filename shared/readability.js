(()=>{
'use strict';

const STORAGE_KEY='dead-signal-font-size';
const SCHEMA_KEY='dead-signal-font-size-schema';
const SCHEMA_VERSION='2';
const MODES={
  compact:{label:'Smaller'},
  default:{label:'Default'},
  large:{label:'Larger'},
  xlarge:{label:'Maximum'}
};
const root=document.documentElement;

/* Build Lab selector geometry is injected from an already-deployed asset so it cannot
   be lost behind stale page CSS or copy-only deployment omissions. */
if(/^\/build-planner\/?$/i.test(location.pathname)){
  const style=document.createElement('style');
  style.id='ds-build-lab-weapon-card-geometry';
  style.textContent=`
    .bl-picker.arsenal-mode{height:min(90vh,1040px)!important;max-height:none!important}
    .bl-picker.arsenal-mode .arsenal-body{display:grid!important;grid-template-columns:150px minmax(0,1fr)!important;min-height:0!important}
    .bl-picker.arsenal-mode .arsenal-inspector{display:none!important}
    .bl-picker.arsenal-mode .bl-picker-list{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;align-content:start!important;gap:12px!important;height:100%!important;max-height:none!important;padding:12px!important;overflow:auto!important}
    .bl-picker.arsenal-mode .arsenal-card{grid-template-columns:190px minmax(0,1fr)!important;min-height:310px!important;height:auto!important}
    .bl-picker.arsenal-mode .arsenal-art{min-height:310px!important;padding:20px!important}
    .bl-picker.arsenal-mode .arsenal-art img{height:155px!important;max-height:155px!important}
    .bl-picker.arsenal-mode .arsenal-copy{padding:16px 16px 14px!important}
    .bl-picker.arsenal-mode .arsenal-title strong{font-size:var(--ds-type-lg)!important;line-height:1.28!important}
    .bl-picker.arsenal-mode .arsenal-chips{margin-top:8px!important}
    .bl-picker.arsenal-mode .arsenal-mechanic{display:-webkit-box!important;min-height:82px!important;margin-top:12px!important;overflow:hidden!important;color:#a7b2b8!important;font-size:var(--ds-type-xs)!important;line-height:1.52!important;-webkit-box-orient:vertical!important;-webkit-line-clamp:5!important}
    .bl-picker.arsenal-mode .arsenal-stats{gap:7px!important;margin-top:12px!important}
    .bl-picker.arsenal-mode .arsenal-stats span{padding:8px!important}
    .bl-picker.arsenal-mode .arsenal-evidence{gap:9px!important;margin-top:11px!important;padding-top:10px!important}
    .bl-picker.arsenal-mode .arsenal-actions{margin-top:auto!important;padding-top:11px!important}
    @media(max-width:1250px){
      .bl-picker.arsenal-mode .arsenal-body{grid-template-columns:125px minmax(0,1fr)!important}
      .bl-picker.arsenal-mode .arsenal-card{grid-template-columns:160px minmax(0,1fr)!important;min-height:300px!important}
      .bl-picker.arsenal-mode .arsenal-art{min-height:300px!important}
    }
    @media(max-width:940px){
      .bl-picker.arsenal-mode .arsenal-body{grid-template-columns:1fr!important}
      .bl-picker.arsenal-mode .arsenal-rail{display:none!important}
      .bl-picker.arsenal-mode .bl-picker-list{grid-template-columns:1fr!important}
      .bl-picker.arsenal-mode .arsenal-card{grid-template-columns:175px minmax(0,1fr)!important}
    }
    @media(max-width:620px){
      .bl-picker.arsenal-mode .arsenal-card{grid-template-columns:1fr!important;min-height:0!important}
      .bl-picker.arsenal-mode .arsenal-art{min-height:160px!important;border-right:0!important;border-bottom:1px solid #21313a!important}
      .bl-picker.arsenal-mode .arsenal-art img{height:120px!important;max-height:120px!important}
      .bl-picker.arsenal-mode .arsenal-mechanic{min-height:0!important;-webkit-line-clamp:6!important}
    }
  `;
  document.head.append(style);
}

function normalize(value){
  return Object.prototype.hasOwnProperty.call(MODES,value)?value:'default';
}

function readStored(){
  try{
    const stored=localStorage.getItem(STORAGE_KEY);
    const schema=localStorage.getItem(SCHEMA_KEY);
    if(!stored)return 'default';
    if(schema===SCHEMA_VERSION)return normalize(stored);

    /* v1 -> v2 migration preserves the user's visible size where possible:
       old Default -> new Smaller, old Large -> new Default,
       old Extra Large -> new Larger. */
    const migrated={compact:'compact',default:'compact',large:'default',xlarge:'large'}[stored]||'default';
    localStorage.setItem(STORAGE_KEY,migrated);
    localStorage.setItem(SCHEMA_KEY,SCHEMA_VERSION);
    return migrated;
  }catch(_){return 'default'}
}

function updateControls(mode){
  document.querySelectorAll('[data-ds-font-size-choice]').forEach(button=>{
    const active=button.dataset.dsFontSizeChoice===mode;
    button.setAttribute('aria-pressed',active?'true':'false');
  });
  document.querySelectorAll('[data-ds-font-size-status]').forEach(node=>{
    node.textContent=MODES[mode].label;
  });
}

function apply(mode,{persist=false,announce=false}={}){
  mode=normalize(mode);
  root.dataset.dsFontSize=mode;
  if(persist){
    try{
      localStorage.setItem(STORAGE_KEY,mode);
      localStorage.setItem(SCHEMA_KEY,SCHEMA_VERSION);
    }catch(_){}
  }
  updateControls(mode);
  if(announce){
    root.dispatchEvent(new CustomEvent('dead-signal:font-size-change',{detail:{mode,label:MODES[mode].label}}));
  }
  return mode;
}

apply(readStored());

function bind(){
  updateControls(normalize(root.dataset.dsFontSize));
  document.addEventListener('click',event=>{
    const button=event.target.closest('[data-ds-font-size-choice]');
    if(!button)return;
    apply(button.dataset.dsFontSizeChoice,{persist:true,announce:true});
  });
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});
else bind();

window.DSReadability={
  modes:Object.freeze({...MODES}),
  get:()=>normalize(root.dataset.dsFontSize),
  set:mode=>apply(mode,{persist:true,announce:true}),
  reset:()=>{
    try{
      localStorage.removeItem(STORAGE_KEY);
      localStorage.setItem(SCHEMA_KEY,SCHEMA_VERSION);
    }catch(_){}
    return apply('default',{announce:true});
  }
};
})();
