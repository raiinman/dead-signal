(()=>{
'use strict';

const D=window.DS_COMMUNITY||{};
const armorImageMap=window.DS_ARMOR_IMAGE_MAP||{};
const pools=['weapons','armor','mods','attachments','deviations','cradles','consumables','ammo','calibrations','armorSets'];
const byId=new Map();
const byName=new Map();

for(const key of pools){
  for(const item of (D[key]||[])){
    if(item?.id&&!byId.has(item.id))byId.set(item.id,item);
    if(item?.name&&!byName.has(item.name))byName.set(item.name,item);
  }
}

const clean=v=>String(v||'').trim();

function normalizeAsset(raw){
  const v=clean(raw).replace(/\\/g,'/');
  if(!v)return '';
  if(/^(https?:\/\/|data:image\/)/i.test(v))return v;
  if(v.startsWith('/build-planner/'))return v;
  if(v.startsWith('/assets/'))return '/build-planner'+v;
  if(v.startsWith('assets/'))return '/build-planner/'+v;
  if(v.startsWith('./assets/'))return '/build-planner/'+v.slice(2);
  const marker='reference-images/';
  const pos=v.toLowerCase().indexOf(marker);
  if(pos>=0)return '/build-planner/assets/'+v.slice(pos);
  return '';
}

function imageUrl(item){
  const raw=item?.imageUrl||item?.imageAsset||item?.image||item?.iconUrl||item?.icon||item?.assetPath||item?.imagePath||item?.media?.image||item?.media?.icon||'';
  const direct=normalizeAsset(raw);
  if(direct)return direct;
  return normalizeAsset(armorImageMap[item?.id]||'');
}

function codeFor(item,fallback='DS'){
  const source=clean(item?.type||item?.slot||item?.category||fallback);
  const map={'Assault Rifle':'AR','Submachine Gun':'SMG','Light Machine Gun':'LMG','Sniper Rifle':'SR','Shotgun':'SG','Pistol':'HG','Crossbow':'XBOW','Melee':'MELEE','Helmet':'HEAD','Mask':'MASK','Top':'TOP','Gloves':'HANDS','Pants':'LEGS','Shoes':'FEET'};
  return map[source]||source.replace(/[^a-z0-9]/gi,'').slice(0,6).toUpperCase()||'DS';
}

function mediaNode(item,size='picker',fallback='DS'){
  const src=imageUrl(item);
  const box=document.createElement('div');
  box.className=`item-media item-media-${size} ${src?'has-image':'no-image'}`;
  if(src){
    const img=document.createElement('img');
    img.src=src;
    img.alt=item?.name||fallback;
    img.loading='lazy';
    img.decoding='async';
    img.addEventListener('load',()=>box.classList.add('media-loaded'));
    img.addEventListener('error',()=>{img.hidden=true;box.classList.add('media-error')});
    box.append(img);
  }
  const fb=document.createElement('div');
  fb.className='media-fallback';
  fb.innerHTML=`<b>${codeFor(item,fallback)}</b><small>${src?'IMAGE UNAVAILABLE':'NO IMAGE'}</small>`;
  box.append(fb);
  return box;
}

function itemFromCard(card){
  const name=clean(card.querySelector('.item-name')?.textContent||card.querySelector('strong')?.textContent);
  return name&&name!=='Empty'?byName.get(name):null;
}

function enhancePicker(card){
  if(card.dataset.dsImageEnhanced==='1')return;
  const pick=card.querySelector(':scope > .pick[data-select]');
  if(!pick)return;
  const item=byId.get(pick.dataset.select)||itemFromCard(card);
  const layout=document.createElement('div');
  layout.className='pick-layout';
  const copy=document.createElement('div');
  copy.className='pick-copy';
  while(pick.firstChild)copy.append(pick.firstChild);
  layout.append(mediaNode(item,'picker','Item'),copy);
  pick.append(layout);
  card.dataset.dsImageEnhanced='1';
}

function enhanceSelected(card,kind){
  if(card.dataset.dsImageEnhanced==='1')return;
  const head=card.querySelector(':scope > .slot-head');
  if(!head)return;
  const item=itemFromCard(card);
  const wrapper=document.createElement('div');
  wrapper.className=`selected-item-head ${kind}-selected-head`;
  const copy=document.createElement('div');
  copy.className='selected-item-copy';
  head.replaceWith(wrapper);
  wrapper.append(mediaNode(item,'selected',kind),copy);
  copy.append(head);
  card.dataset.dsImageEnhanced='1';
}

function enhanceSystem(card){
  if(card.dataset.dsImageEnhanced==='1')return;
  const slot=card.querySelector('.slot-label');
  const name=card.querySelector('.item-name');
  if(!slot||!name)return;
  const item=itemFromCard(card);
  const head=document.createElement('div');
  head.className='system-card-head';
  const copy=document.createElement('div');
  slot.before(head);
  head.append(mediaNode(item,'system',clean(slot.textContent)||'System'),copy);
  copy.append(slot,name);
  const badge=card.querySelector('.rarity-badge');
  if(badge)copy.append(badge);
  card.dataset.dsImageEnhanced='1';
}

function enhanceMod(group){
  if(group.dataset.dsImageEnhanced==='1')return;
  const first=group.querySelector('[data-select]');
  const head=group.querySelector('.mod-group-head');
  if(!first||!head)return;
  const item=byId.get(first.dataset.select);
  head.prepend(mediaNode(item,'mod','Mod'));
  group.dataset.dsImageEnhanced='1';
}

function run(){
  document.querySelectorAll('.pick-card').forEach(enhancePicker);
  document.querySelectorAll('.weapon-card').forEach(x=>enhanceSelected(x,'weapon'));
  document.querySelectorAll('.gear-card').forEach(x=>enhanceSelected(x,'armor'));
  document.querySelectorAll('.system-card').forEach(enhanceSystem);
  document.querySelectorAll('.mod-group').forEach(enhanceMod);
}

let queued=false;
function queue(){
  if(queued)return;
  queued=true;
  requestAnimationFrame(()=>{queued=false;run()});
}

new MutationObserver(queue).observe(document.body,{childList:true,subtree:true});
run();
setTimeout(run,50);
setTimeout(run,250);
})();
