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

function syncCalibrationEffect(card){
  if(!/Calibration Blueprint/i.test(norm(card.textContent||'')))return;

  const sources=[...card.querySelectorAll('.ds-cal-mined-description')];
  let source=sources.find(el=>el.parentElement===card)||sources[0]||null;
  if(!source)return;

  /* The source script searches only direct children. Keep exactly one source
     there so it never respawns a second footer copy. */
  if(source.parentElement!==card)card.append(source);
  for(const extra of sources){if(extra!==source)extra.remove();}
  source.classList.add('ds-cal-source-hidden');
  source.setAttribute('aria-hidden','true');

  const titleRow=card.querySelector('.pick-title-row');
  const content=titleRow?.parentElement;
  if(!content||content===card)return;

  let visible=content.querySelector('.ds-cal-mined-effect-inline');
  const text=norm(source.textContent);
  if(!text){visible?.remove();return;}
  if(!visible){
    visible=document.createElement('p');
    visible.className='ds-cal-mined-effect-inline';
    content.append(visible);
  }
  if(norm(visible.textContent)!==text)visible.textContent=text;
}

function polishCard(card){
  tagTitleControls(card);
  syncCalibrationEffect(card);
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
