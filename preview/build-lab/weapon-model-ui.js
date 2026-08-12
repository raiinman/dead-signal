(()=>{
'use strict';

const WEAPONS=(window.DS_WEAPON_MATH?.weapons||[]).map(record=>({
  n:record.name,
  id:record.canonical_id,
  t:(record.tier_star_matrix||[]).map(row=>[Number(row.gear_tier),Number(row.tier_base_attack_at_1_star)]),
  s:(record.tier_star_matrix?.at(-1)?.blueprint_star_values||[]).map(row=>[Number(row.blueprint_stars),Number(row.preset_attack_ratio),Number(row.base_attack)])
}));
const CAL_RANGES=DATA.calibrationRanges||{Rare:[18,25],Epic:[26,33],Legendary:[34,50]};
const weaponByName=new Map(WEAPONS.map(x=>[String(x.n||'').trim().toLowerCase(),x]));

const STATE_KEY='dead-signal-weapon-model-v1';
let state=readState();
let queued=false;

function readState(){try{return JSON.parse(localStorage.getItem(STATE_KEY)||'{}')||{};}catch(_){return {};}}
function saveState(){try{localStorage.setItem(STATE_KEY,JSON.stringify(state));}catch(_){} }
function norm(v){return String(v??'').replace(/\s+/g,' ').trim();}
function mode(){
  if(window.DSBuildMode&&typeof window.DSBuildMode.get==='function')return window.DSBuildMode.get();
  try{return localStorage.getItem('dead-signal-build-mode')==='god'?'god':'gear';}catch(_){return 'gear';}
}
function romanTier(s){
  const t=norm(s).toUpperCase();
  const m=t.match(/(?:TIER\s*)?(IV|V|III|II|I)\b/);
  if(m)return({I:1,II:2,III:3,IV:4,V:5})[m[1]];
  const n=t.match(/(?:TIER\s*)?([1-5])\b/);
  return n?Number(n[1]):null;
}
function starValue(s){
  const t=norm(s);
  let m=t.match(/([1-6])\s*★/);if(m)return Number(m[1]);
  m=t.match(/(?:BLUEPRINT\s*)?STAR(?:S)?\s*[:\-]?\s*([1-6])/i);return m?Number(m[1]):null;
}
function findNativeSelect(card,kind){
  const own=new Set(card.querySelectorAll('.ds-weapon-model select'));
  for(const sel of card.querySelectorAll('select')){
    if(own.has(sel))continue;
    const texts=[...sel.options].map(o=>norm(o.textContent||o.value));
    const ctx=norm(sel.closest('label,.progression,.profile-select,.mini-select')?.textContent||sel.parentElement?.textContent||'');
    const tierHits=texts.filter(x=>romanTier(x)!=null).length;
    const starHits=texts.filter(x=>starValue(x)!=null).length;
    if(kind==='tier'&&(tierHits>=2||(/\btier\b/i.test(ctx)&&tierHits>=1)))return sel;
    if(kind==='star'&&(starHits>=2||(/\bstar/i.test(ctx)&&starHits>=1)))return sel;
  }
  return null;
}
function slotKey(card,w){
  const cards=[...document.querySelectorAll('.weapon-card')];
  return `${Math.max(0,cards.indexOf(card))}:${w.id||w.n}`;
}
function selectedTier(card,w){
  const sel=findNativeSelect(card,'tier');
  let v=sel?romanTier(sel.selectedOptions?.[0]?.textContent||sel.value):null;
  if(!v)v=romanTier(card.innerText);
  const key=slotKey(card,w);
  if(!v)v=Number(state[key]?.tier)||null;
  const allowed=w.t.map(x=>Number(x[0])).filter(Boolean);
  if(!allowed.includes(v))v=Math.max(...allowed);
  return v;
}
function selectedStar(card,w){
  const sel=findNativeSelect(card,'star');
  let v=sel?starValue(sel.selectedOptions?.[0]?.textContent||sel.value):null;
  if(!v)v=starValue(card.innerText);
  const key=slotKey(card,w);
  if(!v)v=Number(state[key]?.star)||null;
  const allowed=w.s.map(x=>Number(x[0])).filter(Boolean);
  if(!allowed.includes(v))v=Math.max(...allowed);
  return v;
}
function exactTextNodes(root){
  const out=[];const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let n;
  while((n=walker.nextNode())){const t=norm(n.nodeValue);if(t)out.push({t,parent:n.parentElement});}
  return out;
}
function calibrationFromCard(card,key){
  const proxy=card.querySelector('.ds-wm-cal-picker');
  const explicit=norm(proxy?.dataset?.calibrationRarity||'');
  if(explicit&&CAL_RANGES[explicit]){
    const r=CAL_RANGES[explicit];
    return{id:explicit,q:explicit,min:Number(r[0]),max:Number(r[1]),detected:true};
  }

  const proxyName=norm(proxy?.dataset?.calibrationName||proxy?.querySelector('.ds-wm-cal-picker-button strong')?.textContent||'');
  const selectedProxy=proxyName&&!/^Select Calibration Blueprint$/i.test(proxyName);

  const nodes=exactTextNodes(card).filter(x=>/Calibration Blueprint\s*-/i.test(x.t));
  for(const {parent} of nodes){
    const contexts=[];let box=parent;
    for(let i=0;i<3&&box&&box!==card;i++,box=box.parentElement)contexts.push(norm(box.textContent));
    for(const context of contexts){
      for(const q of ['Legendary','Epic','Rare']){
        if(new RegExp(`\\b${q}\\b`,'i').test(context)){
          const r=CAL_RANGES[q];if(r)return{id:q,q,min:Number(r[0]),max:Number(r[1]),detected:true};
        }
      }
    }
  }

  if(selectedProxy)return{id:'unknown',q:null,min:null,max:null,detected:false};

  const saved=state[key]?.calQuality;
  if(saved&&CAL_RANGES[saved]){const r=CAL_RANGES[saved];return{id:saved,q:saved,min:Number(r[0]),max:Number(r[1]),detected:false};}
  return nodes.length?{id:'unknown',q:null,min:null,max:null,detected:false}:null;
}
function weaponName(card){const name=norm(card.querySelector('.item-name')?.textContent||'');return name&&name.toLowerCase()!=='empty'?name:'';}
function options(values,current,labeler){return values.map(v=>`<option value="${v}" ${v===current?'selected':''}>${labeler(v)}</option>`).join('');}
function currentRoll(key,cal){const v=Number(state[key]?.calRoll);return Number.isFinite(v)&&v>=cal.min&&v<=cal.max?v:null;}
function storeChoice(key,patch){state[key]={...(state[key]||{}),...patch};saveState();}
function fmt(v,d=1){return Number.isFinite(Number(v))?Number(v).toFixed(d):'—';}
function signatureFor(w,tier,star,cal,buildMode,roll){return[w.id,tier,star,cal?.id||'none',buildMode,roll==null?'unset':Number(roll).toFixed(1)].join('|');}

function renderCard(card){
  const name=weaponName(card);
  if(!name){card.querySelector('.ds-weapon-model')?.remove();return;}
  const w=weaponByName.get(name.toLowerCase());if(!w)return;

  const tier=selectedTier(card,w),star=selectedStar(card,w),key=slotKey(card,w);
  storeChoice(key,{tier,star});
  const cal=calibrationFromCard(card,key),buildMode=mode();
  const roll=cal&&cal.q?(buildMode==='god'?Number(cal.max):currentRoll(key,cal)):null;
  const signature=signatureFor(w,tier,star,cal,buildMode,roll);

  let panel=card.querySelector('.ds-weapon-model');
  if(panel&&panel.dataset.signature===signature)return;
  if(!panel){panel=document.createElement('section');panel.className='ds-weapon-model';card.append(panel);}

  const nativeTier=findNativeSelect(card,'tier'),nativeStar=findNativeSelect(card,'star');
  const tierControl=nativeTier?'':`<label><span>Gear Tier</span><select data-wm-tier>${options(w.t.map(x=>Number(x[0])),tier,v=>['','I','II','III','IV','V'][v])}</select></label>`;
  const starControl=nativeStar?'':`<label><span>Blueprint Stars</span><select data-wm-star>${options(w.s.map(x=>Number(x[0])),star,v=>`${v}★`)}</select></label>`;

  let calHtml='';
  if(cal&&cal.q){
    if(buildMode==='god'){
      calHtml=`<section class="ds-wm-cal ds-cal-roll-card ds-wm-god">
        <div class="ds-cal-roll-head"><span class="ds-cal-step">1</span><div><small>WEAPON DMG ROLL</small><strong>${cal.q} Calibration</strong></div><em>${fmt(cal.min)}–${fmt(cal.max)}%</em></div>
        <div class="ds-cal-locked-value"><small>GOD ROLL VALUE</small><strong>${fmt(cal.max)}%</strong></div>
      </section>`;
    }else{
      const has=roll!=null;
      calHtml=`<section class="ds-wm-cal ds-cal-roll-card">
        <div class="ds-cal-roll-head"><span class="ds-cal-step">1</span><div><small>WEAPON DMG ROLL</small><strong>${cal.q} Calibration</strong></div><em>${fmt(cal.min)}–${fmt(cal.max)}%</em></div>
        <label class="ds-cal-number-field"><span>Exact Weapon DMG roll</span><div><input data-wm-roll-number type="number" min="${cal.min}" max="${cal.max}" step="0.1" value="${has?fmt(roll):''}" placeholder=""><b>%</b></div><small data-wm-roll-status>${has?`Saved roll: ${fmt(roll)}%`:`Enter a value from ${fmt(cal.min)}% to ${fmt(cal.max)}%`}</small></label>
      </section>`;
    }
  }else if(cal){
    calHtml=`<section class="ds-wm-cal ds-cal-roll-card"><div class="ds-cal-roll-head"><span class="ds-cal-step">1</span><div><small>WEAPON DMG ROLL</small><strong>Calibration rarity unavailable</strong></div></div><p>Re-select this Calibration Blueprint so Dead Signal can bind its exact rarity.</p></section>`;
  }else{
    calHtml='<section class="ds-wm-cal ds-cal-roll-card ds-wm-empty"><div class="ds-cal-roll-head"><span class="ds-cal-step">1</span><div><small>WEAPON DMG ROLL</small><strong>Select a Calibration Blueprint first</strong></div></div></section>';
  }

  panel.innerHTML=`${(tierControl||starControl)?`<div class="ds-wm-controls">${tierControl}${starControl}</div>`:''}${calHtml}`;
  panel.dataset.signature=signature;

  panel.querySelector('[data-wm-tier]')?.addEventListener('change',e=>{storeChoice(key,{tier:Number(e.target.value)});panel.dataset.signature='';renderCard(card);});
  panel.querySelector('[data-wm-star]')?.addEventListener('change',e=>{storeChoice(key,{star:Number(e.target.value)});panel.dataset.signature='';renderCard(card);});

  const number=panel.querySelector('[data-wm-roll-number]'),status=panel.querySelector('[data-wm-roll-status]');
  if(number&&cal){
    const saveValid=v=>{
      v=Math.round(Number(v)*10)/10;
      if(!Number.isFinite(v)||v<cal.min||v>cal.max)return false;
      storeChoice(key,{calRoll:v,calId:cal.id,calQuality:cal.q});
      number.value=fmt(v);
      if(status)status.textContent=`Saved roll: ${fmt(v)}%`;
      panel.dataset.signature=signatureFor(w,tier,star,cal,buildMode,v);
      return true;
    };
    number.addEventListener('input',()=>{
      if(number.value===''){if(status)status.textContent=`Enter a value from ${fmt(cal.min)}% to ${fmt(cal.max)}%`;return;}
      const v=Number(number.value);
      if(Number.isFinite(v)&&v>=cal.min&&v<=cal.max){saveValid(v);}
      else if(status)status.textContent=`Allowed range: ${fmt(cal.min)}%–${fmt(cal.max)}%`;
    });
    number.addEventListener('change',()=>{
      if(number.value===''){storeChoice(key,{calRoll:null,calId:cal.id,calQuality:cal.q});panel.dataset.signature='';renderCard(card);return;}
      let v=Number(number.value);if(!Number.isFinite(v))return;
      v=Math.round(Math.min(cal.max,Math.max(cal.min,v))*10)/10;saveValid(v);
    });
  }
}

function run(){document.querySelectorAll('.weapon-card').forEach(renderCard);}
function resetState(){
  state={};
  try{localStorage.removeItem(STATE_KEY);}catch(_){}
  document.querySelectorAll('.ds-weapon-model').forEach(panel=>{panel.dataset.signature='';});
  run();
}
function queue(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;run();});}
window.DSWeaponModelUI={...(window.DSWeaponModelUI||{}),reset:resetState};
new MutationObserver(queue).observe(document.body,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['data-calibration-rarity','data-calibration-name']});
document.addEventListener('change',e=>{if(e.target.closest?.('.weapon-card'))setTimeout(run,0);});
window.addEventListener('dead-signal:build-mode-change',run);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run,{once:true});else run();
setTimeout(run,120);setTimeout(run,500);
})();
