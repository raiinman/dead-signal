(()=>{
'use strict';

const STORAGE_KEY='dead-signal-build-mode';
const DEFAULT_MODE='gear';
const MODES={
  gear:{
    short:'MY GEAR',
    title:'MY GEAR // ACTUAL BUILD',
    notice:'Actual-build mode is active. Dead Signal uses mined deterministic game values and should ask you only for account-specific RNG rolls that the game server assigned to your gear.'
  },
  god:{
    short:'GOD ROLL',
    title:'GOD ROLL // THEORETICAL BUILD',
    notice:'Theorycraft mode is active. Maximum legal RNG values are assumed and may not match equipment you actually own.'
  }
};

let currentMode=DEFAULT_MODE;

function validMode(value){return value==='gear'||value==='god'?value:DEFAULT_MODE;}
function readMode(){
  try{return validMode(localStorage.getItem(STORAGE_KEY)||DEFAULT_MODE);}catch(_){return DEFAULT_MODE;}
}
function storeMode(mode){try{localStorage.setItem(STORAGE_KEY,mode);}catch(_){/* storage unavailable */}}

function ensureUi(){
  const plan=document.getElementById('section-plan');
  if(plan&&!document.querySelector('[data-ds-build-mode-gate]')){
    const gate=document.createElement('div');
    gate.className='ds-build-mode-gate';
    gate.dataset.dsBuildModeGate='1';
    gate.innerHTML=`
      <div class="ds-build-mode-intro">
        <div>
          <small>BUILD MODE // CHOOSE BEFORE YOU BUILD</small>
          <strong>Are you planning your actual gear or the theoretical ceiling?</strong>
          <p>This choice stays visible while you work so a God Roll theorycraft cannot be mistaken for gear you actually own.</p>
        </div>
      </div>
      <div class="ds-build-mode-options" role="group" aria-label="Choose build mode">
        <button type="button" class="ds-build-mode-choice" data-ds-mode-choice="gear" aria-pressed="true">
          <span class="mode-line"><span class="mode-name">MY GEAR</span><span class="mode-status">SELECTED</span></span>
          <span class="mode-sub">Actual owned build</span>
          <span class="mode-help">Use the rolls on the equipment you actually have. Dead Signal fills deterministic game data automatically.</span>
        </button>
        <button type="button" class="ds-build-mode-choice" data-ds-mode-choice="god" aria-pressed="false">
          <span class="mode-line"><span class="mode-name">GOD ROLL</span><span class="mode-status">SELECTED</span></span>
          <span class="mode-sub">Theoretical maximum build</span>
          <span class="mode-help">Use maximum legal RNG values for theorycrafting and build comparison. These values may not exist on your gear.</span>
        </button>
      </div>
      <div id="buildModeNotice" class="ds-build-mode-notice" role="status" aria-live="polite"></div>`;
    const title=plan.querySelector(':scope > .section-title');
    if(title)title.insertAdjacentElement('afterend',gate); else plan.prepend(gate);
  }

  const actions=document.querySelector('.topbar .actions');
  if(actions&&!document.getElementById('buildModeTopStatus')){
    const top=document.createElement('span');
    top.id='buildModeTopStatus';
    top.className='ds-build-mode-top-status';
    top.textContent='MY GEAR';
    actions.prepend(top);
  }

  const report=document.querySelector('#section-report .sticky');
  if(report&&!document.getElementById('buildModeReportStatus')){
    const status=document.createElement('div');
    status.id='buildModeReportStatus';
    status.className='ds-build-mode-report-status';
    status.innerHTML='<small>BUILD MODE</small><strong>MY GEAR // ACTUAL BUILD</strong>';
    const title=report.querySelector(':scope > .section-title');
    if(title)title.insertAdjacentElement('afterend',status); else report.prepend(status);
  }
}

function render(mode){
  currentMode=validMode(mode);
  const spec=MODES[currentMode];
  document.body.dataset.dsBuildMode=currentMode;

  document.querySelectorAll('[data-ds-mode-choice]').forEach(btn=>{
    const selected=btn.dataset.dsModeChoice===currentMode;
    btn.setAttribute('aria-pressed',selected?'true':'false');
  });

  const notice=document.getElementById('buildModeNotice');
  if(notice)notice.textContent=spec.notice;

  const top=document.getElementById('buildModeTopStatus');
  if(top){
    top.textContent=spec.short;
    top.dataset.mode=currentMode;
    top.title=spec.title;
  }

  const report=document.getElementById('buildModeReportStatus');
  if(report){
    report.dataset.mode=currentMode;
    const strong=report.querySelector('strong');
    if(strong)strong.textContent=spec.title;
  }
}

function choose(mode,{confirmGod=true,persist=true}={}){
  const next=validMode(mode);
  if(next===currentMode)return true;

  if(next==='god'&&confirmGod){
    const ok=window.confirm(
      'Switch to GOD ROLL / THEORETICAL BUILD?\n\n'+
      'Dead Signal will treat RNG-based gear values as theoretical maximums. '+
      'This mode may show stats you do not actually own in game.'
    );
    if(!ok){render(currentMode);return false;}
  }

  render(next);
  if(persist)storeMode(next);
  window.dispatchEvent(new CustomEvent('dead-signal:build-mode-change',{detail:{mode:next}}));
  return true;
}

function warnTheorycraftAction(event){
  if(currentMode!=='god')return;
  const target=event.target.closest('#saveBtn,#shareBtn,#exportBtn');
  if(!target)return;
  const notice=document.getElementById('buildModeNotice');
  if(!notice)return;
  notice.textContent='GOD ROLL mode is active. Saved/exported/shared planner data may represent theoretical maximum RNG values, not gear you actually own.';
}

function init(){
  ensureUi();
  currentMode=readMode();
  render(currentMode);

  document.querySelectorAll('[data-ds-mode-choice]').forEach(btn=>{
    btn.addEventListener('click',()=>choose(btn.dataset.dsModeChoice));
  });

  document.addEventListener('click',warnTheorycraftAction);

  window.DSBuildMode={
    get:()=>currentMode,
    set:(mode,options)=>choose(mode,options),
    modes:{...MODES}
  };
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
else init();
})();
