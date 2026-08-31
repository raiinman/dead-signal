(()=>{
'use strict';

const dialog=document.getElementById('picker');
const list=document.getElementById('pickerList');
const title=document.getElementById('pickerTitle');
const search=document.getElementById('pickerSearch');
const filters=document.getElementById('pickerFilters');
if(!dialog||!list||!title)return;

let queued=false;
let activeStyle='';
let searchHandlerBound=false;

const norm=v=>String(v??'').replace(/\s+/g,' ').trim();
const esc=v=>String(v??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
function setText(el,value){if(el&&norm(el.textContent)!==norm(value))el.textContent=value;}

function calibrationCards(){
  return [...list.querySelectorAll('.pick-card')].filter(card=>/Calibration Blueprint\s*-/i.test(norm(card.textContent||'')));
}

function isCalibrationPicker(){
  return /calibration blueprint/i.test(norm(title.textContent||''))||calibrationCards().length>0||dialog.classList.contains('ds-cal-style-picker-active');
}

function cardBlueprintName(card){
  const strong=card.querySelector('.pick-title-row strong');
  const text=norm(strong?.textContent||card.textContent||'');
  const m=text.match(/Calibration Blueprint\s*-\s*([^\n]+)/i);
  return norm(m?.[1]||text.replace(/^Calibration Blueprint\s*-\s*/i,''));
}

function cardRarity(card){
  const candidates=[
    card.dataset?.rarity,card.dataset?.quality,card.dataset?.grade,
    ...[...card.querySelectorAll('[data-rarity],[data-quality],[data-grade],.rarity-badge,.quality-badge,[class*="rarity"],[class*="quality"]')].flatMap(el=>[
      el.dataset?.rarity,el.dataset?.quality,el.dataset?.grade,el.textContent
    ])
  ];
  for(const value of candidates){
    const text=norm(value);
    for(const q of ['Legendary','Epic','Rare'])if(new RegExp(`\\b${q}\\b`,'i').test(text))return q;
  }
  const text=norm(card.textContent||'');
  for(const q of ['Legendary','Epic','Rare'])if(new RegExp(`\\b${q}\\b`,'i').test(text))return q;
  return '';
}

function styleFromBlueprint(name){
  let style=norm(name);
  const suffixes=[
    'Assault Rifle','Sniper Rifle','Machine Gun','Submachine Gun','Shotgun','Crossbow','Pistol','Melee','Rifle','Sniper','SMG'
  ];
  for(const suffix of suffixes){
    const re=new RegExp(`\\s+${suffix.replace(/ /g,'\\s+')}\\s*$`,'i');
    if(re.test(style)){
      const candidate=norm(style.replace(re,''));
      if(candidate)style=candidate;
      break;
    }
  }
  return style||name;
}

function buildGroups(cards){
  const groups=new Map();
  for(const card of cards){
    const blueprint=cardBlueprintName(card);
    const style=styleFromBlueprint(blueprint);
    const rarity=cardRarity(card);
    card.dataset.dsCalibrationStyle=style;
    card.dataset.dsCalibrationBlueprint=blueprint;
    if(!groups.has(style))groups.set(style,{style,rarities:new Set(),cards:[]});
    const group=groups.get(style);
    if(rarity)group.rarities.add(rarity);
    group.cards.push(card);
  }
  return [...groups.values()].sort((a,b)=>a.style.localeCompare(b.style));
}

function rarityOrder(values){
  const order={Rare:1,Epic:2,Legendary:3};
  return [...values].sort((a,b)=>(order[a]||99)-(order[b]||99));
}

function ensureShell(){
  let shell=dialog.querySelector('.ds-cal-style-shell');
  if(shell)return shell;
  shell=document.createElement('section');
  shell.className='ds-cal-style-shell';
  list.before(shell);
  shell.addEventListener('click',e=>{
    const button=e.target.closest('[data-ds-cal-style]');
    if(button){
      activeStyle=button.dataset.dsCalStyle||'';
      if(search)search.value='';
      render();
      return;
    }
    if(e.target.closest('[data-ds-cal-style-back]')){
      activeStyle='';
      if(search)search.value='';
      render();
    }
  });
  return shell;
}

function hideLegacyCalibrationFilter(){
  if(!filters)return;
  filters.dataset.dsCalStyleHidden='1';
  filters.style.display='none';
}

function restoreLegacyFilters(){
  if(!filters||filters.dataset.dsCalStyleHidden!=='1')return;
  filters.style.display='';
  delete filters.dataset.dsCalStyleHidden;
}

function renderStyleStep(groups,shell){
  const query=norm(search?.value||'').toLowerCase();
  list.style.display='none';
  setText(title,'Choose calibration style');
  if(search&&search.placeholder!=='Search calibration styles...')search.placeholder='Search calibration styles...';

  const visible=groups.filter(group=>!query||group.style.toLowerCase().includes(query));
  const signature=`styles|${query}|${visible.map(group=>`${group.style}:${rarityOrder(group.rarities).join(',')}`).join('|')}`;
  if(shell.dataset.signature===signature)return;

  shell.hidden=false;
  shell.innerHTML=`
    <div class="ds-cal-style-head">
      <span class="ds-cal-style-step">1</span>
      <div><small>CALIBRATION MOD TYPE</small><strong>Choose a Style</strong><p>Select the fixed Calibration Style first. Rarity and RNG rolls come after.</p></div>
    </div>
    <div class="ds-cal-style-grid">
      ${visible.map(group=>{
        const rarities=rarityOrder(group.rarities);
        return `<button type="button" class="ds-cal-style-card" data-ds-cal-style="${esc(group.style)}">
          <strong>${esc(group.style)}</strong>
          <span>${rarities.length?rarities.join(' · '):'Compatible calibration'}</span>
        </button>`;
      }).join('')||'<p class="ds-cal-style-empty">No compatible Calibration Styles match that search.</p>'}
    </div>`;
  shell.dataset.signature=signature;
}

function renderRarityStep(cards,shell){
  const matching=cards.filter(card=>card.dataset.dsCalibrationStyle===activeStyle);
  for(const card of cards)card.style.display=matching.includes(card)?'':'none';
  list.style.display='grid';
  setText(title,`Choose ${activeStyle} calibration`);
  if(search){
    if(search.value)search.value='';
    if(search.placeholder!=='Search this calibration style...')search.placeholder='Search this calibration style...';
  }

  const signature=`rarity|${activeStyle}|${matching.map(card=>`${card.dataset.dsCalibrationBlueprint}:${cardRarity(card)}`).join('|')}`;
  if(shell.dataset.signature===signature)return;

  shell.hidden=false;
  shell.innerHTML=`
    <div class="ds-cal-style-head ds-cal-style-head-rarity">
      <button type="button" class="ds-cal-style-back" data-ds-cal-style-back>← Styles</button>
      <span class="ds-cal-style-step">2</span>
      <div><small>CALIBRATION STYLE</small><strong>${esc(activeStyle)}</strong><p>Now choose the rarity of the Calibration Blueprint you actually have.</p></div>
    </div>`;
  shell.dataset.signature=signature;
}

function cleanup(){
  dialog.querySelector('.ds-cal-style-shell')?.remove();
  list.style.display='';
  for(const card of [...list.querySelectorAll('.pick-card')])card.style.display='';
  restoreLegacyFilters();
  dialog.classList.remove('ds-cal-style-picker-active');
}

function render(){
  const cards=calibrationCards();
  if(!cards.length&&!dialog.classList.contains('ds-cal-style-picker-active'))return;
  if(!isCalibrationPicker()||!cards.length){cleanup();return;}

  dialog.classList.add('ds-cal-style-picker-active');
  hideLegacyCalibrationFilter();
  const groups=buildGroups(cards);
  const styles=new Set(groups.map(g=>g.style));
  if(activeStyle&&!styles.has(activeStyle))activeStyle='';
  const host=ensureShell();

  if(activeStyle)renderRarityStep(cards,host);
  else{
    for(const card of cards)card.style.display='';
    renderStyleStep(groups,host);
  }
}

function queue(){
  if(queued)return;
  queued=true;
  requestAnimationFrame(()=>{queued=false;render();});
}

if(search&&!searchHandlerBound){
  search.addEventListener('input',()=>{if(isCalibrationPicker()&&!activeStyle)render();});
  searchHandlerBound=true;
}

dialog.addEventListener('close',()=>{
  activeStyle='';
  cleanup();
});

new MutationObserver(queue).observe(dialog,{childList:true,subtree:true,characterData:true});
document.addEventListener('click',e=>{
  if(e.target.closest?.('[data-pick]')&&/calib/i.test(String(e.target.closest('[data-pick]')?.dataset?.pick||'')))setTimeout(queue,0);
});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',queue,{once:true});else queue();
setTimeout(queue,250);
})();
