#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "// DEAD SIGNAL PLAYER MEDIA v1.3.2"


def replace_block(text: str, start: str, end: str, new_block: str) -> str:
    a = text.find(start)
    if a < 0:
        raise SystemExit(f'media patch start marker not found: {start}')
    b = text.find(end, a)
    if b < 0:
        raise SystemExit(f'media patch end marker not found: {end}')
    return text[:a] + new_block.rstrip() + "\n\n" + text[b:]


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: patch-player-media-v1.3.py <deploy-path>', file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    app = root / 'app.js'
    if not app.is_file():
        raise SystemExit(f'app.js not found: {app}')

    text = app.read_text(encoding='utf-8')
    if MARKER in text:
        print('Dead Signal player media renderer already installed')
        return 0

    anchor = "const esc=s=>String(s??'').replace(/[&<>\"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[m]));"
    if anchor not in text:
        raise SystemExit('media patch could not find esc() anchor')

    helpers = r'''
// DEAD SIGNAL PLAYER MEDIA v1.3.2
function playerMediaUrl(x){
  const raw=x?.imageAsset||x?.imageUrl||x?.image||x?.iconUrl||x?.icon||x?.assetPath||x?.imagePath||x?.media?.image||x?.media?.icon||'';
  const v=String(raw||'').trim().replace(/\\/g,'/');
  if(!v)return '';
  if(/^(https?:\/\/|data:image\/)/i.test(v))return v;
  if(v.startsWith('/build-planner/'))return v;
  if(v.startsWith('/assets/'))return '/build-planner'+v;
  if(v.startsWith('assets/'))return '/build-planner/'+v;
  if(v.startsWith('./assets/'))return '/build-planner/'+v.slice(2);
  const marker='reference-images/',pos=v.toLowerCase().indexOf(marker);
  if(pos>=0)return '/build-planner/assets/'+v.slice(pos);
  return '';
}
function playerMediaCode(x,fallback='DS'){
  const source=String(x?.type||x?.slot||x?.category||fallback||'DS');
  const map={'Assault Rifle':'AR','Submachine Gun':'SMG','Light Machine Gun':'LMG','Sniper Rifle':'SR','Shotgun':'SG','Pistol':'HG','Crossbow':'XBOW','Melee':'MELEE','Helmet':'HEAD','Mask':'MASK','Top':'TOP','Gloves':'HANDS','Pants':'LEGS','Shoes':'FEET'};
  return map[source]||source.replace(/[^a-z0-9]/gi,'').slice(0,6).toUpperCase()||'DS';
}
function playerMedia(x,size='picker',fallback='DS'){
  const src=playerMediaUrl(x),code=playerMediaCode(x,fallback),alt=esc(x?.name||fallback||'Dead Signal item');
  return `<div class="item-media item-media-${size} ${src?'has-image':'no-image'}">${src?`<img src="${esc(src)}" alt="${alt}" loading="lazy" decoding="async">`:''}<div class="media-fallback"><b>${esc(code)}</b><small>${src?'IMAGE UNAVAILABLE':'NO IMAGE'}</small></div></div>`;
}
'''.strip()
    text = text.replace(anchor, anchor + "\n" + helpers, 1)

    render_weapons = r'''function renderWeapons(){
  $('weapons').innerHTML=weaponSlots.map(([slot,label])=>{
    const w=byId(D.weapons,state.weapons[slot]), c=state.weaponConfig[slot]||defaultWeaponConfig(), st=w?.stats||{};
    return `<article class="weapon-card ${w?'filled':''} ${rarityClass(w)}">
      <div class="selected-item-head weapon-selected-head">${playerMedia(w,'selected',label+' weapon')}<div class="selected-item-copy"><div class="slot-head"><div><div class="slot-label">${label.toUpperCase()} WEAPON</div><div class="item-name">${esc(w?.name||'Empty')}</div><div class="subtle">${w?esc(w.type):'Choose a weapon'}</div>${w?rarityBadge(w):''}</div>${w?`<button class="tiny-clear" data-clear-slot="weapon" data-slot="${slot}" title="Clear">×</button>`:''}</div></div></div>
      ${w?`<div class="tag-row">${(w.tags||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join('')}</div>
      <div class="stats"><div><b>${st.damage??'—'}</b><span>DMG</span></div><div><b>${st.rpm??'—'}</b><span>RPM</span></div><div><b>${st.magazine??'—'}</b><span>MAG</span></div><div><b>${st.critRate??'—'}%</b><span>CRIT</span></div><div><b>${st.critDamage??'—'}%</b><span>CRIT DMG</span></div><div><b>${st.weakspot??'—'}%</b><span>WEAKSPOT</span></div></div>
      ${progressionRow('weapon',slot,c,w?.rarity)}${w.feature?`<div class="effect feature">${esc(w.feature)}</div>`:''}`:''}
      <button class="select-button" data-pick="weapon" data-slot="${slot}">${w?'Change weapon':'Select '+label}</button>
      ${w?renderWeaponParts(slot,w,c):''}
    </article>`;
  }).join('');
}'''
    text = replace_block(text, 'function renderWeapons(){', 'function renderWeaponParts(', render_weapons)

    render_armor = r'''function renderArmor(){
  $('armor').innerHTML=armorSlots.map(slot=>{
    const a=byId(D.armor,state.armor[slot]),m=byId(D.mods,state.armorMods[slot]),cfg=state.armorConfig[slot]||defaultArmorConfig(),mcfg=state.armorModConfig[slot]||defaultModConfig();
    const quality=a?.dataQuality==='community-conflict'?'<span class="quality-badge warn">COMMUNITY CONFLICT</span>':a?.keyArmor?'<span class="quality-badge key">KEY ARMOR</span>':'';
    return `<article class="gear-card ${a?'filled':''} ${rarityClass(a)}"><div class="selected-item-head armor-selected-head">${playerMedia(a,'selected',slot)}<div class="selected-item-copy"><div class="slot-head"><div><div class="slot-label">${slot.toUpperCase()}</div><div class="item-name">${esc(a?.name||'Empty')}</div><div class="subtle">${a?esc(a.setName||'Standalone'):'Choose armor'}</div>${a?rarityBadge(a):''}${quality}</div>${a?`<button class="tiny-clear" data-clear-slot="armor" data-slot="${slot}">×</button>`:''}</div></div></div>
      ${a?`<div class="stats compact"><div><b>${a.hp??'—'}</b><span>HP</span></div><div><b>${a.pollution??'—'}</b><span>POLLUTION</span></div></div>${a.feature?`<div class="effect feature">${esc(a.feature)}</div>`:''}${progressionRow('armor',slot,cfg,a?.rarity)}`:''}
      <button class="select-button" data-pick="armor" data-slot="${slot}">${a?'Change armor':'Select '+slot}</button>
      ${a?`<div class="mini-select ${rarityClass(m)}"><button data-pick="armorMod" data-slot="${slot}"><span><b>${slot} Mod</b><small>${esc(m?.variant||'')}</small></span><span class="choice"><span>${esc(m?.name||'Select')}${m?rarityBadge(m):''}</span> <i>›</i></span></button>${m?`<div class="effect">${esc(effectText(m))}</div>${renderModInstance('armor',slot,m,mcfg)}`:''}</div>`:''}
    </article>`;
  }).join('');
}'''
    text = replace_block(text, 'function renderArmor(){', 'function renderSystems(){', render_armor)

    start = text.find('function systemCard(')
    end = text.find('\n\nfunction completionInfo()', start)
    if start < 0 or end < 0:
        raise SystemExit('media patch could not locate systemCard')
    system_card = r'''function systemCard(label,x,type,subslot,desc){return `<article class="system-card ${x?'filled':''} ${rarityClass(x)}"><div class="system-card-head">${playerMedia(x,'system',label)}<div><div class="slot-label">${label}</div><div class="item-name">${esc(x?.name||'Empty')}</div>${x?rarityBadge(x):''}</div></div><div class="subtle system-description">${esc(desc)}</div><button class="select-button" data-pick="${type}" ${subslot?`data-subslot="${subslot}"`:''}>${x?'Change':'Select'}</button></article>`}'''
    text = text[:start] + system_card + text[end:]

    picker_card = r'''function pickerCard(x){
  const fk=favoriteKey(pick.type,x.id),fav=favorites.has(fk),facts=pickerFacts(x);
  const meta=[x.type,x.slot,x.setName,x.style,x.category].filter(Boolean).join(' · ');
  const factChips=facts?facts.split(' · ').map(v=>`<span>${esc(v)}</span>`).join(''):'';
  const effect=x.feature||(!x.feature?effectText(x):'');
  return `<div class="pick-card ${rarityClass(x)}">
    <button class="fav ${fav?'active':''}" data-fav-type="${pick.type}" data-fav-id="${esc(x.id)}" title="${fav?'Remove from favorites':'Add to favorites'}" aria-label="${fav?'Remove from favorites':'Add to favorites'}">★</button>
    <button class="pick" data-select="${esc(x.id)}">
      <div class="pick-layout">${playerMedia(x,'picker','Item')}<div class="pick-copy">
        <div class="pick-title-row"><strong>${esc(x.name)}</strong>${rarityBadge(x)}</div>
        ${meta?`<div class="pick-meta">${esc(meta)}</div>`:''}
        ${factChips?`<div class="picker-facts">${factChips}</div>`:''}
        ${effect?`<div class="effect picker-effect${x.feature?' feature':''}">${esc(effect)}</div>`:''}
      </div></div>
    </button>
  </div>`
}'''
    text = replace_block(text, 'function pickerCard(x){', 'function renderModGroups(', picker_card)

    old = "return entries.map(([name,xs])=>`<div class=\"mod-group ${rarityClass(xs[0])}\"><div class=\"mod-group-head\"><div><b>${esc(name)}</b>${rarityBadge(xs[0])}</div><span>${xs.length} variant${xs.length===1?'':'s'}</span></div>"
    new = "return entries.map(([name,xs])=>`<div class=\"mod-group ${rarityClass(xs[0])}\"><div class=\"mod-group-head\">${playerMedia(xs[0],'mod','Mod')}<div class=\"mod-group-title\"><b>${esc(name)}</b>${rarityBadge(xs[0])}</div><span>${xs.length} variant${xs.length===1?'':'s'}</span></div>"
    if old not in text:
        raise SystemExit('media patch could not locate mod-group header')
    text = text.replace(old, new, 1)

    app.write_text(text, encoding='utf-8')
    print('Dead Signal player media renderer installed directly into app.js')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
