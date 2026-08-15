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
 * Build Lab weapon-selector rendering/data ownership lives in weapon-public-adapter.js.
 * This shared asset loads after page CSS and supplies only late viewport/geometry guards
 * so page CSS cannot collapse the selector's results surface or defeat pagination.
 */
if(/^\/build-planner\/?$/i.test(location.pathname)){
  const style=document.createElement('style');
  style.id='ds-build-lab-selector-viewport-guard';
  style.textContent=`
    /* Pagination/filter state always wins over legacy card display rules. */
    html body #picker.arsenal-mode .bl-picker-list > .bl-pick[hidden]{
      display:none!important;
    }

    /* Desktop/tablet: one flex column, with the results list consuming the entire
       space between controls and footer. This removes the dead black cavity. */
    html body #picker.arsenal-mode{
      display:flex!important;
      flex-direction:column!important;
      overflow:hidden!important;
    }
    html body #picker.arsenal-mode .bl-picker-head,
    html body #picker.arsenal-mode .bl-picker-tools,
    html body #picker.arsenal-mode .arsenal-secondary-tools,
    html body #picker.arsenal-mode .arsenal-footer{
      flex:0 0 auto!important;
    }
    html body #picker.arsenal-mode .arsenal-body{
      display:block!important;
      flex:1 1 auto!important;
      width:100%!important;
      height:auto!important;
      min-height:0!important;
      overflow:hidden!important;
    }
    html body #picker.arsenal-mode .arsenal-center{
      width:100%!important;
      height:100%!important;
      min-width:0!important;
      min-height:0!important;
      overflow:hidden!important;
    }
    html body #picker.arsenal-mode .bl-picker-list{
      display:grid!important;
      grid-template-columns:repeat(2,minmax(0,1fr))!important;
      align-content:start!important;
      width:100%!important;
      height:100%!important;
      max-height:none!important;
      min-height:0!important;
      padding:12px!important;
      gap:12px!important;
      overflow-y:auto!important;
      overflow-x:hidden!important;
    }

    /* Approved readable card geometry. */
    html body #picker.arsenal-mode .arsenal-card{
      grid-template-columns:200px minmax(0,1fr)!important;
      min-height:320px!important;
      height:auto!important;
    }
    html body #picker.arsenal-mode .arsenal-art{
      min-height:320px!important;
      padding:24px 18px!important;
    }
    html body #picker.arsenal-mode .arsenal-art img{
      height:170px!important;
      max-height:170px!important;
    }
    html body #picker.arsenal-mode .arsenal-copy{
      padding:14px 15px 12px!important;
    }
    html body #picker.arsenal-mode .arsenal-description:not(.unavailable) .arsenal-description-copy{
      font-size:var(--ds-type-xs)!important;
      line-height:1.5!important;
      -webkit-line-clamp:3!important;
    }
    html body #picker.arsenal-mode .arsenal-description.unavailable{
      display:flex!important;
      align-items:center!important;
      gap:7px!important;
      min-height:27px!important;
      margin-top:8px!important;
      padding:4px 7px!important;
      border:1px solid #28343b!important;
      border-radius:5px!important;
      background:#070c10!important;
    }
    html body #picker.arsenal-mode .arsenal-description.unavailable .arsenal-section-label{
      margin:0!important;
      white-space:nowrap!important;
    }
    html body #picker.arsenal-mode .arsenal-description.unavailable .arsenal-description-copy{
      display:none!important;
    }
    html body #picker.arsenal-mode .arsenal-description.unavailable::after{
      content:'NOT VERIFIED FOR PUBLICATION';
      display:inline-flex!important;
      align-items:center!important;
      min-height:17px!important;
      padding:1px 6px!important;
      border:1px solid #3c464c!important;
      border-radius:999px!important;
      color:#87949b!important;
      font-size:var(--ds-type-micro)!important;
      font-style:normal!important;
      font-weight:900!important;
      letter-spacing:.04em!important;
    }
    html body #picker.arsenal-mode .arsenal-skill-copy{
      font-size:var(--ds-type-xs)!important;
      line-height:1.5!important;
      -webkit-line-clamp:4!important;
    }

    @media(max-width:1050px){
      html body #picker.arsenal-mode .bl-picker-list{
        grid-template-columns:1fr!important;
      }
      html body #picker.arsenal-mode .arsenal-card{
        grid-template-columns:190px minmax(0,1fr)!important;
        min-height:310px!important;
      }
      html body #picker.arsenal-mode .arsenal-art{
        min-height:310px!important;
      }
      html body #picker.arsenal-mode .arsenal-art img{
        height:155px!important;
        max-height:155px!important;
      }
    }

    /* Mobile: the whole modal is the scroll surface. This avoids nested-scroll traps
       while still preserving exactly ten paginated records. */
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
        position:static!important;
        height:auto!important;
        max-height:none!important;
        min-height:0!important;
      }
      html body #picker.arsenal-mode .arsenal-body,
      html body #picker.arsenal-mode .arsenal-center,
      html body #picker.arsenal-mode .bl-picker-list{
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
      html body #picker.arsenal-mode .arsenal-description:not(.unavailable) .arsenal-description-copy{
        -webkit-line-clamp:4!important;
      }
      html body #picker.arsenal-mode .arsenal-skill-copy{
        -webkit-line-clamp:5!important;
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
