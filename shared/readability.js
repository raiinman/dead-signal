(()=>{
'use strict';

const STORAGE_KEY='dead-signal-font-size';
const MODES={
  compact:{label:'Compact'},
  default:{label:'Default'},
  large:{label:'Large'},
  xlarge:{label:'Extra Large'}
};
const root=document.documentElement;

function normalize(value){
  return Object.prototype.hasOwnProperty.call(MODES,value)?value:'default';
}

function readStored(){
  try{return normalize(localStorage.getItem(STORAGE_KEY)||'default')}
  catch(_){return 'default'}
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
    try{localStorage.setItem(STORAGE_KEY,mode)}catch(_){}
  }
  updateControls(mode);
  if(announce){
    root.dispatchEvent(new CustomEvent('dead-signal:font-size-change',{detail:{mode,label:MODES[mode].label}}));
  }
  return mode;
}

/* Apply before page paint when this script is loaded from <head>. */
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
    try{localStorage.removeItem(STORAGE_KEY)}catch(_){}
    return apply('default',{announce:true});
  }
};
})();
