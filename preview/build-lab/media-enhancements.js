(()=>{
'use strict';
const D=window.DS_COMMUNITY||{};
const pools=['weapons','armor','mods','attachments','deviations','cradles','consumables','ammo','calibrations','armorSets'];
const byId=new Map();
const byName=new Map();
for(const key of pools){for(const x of (D[key]||[])){if(x?.id&&!byId.has(x.id))byId.set(x.id,x);if(x?.name&&!byName.has(x.name))byName.set(x.name,x)}}
const clean=s=>String(s||'').trim();
function normalizeMediaPath(raw){
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
 return /^(\/|\.\.?\/)/.test(v)?v:'';
}
function mediaUrl(x){
 const raw=x?.imageUrl||x?.imageAsset||x?.image||x?.iconUrl||x?.icon||x?.assetPath||x?.imagePath||x?.media?.image||x?.media?.icon||'';
 return normalizeMediaPath(raw);
}
function codeFor(x,fallback='ITEM'){
 const source=clean(x?.type||x?.slot||x?.category||fallback);
 const map={'Assault Rifle':'AR','Submachine Gun':'SMG','Light Machine Gun':'LMG','Sniper Rifle':'SR','Shotgun':'SG','Pistol':'HG','Crossbow':'XBOW','Melee':'MELEE','Helmet':'HEAD','Mask':'MASK','Top':'TOP','Gloves':'HANDS','Pants':'LEGS','Shoes':'FEET'};
 if(map[source])return map[source];
 const bits=source.replace(/[^a-z0-9 ]/gi,' ').split(/\s+/).filter(Boolean);
 return ((bits.length>1?bits.map(v=>v[0]).join(''):source.slice(0,5))||'DS').toUpperCase().slice(0,5)
}
function mediaNode(x,kind,size){
 const src=mediaUrl(x);
 const el=document.createElement('div');el.className=`item-media item-media-${size} ${src?'has-image':'no-image'}`;el.dataset.mediaKind=kind;
 if(src){const img=document.createElement('img');img.src=src;img.alt=x?.name||kind;img.loading='lazy';img.decoding='async';img.addEventListener('load',()=>el.classList.add('media-loaded'));img.addEventListener('error',()=>{img.hidden=true;el.classList.add('media-error')});el.append(img)}
 const fb=document.createElement('div');fb.className='media-fallback';fb.innerHTML=`<b>${codeFor(x,kind)}</b><small>${src?'IMAGE UNAVAILABLE':'IMAGE SLOT READY'}</small>`;el.append(fb);return el
}
function findByCard(card){const name=clean(card.querySelector('.item-name')?.textContent);return name&&name!=='Empty'?byName.get(name):null}
function enhanceSelected(card,kind){if(card.dataset.mediaEnhanced)return;const head=card.querySelector(':scope > .slot-head');if(!head)return;const item=findByCard(card);const wrapper=document.createElement('div');wrapper.className=`selected-item-head ${kind}-selected-head`;const copy=document.createElement('div');copy.className='selected-item-copy';head.replaceWith(wrapper);wrapper.append(mediaNode(item||{type:clean(head.querySelector('.slot-label')?.textContent)},kind,'selected'),copy);copy.append(head);card.dataset.mediaEnhanced='1'}
function enhanceSystem(card){if(card.dataset.mediaEnhanced)return;const label=clean(card.querySelector('.slot-label')?.textContent);const item=findByCard(card);const slot=card.querySelector('.slot-label');const name=card.querySelector('.item-name');if(!slot||!name)return;const head=document.createElement('div');head.className='system-card-head';const copy=document.createElement('div');slot.before(head);head.append(mediaNode(item||{category:label},label.toLowerCase(),'system'),copy);copy.append(slot,name);const badge=card.querySelector('.rarity-badge');if(badge)copy.append(badge);card.dataset.mediaEnhanced='1'}
function enhancePick(card){if(card.dataset.mediaEnhanced)return;const pick=card.querySelector(':scope > .pick[data-select]');if(!pick)return;const item=byId.get(pick.dataset.select)||byName.get(clean(pick.querySelector('strong')?.textContent));const layout=document.createElement('div');layout.className='pick-layout';const copy=document.createElement('div');copy.className='pick-copy';while(pick.firstChild)copy.append(pick.firstChild);pick.append(layout);layout.append(mediaNode(item||{},'picker','picker'),copy);card.dataset.mediaEnhanced='1'}
function enhanceMod(group){if(group.dataset.mediaEnhanced)return;const first=group.querySelector('[data-select]');const item=first?byId.get(first.dataset.select):null;const head=group.querySelector('.mod-group-head');if(!head)return;head.prepend(mediaNode(item||{},'mod','mod'));group.dataset.mediaEnhanced='1'}
function run(){document.querySelectorAll('.weapon-card').forEach(x=>enhanceSelected(x,'weapon'));document.querySelectorAll('.gear-card').forEach(x=>enhanceSelected(x,'armor'));document.querySelectorAll('.system-card').forEach(enhanceSystem);document.querySelectorAll('.pick-card').forEach(enhancePick);document.querySelectorAll('.mod-group').forEach(enhanceMod)}
let queued=false;const queue=()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;run()})};
new MutationObserver(queue).observe(document.body,{childList:true,subtree:true});
queue();
})();
