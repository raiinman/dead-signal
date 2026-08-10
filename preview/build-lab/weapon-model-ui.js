(()=>{
'use strict';

const DATA=window.DS_WEAPON_MODEL_DATA||{};
const RECORDS=Array.isArray(DATA.records)?DATA.records:(Array.isArray(window.DS_WEAPON_MODEL_RECORDS)?window.DS_WEAPON_MODEL_RECORDS:[]);
const WEAPONS=Array.isArray(DATA.weapons)?DATA.weapons:RECORDS.map((r,idx)=>({n:r[0],id:idx+1,t:(r[1]||[]).map((v,i)=>[i+1,v]).filter(x=>x[1]!=null),s:(r[2]||[]).map((v,i)=>[i+1,v,0]),b:r[3]||[],a:r[4]||[]}));
const CAL_RANGES=DATA.calibrationRanges||{Rare:[18,25],Epic:[26,33],Legendary:[34,50]};
const weaponByName=new Map(WEAPONS.map(x=>[String(x.n||'').trim().toLowerCase(),x]));

const STATE_KEY='dead-signal-weapon-model-v1';
let state=readState();
let queued=false;

function readState(){
  try{return JSON.parse(localStorage.getItem(STATE_KEY)||'{}')||{};}catch(_){return {};}
}
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
  let m=t.match(/([1-6])\s*★/); if(m)return Number(m[1]);
  m=t.match(/(?:BLUEPRINT\s*)?STAR(?:S)?\s*[:\-]?\s*([1-6])/i); if(m)return Number(m[1]);
  return null;
}
function findNativeSelect(card,kind){
  const own=new Set(card.querySelectorAll('.ds-weapon-model select'));
  for(const sel of card.querySelectorAll('select')){
    if(own.has(sel))continue;
    const optionTexts=[...sel.options].map(o=>norm(o.textContent||o.value));
    const ctx=norm(sel.closest('label,.progression,.profile-select,.mini-select')?.textContent||sel.parentElement?.textContent||'');
    const tierHits=optionTexts.filter(x=>romanTier(x)!=null).length;
    const starHits=optionTexts.filter(x=>starValue(x)!=null).length;
    if(kind==='tier' && (tierHits>=2||(/\btier\b/i.test(ctx)&&tierHits>=1)))return sel;
    if(kind==='star' && (starHits>=2||(/\bstar/i.test(ctx)&&starHits>=1)))return sel;
  }
  return null;
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
function slotKey(card,w){
  const cards=[...document.querySelectorAll('.weapon-card')];
  const idx=Math.max(0,cards.indexOf(card));
  return `${idx}:${w.id||w.n}`;
}
function exactTextNodes(root){
  const out=[];
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  let n;
  while((n=walker.nextNode())){
    const t=norm(n.nodeValue);
    if(t)out.push({t,node:n,parent:n.parentElement});
  }
  return out;
}
function calibrationFromCard(card,key){
  const nodes=exactTextNodes(card).filter(x=>/Calibration Blueprint\s*-/i.test(x.t));
  if(!nodes.length)return null;
  for(const {parent} of nodes){
    const contexts=[];
    let box=parent;
    for(let i=0;i<3&&box&&box!==card;i++,box=box.parentElement)contexts.push(norm(box.textContent));
    for(const context of contexts){
      for(const q of ['Legendary','Epic','Rare']){
        if(new RegExp(`\\b${q}\\b`,'i').test(context)){
          const r=CAL_RANGES[q];
          if(r)return {id:q,q,min:Number(r[0]),max:Number(r[1]),detected:true};
        }
      }
    }
  }
  const saved=state[key]?.calQuality;
  if(saved&&CAL_RANGES[saved]){
    const r=CAL_RANGES[saved];
    return {id:saved,q:saved,min:Number(r[0]),max:Number(r[1]),detected:false};
  }
  return {id:'unknown',q:null,min:null,max:null,detected:false};
}
function weaponName(card){
  const el=card.querySelector('.item-name');
  const name=norm(el?.textContent||'');
  return name&&name.toLowerCase()!=='empty'?name:'';
}
function tierAttack(w,tier){return Number((w.t.find(x=>Number(x[0])===tier)||[])[1]);}
function starRow(w,star){return w.s.find(x=>Number(x[0])===star)||w.s[0]||[1,1,0];}
function roundHalfEven(x){
  if(!Number.isFinite(x))return null;
  const f=Math.floor(x), frac=x-f;
  if(Math.abs(frac-.5)<1e-10)return f%2===0?f:f+1;
  return Math.round(x);
}
function fmt(v,d=0){return Number.isFinite(Number(v))?Number(v).toFixed(d):'—';}
function stat(label,value,unit=''){
  return `<div class="ds-wm-stat"><small>${label}</small><strong>${value}${unit}</strong></div>`;
}
function baseAttrHtml(w){
  return (w.a||[]).slice(0,4).map(a=>stat(a[0],a[1]||'—')).join('');
}
function options(values,current,labeler){return values.map(v=>`<option value="${v}" ${v===current?'selected':''}>${labeler(v)}</option>`).join('');}
function currentRoll(key,cal){
  const v=Number(state[key]?.calRoll);
  return Number.isFinite(v)&&v>=cal.min&&v<=cal.max?v:null;
}
function storeChoice(key,patch){state[key]={...(state[key]||{}),...patch};saveState();}

function renderCard(card){
  const name=weaponName(card);
  if(!name){card.querySelector('.ds-weapon-model')?.remove();return;}
  const w=weaponByName.get(name.toLowerCase());
  if(!w)return;

  const tier=selectedTier(card,w);
  const star=selectedStar(card,w);
  const tAttack=tierAttack(w,tier);
  const sr=starRow(w,star);
  const ratio=Number(sr[1]??1);
  const intrinsic=Math.trunc(tAttack*ratio);
  const key=slotKey(card,w);
  storeChoice(key,{tier,star});
  const cal=calibrationFromCard(card,key);
  const buildMode=mode();
  const roll=cal&&cal.q?(buildMode==='god'?Number(cal.max):currentRoll(key,cal)):null;
  const rngAttack=cal&&roll!=null?roundHalfEven(intrinsic*(1+roll/100)):null;
  const base=w.b||[];

  let panel=card.querySelector('.ds-weapon-model');
  const signature=[w.id,tier,star,cal?.id||'none',buildMode,roll==null?'unset':roll].join('|');
  if(panel&&panel.dataset.signature===signature)return;
  if(!panel){panel=document.createElement('section');panel.className='ds-weapon-model';card.append(panel);}

  const nativeTier=findNativeSelect(card,'tier');
  const nativeStar=findNativeSelect(card,'star');
  const tierControl=nativeTier?'':`<label><span>Gear Tier</span><select data-wm-tier>${options(w.t.map(x=>Number(x[0])),tier,v=>['','I','II','III','IV','V'][v])}</select></label>`;
  const starControl=nativeStar?'':`<label><span>Blueprint Stars</span><select data-wm-star>${options(w.s.map(x=>Number(x[0])),star,v=>`${v}★`)}</select></label>`;

  let calHtml='';
  if(cal&&cal.q){
    if(buildMode==='god'){
      calHtml=`<div class="ds-wm-cal ds-wm-god"><div><small>CALIBRATION ATTACK RNG</small><strong>${cal.q} // GOD ROLL</strong></div><div class="ds-wm-rollline"><input type="range" min="${cal.min}" max="${cal.max}" step="0.1" value="${cal.max}" disabled><output>${fmt(cal.max,1)}%</output></div><p>Maximum legal roll is being used automatically in God Roll mode.</p></div>`;
    }else{
      const has=roll!=null;
      calHtml=`<div class="ds-wm-cal"><div class="ds-wm-calhead"><div><small>CALIBRATION ATTACK RNG</small><strong>${cal.q} // ${fmt(cal.min,1)}–${fmt(cal.max,1)}%</strong></div><span>${has?'PLAYER ROLL':'ROLL REQUIRED'}</span></div><div class="ds-wm-rollgrid"><input data-wm-roll-range type="range" min="${cal.min}" max="${cal.max}" step="0.1" value="${has?roll:cal.min}"><label><input data-wm-roll-number type="number" min="${cal.min}" max="${cal.max}" step="0.1" value="${has?fmt(roll,1):''}" placeholder="e.g. 42.7"><b>%</b></label></div><div class="ds-wm-range"><span>${fmt(cal.min,1)}%</span><span>${has?`Your roll: ${fmt(roll,1)}%`:'Type your exact roll or drag the slider'}</span><span>${fmt(cal.max,1)}%</span></div></div>`;
    }
  }else if(cal){
    calHtml=`<div class="ds-wm-cal"><div class="ds-wm-calhead"><div><small>CALIBRATION ATTACK RNG</small><strong>Calibration detected // choose rarity</strong></div><span>RANGE NEEDED</span></div><label class="ds-wm-quality"><span>Calibration rarity</span><select data-wm-cal-quality><option value="">Choose…</option><option>Rare</option><option>Epic</option><option>Legendary</option></select></label><p>Once rarity is known, Dead Signal loads the mined legal RNG range automatically.</p></div>`;
  }else{
    calHtml='<div class="ds-wm-cal ds-wm-empty"><small>CALIBRATION ATTACK RNG</small><strong>Select a Calibration Blueprint on this weapon</strong><p>The synced slider + exact input will appear here using that blueprint rarity’s mined legal range.</p></div>';
  }

  panel.innerHTML=`
    <div class="ds-wm-head"><div><small>MINED WEAPON CORE</small><strong>${name}</strong></div><span>GAME DATA</span></div>
    ${(tierControl||starControl)?`<div class="ds-wm-controls">${tierControl}${starControl}</div>`:''}
    <div class="ds-wm-proof"><div><small>Tier ${['','I','II','III','IV','V'][tier]} base</small><b>${fmt(tAttack,0)}</b></div><i>×</i><div><small>${star}★ ratio</small><b>${fmt(ratio,ratio%1?3:2)}×</b></div><i>→</i><div class="hot"><small>Intrinsic Attack</small><b>${fmt(intrinsic,0)}</b></div></div>
    <div class="ds-wm-stats">${stat('RPM',base[0])}${stat('Magazine',base[1])}${stat('Range',base[2])}${stat('Accuracy',base[3])}${stat('Stability',base[4])}${stat('Mobility',base[5])}${stat('Reload',base[6],'s')}${baseAttrHtml(w)}</div>
    ${calHtml}
    ${cal&&roll!=null?`<div class="ds-wm-result"><div><small>ATTACK + CALIBRATION RNG PREVIEW</small><strong>${fmt(rngAttack,0)}</strong></div><p>${fmt(intrinsic,0)} × (1 + ${fmt(roll,1)}%) = ${fmt(intrinsic*(1+roll/100),3)} → <b>${fmt(rngAttack,0)}</b></p><em>RNG contribution only. Fixed calibration-style effects and accessory Attack modifiers stay separate until their exact card integration is wired.</em></div>`:''}
  `;

  panel.dataset.signature=signature;
  panel.querySelector('[data-wm-tier]')?.addEventListener('change',e=>{storeChoice(key,{tier:Number(e.target.value)});panel.dataset.signature='';renderCard(card);});
  panel.querySelector('[data-wm-star]')?.addEventListener('change',e=>{storeChoice(key,{star:Number(e.target.value)});panel.dataset.signature='';renderCard(card);});
  panel.querySelector('[data-wm-cal-quality]')?.addEventListener('change',e=>{const q=e.target.value;if(q){storeChoice(key,{calQuality:q,calRoll:null});panel.dataset.signature='';renderCard(card);}});
  const range=panel.querySelector('[data-wm-roll-range]');
  const number=panel.querySelector('[data-wm-roll-number]');
  if(range&&number&&cal){
    range.addEventListener('input',()=>{const v=Number(range.value);storeChoice(key,{calRoll:v,calId:cal.id});number.value=fmt(v,1);panel.dataset.signature='';renderCard(card);});
    number.addEventListener('input',()=>{
      if(number.value==='')return;
      let v=Number(number.value); if(!Number.isFinite(v))return;
      v=Math.min(cal.max,Math.max(cal.min,v));
      v=Math.round(v*10)/10;
      storeChoice(key,{calRoll:v,calId:cal.id});range.value=String(v);panel.dataset.signature='';renderCard(card);
    });
    number.addEventListener('change',()=>{
      if(number.value===''){storeChoice(key,{calRoll:null,calId:cal.id});panel.dataset.signature='';renderCard(card);}
    });
  }
}

function run(){document.querySelectorAll('.weapon-card').forEach(renderCard);}
function queue(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;run();});}
new MutationObserver(queue).observe(document.body,{childList:true,subtree:true,characterData:true});
document.addEventListener('change',e=>{if(e.target.closest?.('.weapon-card'))setTimeout(run,0);});
window.addEventListener('dead-signal:build-mode-change',run);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run,{once:true});else run();
setTimeout(run,120);setTimeout(run,500);
})();
