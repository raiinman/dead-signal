(()=>{
'use strict';

const D=window.DS_COMMUNITY||{};
const weapons=(D.weapons||[]).filter(x=>x&&x.id&&x.name);
if(!weapons.length)return;

const byId=new Map(weapons.map(x=>[String(x.id),x]));
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const norm=s=>String(s??'').replace(/\s+/g,' ').trim();
const numeric=v=>v!==null&&v!==''&&Number.isFinite(Number(v));
const fmt=v=>numeric(v)?Number(v).toLocaleString(undefined,{maximumFractionDigits:2}):'—';
const sign=v=>Number(v)>0?`+${fmt(v)}`:fmt(v);

const STAT_ROWS=[
  ['damage','DMG',''],
  ['rpm','RPM',''],
  ['magazine','MAG',''],
  ['reload','RELOAD','s'],
  ['critRate','CRIT RATE','%'],
  ['critDamage','CRIT DMG','%'],
  ['weakspot','WEAKSPOT','%'],
  ['range','RANGE',''],
  ['effectiveRange','EFFECTIVE',''],
  ['mobility','MOBILITY',''],
  ['pellets','PELLETS','']
];

function rarityClass(item){
  const v=String(item?.rarity||'').toLowerCase();
  if(/legendary|gold/.test(v))return 'legendary';
  if(/epic|purple/.test(v))return 'epic';
  if(/rare|blue/.test(v))return 'rare';
  if(/common|green|uncommon/.test(v))return 'common';
  return 'normal';
}
function effectText(x){
  if(!x)return'';
  if(x.feature)return norm(x.feature);
  if(x.effect)return norm(x.effect);
  if(x.description)return norm(x.description);
  if(Array.isArray(x.effects))return x.effects.filter(Boolean).join(' · ');
  return'';
}
function optionHtml(selected){
  const groups=new Map();
  for(const w of weapons){
    const key=norm(w.type)||'Other';
    if(!groups.has(key))groups.set(key,[]);
    groups.get(key).push(w);
  }
  return [...groups.entries()].sort((a,b)=>a[0].localeCompare(b[0])).map(([type,items])=>
    `<optgroup label="${esc(type)}">${items.sort((a,b)=>a.name.localeCompare(b.name)).map(w=>`<option value="${esc(w.id)}" ${String(w.id)===String(selected)?'selected':''}>${esc(w.name)}${w.rarity?` — ${esc(w.rarity)}`:''}</option>`).join('')}</optgroup>`
  ).join('');
}
function selectedPlannerWeapon(index){
  const cards=[...document.querySelectorAll('.weapon-card')];
  const name=norm(cards[index]?.querySelector('.item-name')?.textContent||'');
  if(!name||name.toLowerCase()==='empty')return null;
  return weapons.find(w=>norm(w.name).toLowerCase()===name.toLowerCase())||null;
}
function defaultPair(){
  const primary=selectedPlannerWeapon(0);
  const secondary=selectedPlannerWeapon(1);
  return [primary?.id||weapons[0]?.id,secondary?.id||weapons.find(w=>String(w.id)!==String(primary?.id||weapons[0]?.id))?.id||weapons[0]?.id];
}

function ensureUi(){
  const actions=document.querySelector('.topbar .actions');
  if(actions&&!document.getElementById('compareWeaponsBtn')){
    const btn=document.createElement('button');
    btn.id='compareWeaponsBtn';
    btn.type='button';
    btn.className='ds-compare-open';
    btn.textContent='Compare Weapons';
    btn.title='Compare indexed weapon records side by side';
    actions.prepend(btn);
  }

  if(document.getElementById('weaponCompareDialog'))return;
  const dialog=document.createElement('dialog');
  dialog.id='weaponCompareDialog';
  dialog.className='ds-weapon-compare-dialog';
  dialog.innerHTML=`
    <div class="dialog-head ds-compare-head">
      <div><small>DEAD SIGNAL // INDEXED DATA</small><h2>Weapon Compare</h2></div>
      <button type="button" data-compare-close aria-label="Close">×</button>
    </div>
    <div class="ds-compare-notice">
      <strong>RAW INDEXED ITEM STATS</strong>
      <span>This compares the player-facing weapon records currently indexed by Dead Signal. Tier, Blueprint Stars, Calibration, attachments and derived DPS are not applied here.</span>
    </div>
    <div class="ds-compare-selectors">
      <label><span>WEAPON A</span><select data-compare-a></select></label>
      <button type="button" class="ds-compare-swap" data-compare-swap aria-label="Swap compared weapons">⇄</button>
      <label><span>WEAPON B</span><select data-compare-b></select></label>
    </div>
    <div class="ds-compare-body" data-compare-body></div>`;
  document.body.append(dialog);
}

function itemHeader(item,label){
  return `<div class="ds-compare-item rarity-${rarityClass(item)}">
    <small>${esc(label)}</small>
    <strong>${esc(item?.name||'—')}</strong>
    <span>${esc([item?.type,item?.rarity].filter(Boolean).join(' · '))}</span>
  </div>`;
}
function statValue(item,key,suffix){
  const v=item?.stats?.[key];
  return numeric(v)?`${fmt(v)}${suffix}`:'—';
}
function deltaValue(a,b,key,suffix){
  const av=a?.stats?.[key],bv=b?.stats?.[key];
  if(!numeric(av)||!numeric(bv))return '—';
  const d=Number(bv)-Number(av);
  if(Math.abs(d)<1e-9)return '0';
  return `${sign(d)}${suffix}`;
}
function render(){
  const dialog=document.getElementById('weaponCompareDialog');
  const aSel=dialog?.querySelector('[data-compare-a]');
  const bSel=dialog?.querySelector('[data-compare-b]');
  const body=dialog?.querySelector('[data-compare-body]');
  if(!aSel||!bSel||!body)return;

  const a=byId.get(String(aSel.value));
  const b=byId.get(String(bSel.value));
  if(!a||!b){body.innerHTML='<div class="empty">Choose two indexed weapons to compare.</div>';return;}

  const rows=STAT_ROWS.map(([key,label,suffix])=>{
    const av=a?.stats?.[key],bv=b?.stats?.[key];
    if(!numeric(av)&&!numeric(bv))return'';
    return `<div class="ds-compare-row">
      <span>${esc(label)}</span>
      <b>${esc(statValue(a,key,suffix))}</b>
      <em title="Weapon B minus Weapon A">${esc(deltaValue(a,b,key,suffix))}</em>
      <b>${esc(statValue(b,key,suffix))}</b>
    </div>`;
  }).join('');

  const ae=effectText(a),be=effectText(b);
  body.innerHTML=`
    <div class="ds-compare-grid-head">
      ${itemHeader(a,'WEAPON A')}
      <div class="ds-compare-delta-title"><small>DELTA</small><span>B − A</span></div>
      ${itemHeader(b,'WEAPON B')}
    </div>
    <div class="ds-compare-stat-list">${rows||'<div class="empty">No shared indexed numeric stats are available for these records.</div>'}</div>
    <div class="ds-compare-effects">
      <article><small>WEAPON A EFFECT</small><p>${esc(ae||'Detailed weapon effect not indexed for this record yet.')}</p></article>
      <article><small>WEAPON B EFFECT</small><p>${esc(be||'Detailed weapon effect not indexed for this record yet.')}</p></article>
    </div>
    <p class="ds-compare-footnote">Delta is arithmetic only, not a winner score. Higher is not automatically better for every stat.</p>`;
}
function open(){
  ensureUi();
  const dialog=document.getElementById('weaponCompareDialog');
  const aSel=dialog.querySelector('[data-compare-a]');
  const bSel=dialog.querySelector('[data-compare-b]');
  const [a,b]=defaultPair();
  aSel.innerHTML=optionHtml(a);
  bSel.innerHTML=optionHtml(b);
  render();
  dialog.showModal();
}
function init(){
  ensureUi();
  document.addEventListener('click',e=>{
    if(e.target.closest('#compareWeaponsBtn')){open();return;}
    if(e.target.closest('[data-compare-close]')){document.getElementById('weaponCompareDialog')?.close();return;}
    if(e.target.closest('[data-compare-swap]')){
      const d=document.getElementById('weaponCompareDialog'),a=d?.querySelector('[data-compare-a]'),b=d?.querySelector('[data-compare-b]');
      if(a&&b){const v=a.value;a.value=b.value;b.value=v;render();}
    }
  });
  document.addEventListener('change',e=>{
    if(e.target.matches?.('[data-compare-a],[data-compare-b]'))render();
  });
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
