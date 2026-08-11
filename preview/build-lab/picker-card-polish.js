(()=>{
'use strict';

let queued=false;
const norm=v=>String(v??'').replace(/\s+/g,' ').trim();

function tagTitleControls(card){
  const row=card.querySelector('.pick-title-row');
  if(!row)return;

  let favorite=[...row.querySelectorAll('button')].find(btn=>{
    const text=norm(btn.textContent);
    const aria=norm(btn.getAttribute('aria-label'));
    const title=norm(btn.getAttribute('title'));
    return text==='★'||/favorite/i.test(`${aria} ${title}`);
  });
  if(!favorite){
    favorite=[...card.querySelectorAll('button')].find(btn=>{
      const text=norm(btn.textContent);
      const aria=norm(btn.getAttribute('aria-label'));
      const title=norm(btn.getAttribute('title'));
      return text==='★'||/favorite/i.test(`${aria} ${title}`);
    })||null;
  }
  favorite?.classList.add('ds-picker-favorite');

  const rarityCandidates=[...row.querySelectorAll('*')]
    .filter(el=>el!==favorite)
    .filter(el=>/\b(COMMON|RARE|EPIC|LEGENDARY)\b/i.test(norm(el.textContent)))
    .sort((a,b)=>norm(a.textContent).length-norm(b.textContent).length);
  const rarity=rarityCandidates[0]||null;
  rarity?.classList.add('ds-picker-rarity-chip');

  if(favorite&&rarity)row.classList.add('ds-picker-title-controls-fixed');
}

function moveCalibrationEffect(card){
  if(!/Calibration Blueprint/i.test(norm(card.textContent||'')))return;
  const effect=card.querySelector('.ds-cal-mined-description');
  if(!effect)return;

  const titleRow=card.querySelector('.pick-title-row');
  const content=titleRow?.parentElement;
  if(!content||content===card)return;

  if(effect.parentElement!==content)content.append(effect);
  effect.classList.add('ds-cal-mined-description-inside');
}

function polishCard(card){
  tagTitleControls(card);
  moveCalibrationEffect(card);
}

function run(){document.querySelectorAll('#picker .pick-card').forEach(polishCard);}
function queue(){
  if(queued)return;
  queued=true;
  requestAnimationFrame(()=>{queued=false;run();});
}

new MutationObserver(queue).observe(document.body,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['class','data-rarity','data-quality','data-grade']});
document.addEventListener('click',e=>{if(e.target.closest?.('#picker'))setTimeout(run,0);});
document.addEventListener('change',e=>{if(e.target.closest?.('#picker'))setTimeout(run,0);});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run,{once:true});else run();
setTimeout(run,120);setTimeout(run,400);setTimeout(run,900);
})();
