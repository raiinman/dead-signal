(()=>{
'use strict';

const COMMUNITY=window.DS_COMMUNITY||{};
const calibrations=(COMMUNITY.calibrations||[])
  .filter(x=>x&&x.name)
  .sort((a,b)=>String(b.name).length-String(a.name).length);
const RARITIES=['Legendary','Epic','Rare'];

let queued=false;
const norm=v=>String(v??'').replace(/\s+/g,' ').trim();
const rarityOf=item=>norm(item?.rarity||item?.quality||item?.grade||'');

function rarityFromValue(value){
  const text=norm(value);
  for(const q of RARITIES)if(new RegExp(`\\b${q}\\b`,'i').test(text))return q;
  return '';
}
function rarityFromElement(el){
  if(!el)return '';
  const nodes=[el,...el.querySelectorAll('[data-rarity],[data-quality],[data-grade],[data-item-rarity],[data-item-quality],[class]')];
  for(const node of nodes){
    const values=[
      node.dataset?.rarity,node.dataset?.quality,node.dataset?.grade,node.dataset?.itemRarity,node.dataset?.itemQuality,
      node.getAttribute?.('data-rarity'),node.getAttribute?.('data-quality'),node.getAttribute?.('data-grade'),
      typeof node.className==='string'?node.className:''
    ];
    for(const value of values){const q=rarityFromValue(value);if(q)return q;}
  }
  return rarityFromValue(el.textContent||'');
}
function idHintsFromElement(el){
  if(!el)return[];
  const out=[];
  for(const node of [el,...el.querySelectorAll('[data-id],[data-item-id],[data-record-id],[data-calibration-id]')]){
    for(const value of [node.dataset?.id,node.dataset?.itemId,node.dataset?.recordId,node.dataset?.calibrationId,node.getAttribute?.('data-id'),node.getAttribute?.('data-item-id')]){
      if(value!=null&&String(value).trim())out.push(String(value).trim());
    }
  }
  return [...new Set(out)];
}
function itemId(item){return String(item?.id??item?.item_id??item?.itemId??item?.no??item?.item_no??'').trim();}

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
function nativeProgressionSelect(card,kind){
  for(const sel of card.querySelectorAll('select')){
    if(sel.closest('.ds-weapon-model'))continue;
    const texts=[...sel.options].map(o=>norm(o.textContent||o.value));
    if(kind==='tier'&&texts.filter(x=>romanTier(x)!=null).length>=2)return sel;
    if(kind==='star'&&texts.filter(x=>starValue(x)!=null).length>=2)return sel;
  }
  return null;
}
function directChild(card,node){
  if(!node)return null;
  let cur=node;
  while(cur&&cur.parentElement&&cur.parentElement!==card)cur=cur.parentElement;
  return cur&&cur.parentElement===card?cur:null;
}
function progressionAnchor(card){
  const progression=card.querySelector(':scope > .progression')||card.querySelector('.progression');
  if(progression)return directChild(card,progression)||progression;
  const tier=directChild(card,nativeProgressionSelect(card,'tier'));
  const star=directChild(card,nativeProgressionSelect(card,'star'));
  if(tier&&star){
    if(tier===star)return tier;
    return (tier.compareDocumentPosition(star)&Node.DOCUMENT_POSITION_FOLLOWING)?star:tier;
  }
  return tier||star||directChild(card,card.querySelector('.selected-item-head,.slot-head'));
}

function nativeCalibrationTrigger(card){
  const all=[...card.querySelectorAll('[data-pick],button,[role="button"]')]
    .filter(el=>!el.closest('.ds-weapon-model')&&!el.closest('dialog'));
  const explicit=all.find(el=>/calib/i.test(String(el.dataset?.pick||'')));
  if(explicit)return explicit;
  return all.find(el=>{
    const own=norm(el.textContent);
    const parent=norm(el.parentElement?.textContent);
    return /Calibration Blueprint/i.test(own)||(/Calibration Blueprint/i.test(parent)&&parent.length<320);
  })||null;
}
function nativeCalibrationBlock(card,trigger){
  if(!trigger)return null;
  const preferred=trigger.closest('.profile-select,.mini-select,.calibration-select,.slot-option,.config-row,.selection-row');
  if(preferred&&!preferred.closest('.ds-weapon-model'))return preferred;
  let node=trigger.parentElement;
  for(let i=0;i<4&&node&&node!==card;i++,node=node.parentElement){
    const txt=norm(node.textContent);
    if(/Calibration Blueprint/i.test(txt)&&
       !/(\bAmmo\b|Weapon Mod|Gear Tier|Blueprint Star|Attachment)/i.test(txt)&&
       txt.length<420){
      return node;
    }
  }
  return null;
}
function calibrationMatches(card,block,trigger){
  const haystack=norm(`${trigger?.textContent||''} ${block?.textContent||''} ${card.textContent||''}`).toLowerCase();
  return calibrations.filter(item=>{
    const n=norm(item.name).toLowerCase();
    return n.length>=4&&haystack.includes(n);
  });
}
function calibrationItemFromCard(card,block,trigger){
  const matches=calibrationMatches(card,block,trigger);
  if(!matches.length)return null;
  if(matches.length===1)return matches[0];

  const ids=[...idHintsFromElement(trigger),...idHintsFromElement(block)];
  if(ids.length){
    const byId=matches.find(item=>itemId(item)&&ids.includes(itemId(item)));
    if(byId)return byId;
  }

  const rarityHint=rarityFromElement(block)||rarityFromElement(trigger);
  if(rarityHint){
    const byRarity=matches.find(item=>rarityOf(item).toLowerCase()===rarityHint.toLowerCase());
    if(byRarity)return byRarity;
  }

  return null;
}
function calibrationDisplay(card,block,trigger){
  const item=calibrationItemFromCard(card,block,trigger);
  if(item){
    return {name:norm(item.name),rarity:rarityOf(item)};
  }

  const rarity=rarityFromElement(block)||rarityFromElement(trigger);
  let label=norm(trigger?.textContent||'');
  label=label.replace(/Calibration Blueprint\s*[-:]?/ig,'').trim();
  if(!label||/^(choose|select|empty|none|add)$/i.test(label))label='Select Calibration Blueprint';
  return {name:label,rarity};
}
function makeProxy(card,panel,trigger,block){
  const calBox=panel.querySelector('.ds-wm-cal');
  if(!calBox)return;
  const display=calibrationDisplay(card,block,trigger);
  const signature=`${display.name}|${display.rarity}|${trigger?'active':'disabled'}`;
  const existing=panel.querySelector('.ds-wm-cal-picker');
  if(existing&&existing.dataset.signature===signature&&existing._dsNativeTrigger===trigger)return;
  existing?.remove();

  const wrap=document.createElement('div');
  wrap.className='ds-wm-cal-picker';
  wrap.dataset.signature=signature;
  wrap.dataset.calibrationName=display.name;
  wrap.dataset.calibrationRarity=display.rarity||'';
  wrap._dsNativeTrigger=trigger;
  wrap.innerHTML=`
    <div class="ds-wm-cal-picker-label">
      <small>CRAFTING CALIBRATION</small>
      <span>Chosen when this weapon is crafted</span>
    </div>
    <button type="button" class="ds-wm-cal-picker-button" ${trigger?'':'disabled'}>
      <span>Calibration Blueprint</span>
      <strong>${display.name}</strong>
      ${display.rarity?`<em>${display.rarity}</em>`:''}
      <b>CHANGE</b>
    </button>`;
  calBox.before(wrap);
  if(trigger){
    wrap.querySelector('button').addEventListener('click',()=>trigger.click());
  }
}
function placePanel(card,panel){
  const anchor=progressionAnchor(card);
  if(anchor&&anchor.parentElement){
    if(anchor.nextElementSibling!==panel)anchor.after(panel);
    return;
  }
  const head=directChild(card,card.querySelector('.selected-item-head,.slot-head'));
  if(head&&head.nextElementSibling!==panel)head.after(panel);
}
function reorderPanel(panel){
  const desired=[
    panel.querySelector('.ds-wm-head'),
    panel.querySelector('.ds-wm-controls'),
    panel.querySelector('.ds-wm-cal-picker'),
    panel.querySelector('.ds-wm-cal'),
    panel.querySelector('.ds-cal-secondary-editor'),
    panel.querySelector('.ds-wm-proof'),
    panel.querySelector('.ds-wm-stats'),
    panel.querySelector('.ds-wm-result')
  ].filter(node=>node&&node.parentElement===panel);

  const children=[...panel.children];
  let last=-1;
  let ordered=true;
  for(const node of desired){
    const idx=children.indexOf(node);
    if(idx<last){ordered=false;break;}
    last=idx;
  }
  if(ordered)return;
  desired.forEach(node=>panel.append(node));
}
function enhance(card){
  const panel=card.querySelector('.ds-weapon-model');
  if(!panel)return;
  placePanel(card,panel);
  const trigger=nativeCalibrationTrigger(card);
  const block=nativeCalibrationBlock(card,trigger);
  makeProxy(card,panel,trigger,block);
  reorderPanel(panel);
  if(block&&block!==panel&&!block.closest('.ds-weapon-model')){
    if(!block.classList.contains('ds-native-calibration-relocated'))block.classList.add('ds-native-calibration-relocated');
    if(block.getAttribute('aria-hidden')!=='true')block.setAttribute('aria-hidden','true');
  }
  if(!panel.classList.contains('ds-crafting-order-active'))panel.classList.add('ds-crafting-order-active');
}
function run(){document.querySelectorAll('.weapon-card').forEach(enhance);}
function queue(){
  if(queued)return;
  queued=true;
  requestAnimationFrame(()=>{queued=false;run();});
}
new MutationObserver(queue).observe(document.body,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['class','data-rarity','data-quality','data-grade','data-item-id','data-id']});
document.addEventListener('change',e=>{if(e.target.closest?.('.weapon-card'))setTimeout(run,0);});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run,{once:true});else run();
setTimeout(run,150);
setTimeout(run,600);
})();
