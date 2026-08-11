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

const STAT_ROWS=[['damage','DMG',''],['rpm','RPM',''],['magazine','MAG',''],['reload','RELOAD','s'],['critRate','CRIT RATE','%'],['critDamage','CRIT DMG','%'],['weakspot','WEAKSPOT','%'],['range','RANGE',''],['effectiveRange','EFFECTIVE',''],['mobility','MOBILITY',''],['pellets','PELLETS','']];

function rarityClass(item){const v=String(item?.rarity||'').toLowerCase();if(/legendary|gold/.test(v))return'legendary';if(/epic|purple/.test(v))return'epic';if(/rare|blue/.test(v))return'rare';if(/common|green|uncommon/.test(v))return'common';return'normal';}
function effectText(x){if(!x)return'';if(x.feature)return norm(x.feature);if(x.effect)return norm(x.effect);if(x.description)return norm(x.description);if(Array.isArray(x.effects))return x.effects.filter(Boolean).join(' · ');return'';}
function imageUrl(item){
  const raw=item?.imageUrl||item?.imageAsset||item?.image||item?.iconUrl||item?.icon||item?.assetPath||item?.imagePath||item?.media?.image||item?.media?.icon||'';
  const v=String(raw||'').trim().replace(/\\/g,'/');if(!v)return'';
  if(/^(https?:\/\/|data:image\/)/i.test(v))return v;
  if(v.startsWith('/build-planner/'))return v;
  if(v.startsWith('/assets/'))return '/build-planner'+v;
  if(v.startsWith('assets/'))return '/build-planner/'+v;
  if(v.startsWith('./assets/'))return '/build-planner/'+v.slice(2);
  const marker='reference-images/',pos=v.toLowerCase().indexOf(marker);
  return pos>=0?'/build-planner/assets/'+v.slice(pos):'';
}
function searchable(w){return norm(`${w.name} ${w.type||''} ${w.rarity||''} ${effectText(w)}`).toLowerCase();}
function filteredWeapons(query){const q=norm(query).toLowerCase();return q?weapons.filter(w=>searchable(w).includes(q)):weapons.slice();}
function optionHtml(items,selected){
  const groups=new Map();for(const w of items){const key=norm(w.type)||'Other';if(!groups.has(key))groups.set(key,[]);groups.get(key).push(w);}
  return [...groups.entries()].sort((a,b)=>a[0].localeCompare(b[0])).map(([type,xs])=>`<optgroup label="${esc(type)}">${xs.sort((a,b)=>a.name.localeCompare(b.name)).map(w=>`<option value="${esc(w.id)}" ${String(w.id)===String(selected)?'selected':''}>${esc(w.name)}${w.rarity?` — ${esc(w.rarity)}`:''}</option>`).join('')}</optgroup>`).join('');
}
function populateSide(side,preferred){
  const d=document.getElementById('weaponCompareDialog');if(!d)return;
  const search=d.querySelector(`[data-compare-search-${side}]`),sel=d.querySelector(`[data-compare-${side}]`),count=d.querySelector(`[data-compare-count-${side}]`);if(!sel)return;
  const items=filteredWeapons(search?.value||''),wanted=String(preferred??sel.value??'');
  const chosen=items.some(w=>String(w.id)===wanted)?wanted:String(items[0]?.id||'');
  sel.innerHTML=items.length?optionHtml(items,chosen):'<option value="">No matching weapons</option>';
  sel.disabled=!items.length;if(chosen)sel.value=chosen;if(count)count.textContent=`${items.length}/${weapons.length} indexed`;
}
function selectedPlannerWeapon(index){const cards=[...document.querySelectorAll('.weapon-card')],name=norm(cards[index]?.querySelector('.item-name')?.textContent||'');if(!name||name.toLowerCase()==='empty')return null;return weapons.find(w=>norm(w.name).toLowerCase()===name.toLowerCase())||null;}
function defaultPair(){const primary=selectedPlannerWeapon(0),secondary=selectedPlannerWeapon(1);return[primary?.id||weapons[0]?.id,secondary?.id||weapons.find(w=>String(w.id)!==String(primary?.id||weapons[0]?.id))?.id||weapons[0]?.id];}

function ensureUi(){
  const actions=document.querySelector('.topbar .actions');if(actions&&!document.getElementById('compareWeaponsBtn')){const btn=document.createElement('button');btn.id='compareWeaponsBtn';btn.type='button';btn.className='ds-compare-open';btn.textContent='Compare Weapons';btn.title='Compare indexed weapon records side by side';actions.prepend(btn);}
  if(document.getElementById('weaponCompareDialog'))return;
  const dialog=document.createElement('dialog');dialog.id='weaponCompareDialog';dialog.className='ds-weapon-compare-dialog';dialog.innerHTML=`
    <div class="dialog-head ds-compare-head"><div><small>DEAD SIGNAL // INDEXED DATA</small><h2>Weapon Compare</h2></div><button type="button" data-compare-close aria-label="Close">×</button></div>
    <div class="ds-compare-notice"><strong>RAW INDEXED ITEM STATS</strong><span>This compares player-facing weapon records currently indexed by Dead Signal. Tier, Blueprint Stars, Calibration, attachments and derived DPS are not applied here.</span></div>
    <div class="ds-compare-selectors">
      <label><span>WEAPON A</span><input type="search" data-compare-search-a placeholder="Search name, type, rarity, effect…" autocomplete="off"><small data-compare-count-a></small><select data-compare-a aria-label="Weapon A"></select></label>
      <button type="button" class="ds-compare-swap" data-compare-swap aria-label="Swap compared weapons">⇄</button>
      <label><span>WEAPON B</span><input type="search" data-compare-search-b placeholder="Search name, type, rarity, effect…" autocomplete="off"><small data-compare-count-b></small><select data-compare-b aria-label="Weapon B"></select></label>
    </div><div class="ds-compare-body" data-compare-body></div>`;document.body.append(dialog);
}
function itemHeader(item,label){const src=imageUrl(item);return `<div class="ds-compare-item rarity-${rarityClass(item)}">${src?`<img class="ds-compare-image" src="${esc(src)}" alt="${esc(item?.name||label)}" loading="lazy" decoding="async">`:''}<div><small>${esc(label)}</small><strong>${esc(item?.name||'—')}</strong><span>${esc([item?.type,item?.rarity].filter(Boolean).join(' · '))}</span></div></div>`;}
function statValue(item,key,suffix){const v=item?.stats?.[key];return numeric(v)?`${fmt(v)}${suffix}`:'—';}
function deltaValue(a,b,key,suffix){const av=a?.stats?.[key],bv=b?.stats?.[key];if(!numeric(av)||!numeric(bv))return'—';const d=Number(bv)-Number(av);if(Math.abs(d)<1e-9)return'0';return`${sign(d)}${suffix}`;}
function render(){
  const d=document.getElementById('weaponCompareDialog'),aSel=d?.querySelector('[data-compare-a]'),bSel=d?.querySelector('[data-compare-b]'),body=d?.querySelector('[data-compare-body]');if(!aSel||!bSel||!body)return;
  const a=byId.get(String(aSel.value)),b=byId.get(String(bSel.value));if(!a||!b){body.innerHTML='<div class="empty">Choose two indexed weapons to compare.</div>';return;}
  const rows=STAT_ROWS.map(([key,label,suffix])=>{const av=a?.stats?.[key],bv=b?.stats?.[key];if(!numeric(av)&&!numeric(bv))return'';return`<div class="ds-compare-row"><span>${esc(label)}</span><b>${esc(statValue(a,key,suffix))}</b><em title="Weapon B minus Weapon A">${esc(deltaValue(a,b,key,suffix))}</em><b>${esc(statValue(b,key,suffix))}</b></div>`;}).join('');
  const ae=effectText(a),be=effectText(b);body.innerHTML=`<div class="ds-compare-grid-head">${itemHeader(a,'WEAPON A')}<div class="ds-compare-delta-title"><small>DELTA</small><span>B − A</span></div>${itemHeader(b,'WEAPON B')}</div><div class="ds-compare-stat-list">${rows||'<div class="empty">No indexed numeric stats are available for these records.</div>'}</div><div class="ds-compare-effects"><article><small>WEAPON A EFFECT</small><p>${esc(ae||'Detailed weapon effect not indexed for this record yet.')}</p></article><article><small>WEAPON B EFFECT</small><p>${esc(be||'Detailed weapon effect not indexed for this record yet.')}</p></article></div><p class="ds-compare-footnote">Delta is arithmetic only, not a winner score. Higher is not automatically better for every stat.</p>`;
}
function open(){ensureUi();const d=document.getElementById('weaponCompareDialog'),[a,b]=defaultPair();d.querySelector('[data-compare-search-a]').value='';d.querySelector('[data-compare-search-b]').value='';populateSide('a',a);populateSide('b',b);render();d.showModal();}
function init(){ensureUi();document.addEventListener('click',e=>{if(e.target.closest('#compareWeaponsBtn')){open();return}if(e.target.closest('[data-compare-close]')){document.getElementById('weaponCompareDialog')?.close();return}if(e.target.closest('[data-compare-swap]')){const d=document.getElementById('weaponCompareDialog'),a=d?.querySelector('[data-compare-a]'),b=d?.querySelector('[data-compare-b]');if(a&&b){const v=a.value;a.value=b.value;b.value=v;render();}}});document.addEventListener('change',e=>{if(e.target.matches?.('[data-compare-a],[data-compare-b]'))render();});document.addEventListener('input',e=>{if(e.target.matches?.('[data-compare-search-a]')){populateSide('a');render();}if(e.target.matches?.('[data-compare-search-b]')){populateSide('b');render();}});}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
