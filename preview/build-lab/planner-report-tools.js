(()=>{
'use strict';

let queued=false;

const norm=v=>String(v??'').replace(/\s+/g,' ').trim();
const lines=[];
function text(el){return norm(el?.textContent||'');}
function unique(arr){return [...new Set(arr.filter(Boolean))];}

function toast(message){
  const host=document.getElementById('toast');
  if(host){
    host.textContent=message;
    host.classList.add('show');
    clearTimeout(toast.timer);
    toast.timer=setTimeout(()=>host.classList.remove('show'),1800);
  }
}
async function copyText(value,success){
  try{
    await navigator.clipboard.writeText(value);
    toast(success);
  }catch(_){
    window.prompt('Copy this text:',value);
  }
}

function buildIdentity(){
  const name=norm(document.getElementById('buildName')?.value)||'Unnamed Build';
  const author=norm(document.getElementById('buildAuthor')?.value);
  const type=norm(document.getElementById('buildType')?.value);
  const mode=window.DSBuildMode?.get?.()==='god'?'GOD ROLL':'MY GEAR';
  return {name,author,type,mode};
}
function selectedName(card){
  const name=text(card.querySelector('.item-name'));
  return name&&name.toLowerCase()!=='empty'?name:'';
}
function weaponLine(card,index){
  const labels=['Primary','Secondary','Melee'];
  const name=selectedName(card);if(!name)return '';
  const parts=[];
  const tier=card.querySelector('[data-weapon-tier]')?.selectedOptions?.[0]?.textContent;
  const stars=card.querySelector('[data-weapon-stars]')?.selectedOptions?.[0]?.textContent;
  if(tier)parts.push(norm(tier));if(stars)parts.push(norm(stars));
  const cal=norm(card.querySelector('.ds-wm-cal-picker')?.dataset?.calibrationName||'');
  if(cal&&!/^Select Calibration Blueprint$/i.test(cal))parts.push(`Cal: ${cal}`);
  const dmg=card.querySelector('[data-wm-roll-number]')?.value;
  if(dmg!=='')parts.push(`Weapon DMG ${dmg}%`);
  const sec=card.querySelector('[data-cal-secondary-choice]')?.selectedOptions?.[0]?.textContent;
  const secValue=card.querySelector('[data-cal-secondary-number]')?.value;
  if(sec&&secValue!=='')parts.push(`${norm(sec).replace(/\s*\/\/.*$/,'')} ${secValue}%`);
  return `${labels[index]||'Weapon'}: ${name}${parts.length?` — ${parts.join(' · ')}`:''}`;
}
function armorLines(){
  return [...document.querySelectorAll('.gear-card')].map(card=>{
    const slot=text(card.querySelector('.slot-label'));
    const name=selectedName(card);if(!name)return '';
    const mod=text(card.querySelector('.mini-select .choice span'));
    return `${slot||'Armor'}: ${name}${mod&&mod.toLowerCase()!=='select'?` — Mod: ${mod}`:''}`;
  }).filter(Boolean);
}
function systemLines(){
  return [...document.querySelectorAll('.system-card')].map(card=>{
    const slot=text(card.querySelector('.slot-label'));
    const name=selectedName(card);return name?`${slot}: ${name}`:'';
  }).filter(Boolean);
}
function cradleLines(){
  return [...document.querySelectorAll('#cradles .cradle.selected b')].map(el=>`Cradle: ${text(el)}`).filter(x=>!/:\s*$/.test(x));
}
function reportText(){
  const id=buildIdentity();
  const out=[`DEAD SIGNAL // ${id.name}`,`${id.mode}${id.type?` · ${id.type}`:''}${id.author?` · by ${id.author}`:''}`,''];
  const weapons=[...document.querySelectorAll('.weapon-card')].map(weaponLine).filter(Boolean);
  if(weapons.length)out.push('WEAPONS',...weapons,'');
  const armor=armorLines();if(armor.length)out.push('ARMOR',...armor,'');
  const systems=systemLines();if(systems.length)out.push('SYSTEMS',...systems,'');
  const cradles=cradleLines();if(cradles.length)out.push('CRADLES',...cradles,'');
  const notes=norm(document.getElementById('buildNotes')?.value);if(notes)out.push('NOTES',notes,'');
  out.push('Built with Dead Signal Ultimate Planner');
  return out.join('\n').replace(/\n{3,}/g,'\n\n');
}
function checklistText(){
  const id=buildIdentity();
  const items=[];
  [...document.querySelectorAll('.weapon-card,.gear-card,.system-card')].forEach(card=>{
    const name=selectedName(card);if(name)items.push(name);
    card.querySelectorAll('.mini-select .choice span').forEach(el=>{
      const v=text(el);if(v&&v.toLowerCase()!=='select')items.push(v);
    });
  });
  document.querySelectorAll('#cradles .cradle.selected b').forEach(el=>items.push(text(el)));
  const clean=unique(items).sort((a,b)=>a.localeCompare(b));
  return [`DEAD SIGNAL FARMING CHECKLIST // ${id.name}`,'',...clean.map(x=>`[ ] ${x}`)].join('\n');
}
function ensureTools(){
  const sticky=document.querySelector('#section-report .sticky');if(!sticky)return;
  let tools=document.getElementById('dsReportTools');
  if(!tools){
    tools=document.createElement('div');
    tools.id='dsReportTools';
    tools.className='ds-report-tools';
    tools.innerHTML='<button type="button" data-ds-copy-report>Copy Loadout Text</button><button type="button" data-ds-copy-checklist>Copy Farming Checklist</button>';
    const title=sticky.querySelector(':scope > .section-title');
    if(title)title.insertAdjacentElement('afterend',tools);else sticky.prepend(tools);
    tools.addEventListener('click',e=>{
      if(e.target.closest('[data-ds-copy-report]'))copyText(reportText(),'Loadout text copied.');
      if(e.target.closest('[data-ds-copy-checklist]'))copyText(checklistText(),'Farming checklist copied.');
    });
  }
}
function run(){ensureTools();}
function queue(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;run();});}
new MutationObserver(queue).observe(document.body,{childList:true,subtree:true});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run,{once:true});else run();
setTimeout(run,250);
})();
