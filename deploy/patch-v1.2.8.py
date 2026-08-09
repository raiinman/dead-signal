#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
app_path=root/'app.js'; css_path=root/'styles.css'; index_path=root/'index.html'; data_path=root/'data/community-data.js'
app=app_path.read_text(encoding='utf-8'); css=css_path.read_text(encoding='utf-8'); index=index_path.read_text(encoding='utf-8'); data=data_path.read_text(encoding='utf-8')

app=app.replace("PLANNER_VERSION='1.2.7'", "PLANNER_VERSION='1.2.8'", 1)
old_picker="""function pickerCard(x){const fk=favoriteKey(pick.type,x.id),fav=favorites.has(fk),facts=pickerFacts(x);return `<div class=\"pick-card ${rarityClass(x)}\"><button class=\"fav ${fav?'active':''}\" data-fav-type=\"${pick.type}\" data-fav-id=\"${esc(x.id)}\" title=\"Favorite\">★</button><button class=\"pick\" data-select=\"${esc(x.id)}\"><strong>${esc(x.name)}</strong>${rarityBadge(x)}<span>${esc([x.type,x.slot,x.setName,x.style,x.category].filter(Boolean).join(' · '))}</span>${facts?`<div class=\"picker-facts\">${esc(facts)}</div>`:''}${x.feature?`<div class=\"effect feature\">${esc(x.feature)}</div>`:''}${effectText(x)&&!x.feature?`<div class=\"effect\">${esc(effectText(x))}</div>`:''}</button></div>`}\n"""
new_picker="""function pickerCard(x){
  const fk=favoriteKey(pick.type,x.id),fav=favorites.has(fk),facts=pickerFacts(x);
  const meta=[x.type,x.slot,x.setName,x.style,x.category].filter(Boolean).join(' · ');
  const factChips=facts?facts.split(' · ').map(v=>`<span>${esc(v)}</span>`).join(''):'';
  const effect=x.feature||(!x.feature?effectText(x):'');
  return `<div class=\"pick-card ${rarityClass(x)}\">
    <button class=\"fav ${fav?'active':''}\" data-fav-type=\"${pick.type}\" data-fav-id=\"${esc(x.id)}\" title=\"${fav?'Remove from favorites':'Add to favorites'}\" aria-label=\"${fav?'Remove from favorites':'Add to favorites'}\">★</button>
    <button class=\"pick\" data-select=\"${esc(x.id)}\">
      <div class=\"pick-title-row\"><strong>${esc(x.name)}</strong>${rarityBadge(x)}</div>
      ${meta?`<div class=\"pick-meta\">${esc(meta)}</div>`:''}
      ${factChips?`<div class=\"picker-facts\">${factChips}</div>`:''}
      ${effect?`<div class=\"effect picker-effect${x.feature?' feature':''}\">${esc(effect)}</div>`:''}
    </button>
  </div>`
}\n"""
if old_picker not in app:
    raise RuntimeError('Expected v1.2.7 pickerCard block not found')
app=app.replace(old_picker,new_picker,1)

old_span='.pick strong,.pick span{display:block}.pick span{font-size:11px;color:#8f96a1;margin-top:4px}'
new_span='.pick strong,.pick>span{display:block}.pick>span{font-size:11px;color:#8f96a1;margin-top:4px}'
if old_span not in css:
    raise RuntimeError('Expected picker span CSS rule not found')
css=css.replace(old_span,new_span,1)

marker='/* v1.2.8 picker readability + rarity spacing */'
if marker not in css:
    css += r'''

/* v1.2.8 picker readability + rarity spacing */
#picker{width:min(1120px,96vw);max-height:90vh}
#picker .dialog-head{padding:17px 20px}
#picker .dialog-head h2{margin-top:3px;font-size:20px;letter-spacing:-.02em}
.picker-tools{display:grid;grid-template-columns:minmax(280px,1fr) 150px auto auto auto;gap:8px;padding:13px 20px 10px;align-items:stretch}
.picker-tools input,.picker-tools select,.picker-tools button{min-height:42px}
.filters{padding:0 20px 12px;gap:7px;flex-wrap:wrap;overflow:visible;border-bottom:1px solid rgba(255,255,255,.035)}
.filters button{padding:8px 11px}
.picker-list{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;padding:12px 20px 24px;align-items:start}
.pick-card{position:relative;display:block;min-width:0}
.pick-card>.fav{position:absolute;z-index:3;top:12px;right:12px;width:30px;min-width:30px;height:30px;padding:0;border-radius:8px;background:rgba(7,9,12,.72);color:#626a76;border-color:#303640;backdrop-filter:blur(5px)}
.pick-card>.fav:hover{color:#f0c96d;border-color:#80622c;background:#17140d}
.pick-card>.fav.active{color:#ffd262;border-color:#80622c;background:#1c170d}
.pick-card .pick{width:100%;min-height:144px;padding:14px 15px;text-align:left;border-radius:12px;overflow:hidden;transform:none}
.pick-card .pick:hover{transform:none;background:#1a1e25}
.pick-title-row{display:flex;align-items:flex-start;gap:10px;padding-right:36px;min-width:0}
.pick-title-row strong{min-width:0;flex:1;font-size:14px;line-height:1.25;letter-spacing:-.01em;white-space:normal;overflow-wrap:anywhere}
.pick-title-row .rarity-badge{display:inline-flex;flex:none;margin:0;padding:3px 7px;line-height:1.2}
.pick-title-row .rarity-badge i{width:5px;height:5px}
.pick-meta{margin-top:6px;color:#939ba8;font-size:10px;line-height:1.35;min-height:14px}
.picker-facts{display:flex;flex-wrap:wrap;gap:5px;margin-top:10px;color:inherit;font-weight:inherit}
.picker-facts span{display:inline-flex;align-items:center;margin:0;padding:4px 7px;border:1px solid #2c333d;border-radius:6px;background:#0a0d11;color:#d6dbe3;font-size:9px;font-weight:800;line-height:1;letter-spacing:.02em}
.pick-card.has-rarity .picker-facts span{border-color:color-mix(in srgb,var(--rarity-color) 20%,#2c333d)}
.pick-card .picker-effect{margin-top:10px;padding:8px 9px;line-height:1.45;color:#bdc4ce;background:#0d1015;border-left-width:2px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;max-height:58px}
.pick-card.has-rarity .picker-effect{border-left-color:color-mix(in srgb,var(--rarity-color) 65%,#87303b)}
.pick-card.has-rarity .pick{background-image:linear-gradient(115deg,var(--rarity-glow),transparent 30%)}
.pick-card.has-rarity .pick>strong{color:inherit}
@media(max-width:900px){.picker-tools{grid-template-columns:1fr 1fr}.picker-tools input{grid-column:1/-1}.picker-tools button{min-width:0}.picker-list{grid-template-columns:1fr}}
@media(max-width:560px){#picker{width:96vw}.picker-tools{grid-template-columns:1fr}.picker-tools input{grid-column:auto}.picker-list{padding:10px 12px 18px}.filters{padding-left:12px;padding-right:12px}.pick-title-row{display:grid;gap:6px}.pick-title-row .rarity-badge{grid-row:2}.pick-card .pick{min-height:0}}
'''

index=index.replace('1.2.7','1.2.8')
data=data.replace('"version":"1.2.7-community"','"version":"1.2.8-community"',1)
app_path.write_text(app,encoding='utf-8'); css_path.write_text(css,encoding='utf-8'); index_path.write_text(index,encoding='utf-8'); data_path.write_text(data,encoding='utf-8')
print('Dead Signal v1.2.8 picker readability patch applied')
