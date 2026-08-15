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

/*
 * Build Lab weapon-selector ownership lives in weapon-public-adapter.js.
 * Keep readability.js out of selector rendering/geometry so the two layers do not
 * fight each other. The only selector rules here are late-loading viewport guards,
 * because this shared asset is guaranteed to load after page CSS.
 */
if(/^\/build-planner\/?$/i.test(location.pathname)){
  const style=document.createElement('style');
  style.id='ds-build-lab-mobile-selector-scroll';
  style.textContent=`
    /* Pagination/filter state must always win over any card display rule. */
    html body #picker.arsenal-mode .bl-picker-list > .bl-pick[hidden]{
      display:none!important;
    }
    @media(max-width:680px){
      html body #picker.arsenal-mode{
        display:block!important;
        width:calc(100vw - 12px)!important;
        height:auto!important;
        max-height:calc(100dvh - 12px)!important;
        margin:auto!important;
        padding:0!important;
        overflow-y:auto!important;
        overflow-x:hidden!important;
        overscroll-behavior:contain!important;
        -webkit-overflow-scrolling:touch!important;
      }
      html body #picker.arsenal-mode .bl-picker-head,
      html body #picker.arsenal-mode .bl-picker-tools,
      html body #picker.arsenal-mode .arsenal-secondary-tools,
      html body #picker.arsenal-mode .arsenal-body,
      html body #picker.arsenal-mode .arsenal-center,
      html body #picker.arsenal-mode .bl-picker-list,
      html body #picker.arsenal-mode .arsenal-footer{
        display:block!important;
        position:static!important;
        height:auto!important;
        max-height:none!important;
        min-height:0!important;
        overflow:visible!important;
      }
      html body #picker.arsenal-mode .bl-picker-list{
        display:grid!important;
        grid-template-columns:1fr!important;
        padding:10px!important;
        gap:10px!important;
      }
      html body #picker.arsenal-mode .bl-picker-list > .bl-pick[hidden]{
        display:none!important;
      }
      html body #picker.arsenal-mode .arsenal-card{
        grid-template-columns:1fr!important;
        min-height:0!important;
      }
      html body #picker.arsenal-mode .arsenal-art{
        min-height:150px!important;
        border-right:0!important;
        border-bottom:1px solid #1f3038!important;
      }
      html body #picker.arsenal-mode .arsenal-art img{
        height:115px!important;
        max-height:115px!important;
      }
      html body #picker.arsenal-mode .arsenal-footer{
        display:flex!important;
        flex-wrap:wrap!important;
        gap:8px!important;
        padding:10px!important;
      }
      html body #picker.arsenal-mode .arsenal-footer-spacer{display:none!important}
      html body #picker.arsenal-mode .arsenal-confirm{width:100%!important}
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
