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
    .bl-picker.arsenal-mode .arsenal-body{display:grid!important;grid-template-columns:minmax(0,1fr)!important;min-height:0!important}
    .bl-picker.arsenal-mode .arsenal-rail{display:none!important}
    .bl-picker.arsenal-mode .arsenal-inspector{display:none!important}
    .bl-picker.arsenal-mode .arsenal-center{min-width:0!important;width:100%!important;overflow:hidden!important}
    .bl-picker.arsenal-mode .bl-picker-list{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;align-content:start!important;gap:12px!important;height:100%!important;max-height:none!important;padding:12px!important;overflow:auto!important}
    .bl-picker.arsenal-mode .arsenal-card{grid-template-columns:210px minmax(0,1fr)!important;min-height:390px!important;height:auto!important}
    .bl-picker.arsenal-mode .arsenal-art{min-height:390px!important;padding:22px!important}
    .bl-picker.arsenal-mode .arsenal-art img{height:165px!important;max-height:165px!important}
    .bl-picker.arsenal-mode .arsenal-copy{padding:16px 16px 14px!important}
    .bl-picker.arsenal-mode .arsenal-title strong{font-size:var(--ds-type-lg)!important;line-height:1.28!important}
    .bl-picker.arsenal-mode .arsenal-chips{margin-top:8px!important}
    .bl-picker.arsenal-mode .arsenal-description{display:grid!important;gap:6px!important;margin-top:11px!important;padding:9px 11px!important;border:1px solid #23333d!important;border-radius:7px!important;background:linear-gradient(145deg,#091218,#070c10)!important;box-shadow:inset 2px 0 #314955!important}
    .bl-picker.arsenal-mode .arsenal-description-label{color:#73838c!important;font-size:var(--ds-type-micro)!important;font-weight:900!important;letter-spacing:.14em!important;text-transform:uppercase!important}
    .bl-picker.arsenal-mode .arsenal-description-copy{display:-webkit-box!important;overflow:hidden!important;color:#aab5bb!important;font-size:var(--ds-type-xs)!important;line-height:1.48!important;-webkit-box-orient:vertical!important;-webkit-line-clamp:3!important}
    .bl-picker.arsenal-mode .arsenal-description.unavailable{border-color:#2b3338!important;box-shadow:inset 2px 0 #3b4449!important;background:#080d10!important}
    .bl-picker.arsenal-mode .arsenal-description.unavailable .arsenal-description-copy{color:#76848c!important;font-style:italic!important}
    .bl-picker.arsenal-mode .arsenal-mechanic{display:block!important;min-height:0!important;margin-top:10px!important;overflow:visible!important;color:inherit!important;font-size:inherit!important;line-height:inherit!important;-webkit-line-clamp:unset!important}
    .bl-picker.arsenal-mode .arsenal-skill{display:grid!important;grid-template-rows:auto minmax(0,1fr)!important;gap:7px!important;min-height:96px!important;padding:10px 11px!important;border:1px solid color-mix(in srgb,var(--ars-color,#3a4b54) 34%,#223039)!important;border-radius:7px!important;background:linear-gradient(145deg,color-mix(in srgb,var(--ars-color,#3a4b54) 7%,#071015),#070c10)!important;box-shadow:inset 2px 0 color-mix(in srgb,var(--ars-color,#3a4b54) 72%,transparent)!important}
    .bl-picker.arsenal-mode .arsenal-skill-head{display:flex!important;align-items:center!important;justify-content:space-between!important;gap:8px!important}
    .bl-picker.arsenal-mode .arsenal-skill-label{color:#73838c!important;font-size:var(--ds-type-micro)!important;font-weight:900!important;letter-spacing:.14em!important;text-transform:uppercase!important}
    .bl-picker.arsenal-mode .arsenal-skill-state{display:inline-flex!important;align-items:center!important;min-height:19px!important;padding:2px 6px!important;border:1px solid #354650!important;border-radius:999px!important;background:#081116!important;color:#90a0a8!important;font-size:var(--ds-type-micro)!important;font-weight:900!important;letter-spacing:.06em!important;white-space:nowrap!important}
    .bl-picker.arsenal-mode .arsenal-skill.resolved .arsenal-skill-state{border-color:#246653!important;color:#6fe1a8!important;background:#071712!important}
    .bl-picker.arsenal-mode .arsenal-skill.no-fixed .arsenal-skill-state{border-color:#3a4850!important;color:#95a2a9!important}
    .bl-picker.arsenal-mode .arsenal-skill.unresolved .arsenal-skill-state{border-color:#72551c!important;color:#efbd5d!important;background:#171104!important}
    .bl-picker.arsenal-mode .arsenal-skill-copy{display:-webkit-box!important;overflow:hidden!important;color:#aab5bb!important;font-size:var(--ds-type-xs)!important;line-height:1.48!important;-webkit-box-orient:vertical!important;-webkit-line-clamp:4!important}
    .bl-picker.arsenal-mode .arsenal-skill.no-fixed .arsenal-skill-copy{color:#829098!important}
    .bl-picker.arsenal-mode .arsenal-skill.unresolved .arsenal-skill-copy{color:#c4aa75!important}
    .bl-picker.arsenal-mode .arsenal-stats{gap:7px!important;margin-top:12px!important}
    .bl-picker.arsenal-mode .arsenal-stats span{padding:8px!important}
    .bl-picker.arsenal-mode .arsenal-evidence{gap:9px!important;margin-top:11px!important;padding-top:10px!important}
    .bl-picker.arsenal-mode .arsenal-actions{display:none!important}
    @media(max-width:1250px){
      .bl-picker.arsenal-mode .arsenal-body{grid-template-columns:minmax(0,1fr)!important}
      .bl-picker.arsenal-mode .arsenal-card{grid-template-columns:185px minmax(0,1fr)!important;min-height:380px!important}
      .bl-picker.arsenal-mode .arsenal-art{min-height:380px!important}
    }
    @media(max-width:940px){
      .bl-picker.arsenal-mode .arsenal-body{grid-template-columns:1fr!important}
      .bl-picker.arsenal-mode .bl-picker-list{grid-template-columns:1fr!important}
      .bl-picker.arsenal-mode .arsenal-card{grid-template-columns:190px minmax(0,1fr)!important}
    }
    @media(max-width:620px){
      .bl-picker.arsenal-mode .arsenal-card{grid-template-columns:1fr!important;min-height:0!important}
      .bl-picker.arsenal-mode .arsenal-art{min-height:160px!important;border-right:0!important;border-bottom:1px solid #21313a!important}
      .bl-picker.arsenal-mode .arsenal-art img{height:120px!important;max-height:120px!important}
      .bl-picker.arsenal-mode .arsenal-description-copy{-webkit-line-clamp:5!important}
      .bl-picker.arsenal-mode .arsenal-skill{min-height:0!important}
      .bl-picker.arsenal-mode .arsenal-skill-copy{-webkit-line-clamp:6!important}
    }
  `;
  document.head.append(style);

  function weaponForCard(card){
    const name=String(card?.querySelector('.arsenal-title strong')?.textContent||card?.querySelector('strong')?.textContent||'').trim();
    if(!name)return null;
    const weapons=Array.isArray(window.DS_WEAPON_MATH?.weapons)?window.DS_WEAPON_MATH.weapons:[];
    return weapons.find(weapon=>String(weapon?.name||'').trim()===name)||null;
  }

  function textFromPublishedDescription(value){
    if(typeof value==='string')return value.trim();
    if(!value||typeof value!=='object')return '';
    const status=String(value.publication_status||value.status||'').toLowerCase();
    if(status&&/(withheld|unresolved|conflict|suspect|blocked)/.test(status))return '';
    const text=value.text||value.description||value.value||value.published_text||value.player_facing_text||'';
    return typeof text==='string'?text.trim():'';
  }

  function verifiedWeaponDescription(weapon){
    const contract=weapon?.public_contract||{};
    const direct=[
      contract.player_facing_description,
      contract.weapon_description,
      contract.catalog_description,
      contract.description
    ];
    for(const candidate of direct){
      const text=textFromPublishedDescription(candidate);
      if(text)return text;
    }

    const evidence=contract.short_description_evidence;
    if(evidence&&typeof evidence==='object'){
      const publication=String(evidence.publication_status||'').toLowerCase();
      if(publication&&/(published|verified|approved|resolved-for-publication)/.test(publication)&&!/(withheld|suspect|conflict|unresolved)/.test(publication)){
        const text=textFromPublishedDescription(evidence.published_text||evidence.player_facing_text||evidence.resolved_text||evidence.description);
        if(text)return text;
      }
    }
    return '';
  }

  function enhanceWeaponDescriptions(scope=document){
    scope.querySelectorAll?.('.bl-picker.arsenal-mode .arsenal-card').forEach(card=>{
      card.querySelectorAll('.arsenal-actions').forEach(node=>node.remove());
      if(card.querySelector('.arsenal-description'))return;
      const copy=card.querySelector('.arsenal-copy');
      const mechanic=card.querySelector('.arsenal-mechanic');
      if(!copy||!mechanic)return;

      const description=verifiedWeaponDescription(weaponForCard(card));
      const box=document.createElement('span');
      box.className=`arsenal-description${description?'':' unavailable'}`;
      const label=document.createElement('span');
      label.className='arsenal-description-label';
      label.textContent='WEAPON DESCRIPTION';
      const body=document.createElement('span');
      body.className='arsenal-description-copy';
      body.textContent=description||'No verified player-facing weapon description is currently published for this record.';
      box.append(label,body);
      copy.insertBefore(box,mechanic);
    });
  }

  function enhanceWeaponSkillBlocks(scope=document){
    scope.querySelectorAll?.('.bl-picker.arsenal-mode .arsenal-mechanic:not([data-ds-skill-enhanced])').forEach(node=>{
      const original=String(node.textContent||'').trim();
      let state='resolved';
      let stateLabel='RESOLVED';
      let copy=original;

      if(!original||/no resolved mechanic text/i.test(original)){
        state='unresolved';
        stateLabel='REVIEW';
        copy='No player-facing special-skill text is currently resolved for this weapon.';
      }else if(/no fixed-skill reference/i.test(original)){
        state='no-fixed';
        stateLabel='NO FIXED SKILL';
        copy='No weapon-specific special skill is resolved in the current exact fixed-skill path.';
      }else if(/exact skill record missing/i.test(original)){
        state='unresolved';
        stateLabel='UNRESOLVED';
        copy='A special-skill reference exists, but its exact skill record is unresolved.';
      }

      node.dataset.dsSkillEnhanced='1';
      node.textContent='';
      const box=document.createElement('span');
      box.className=`arsenal-skill ${state}`;
      const head=document.createElement('span');
      head.className='arsenal-skill-head';
      const label=document.createElement('span');
      label.className='arsenal-skill-label';
      label.textContent='SPECIAL SKILL';
      const badge=document.createElement('span');
      badge.className='arsenal-skill-state';
      badge.textContent=stateLabel;
      const body=document.createElement('span');
      body.className='arsenal-skill-copy';
      body.textContent=copy;
      head.append(label,badge);
      box.append(head,body);
      node.append(box);
    });
  }

  const enhanceWeaponCards=(scope=document)=>{
    enhanceWeaponDescriptions(scope);
    enhanceWeaponSkillBlocks(scope);
  };

  const observeWeaponSkills=()=>{
    enhanceWeaponCards();
    const observer=new MutationObserver(mutations=>{
      for(const mutation of mutations){
        for(const added of mutation.addedNodes){
          if(added.nodeType!==1)continue;
          if(added.matches?.('.arsenal-card,.arsenal-mechanic,.arsenal-actions')) enhanceWeaponCards(added.parentElement||document);
          else if(added.querySelector?.('.arsenal-card,.arsenal-mechanic,.arsenal-actions')) enhanceWeaponCards(added);
        }
      }
    });
    observer.observe(document.body,{childList:true,subtree:true});
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',observeWeaponSkills,{once:true});
  else observeWeaponSkills();
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
