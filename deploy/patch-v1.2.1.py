#!/usr/bin/env python3
from pathlib import Path
import json,re,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')

def rw(rel,fn):
    p=root/rel; s=p.read_text(); p.write_text(fn(s))

# Version + cache-busted asset URLs.
def patch_index(s):
    s=s.replace('COMMUNITY v1.2.0','COMMUNITY v1.2.1')
    s=s.replace('href="styles.css"','href="styles.css?v=1.2.1"')
    s=s.replace('src="data/community-data.js"','src="data/community-data.js?v=1.2.1"')
    s=s.replace('src="app.js"','src="app.js?v=1.2.1"')
    return s
rw('index.html',patch_index)

# Replace corpus strip with a structured responsive status deck.
def patch_app(s):
    s=s.replace("const SCHEMA=14, PLANNER_VERSION='1.2.0'", "const SCHEMA=14, PLANNER_VERSION='1.2.1'")
    start=s.index('function renderCatalogStrip(){')
    end=s.index('\nfunction render(){',start)
    block=r'''function renderCatalogStrip(){
  const el=$('catalogStrip');if(!el)return;
  const R=D.meta?.referenceTotals||{};
  const rows=[
    {label:'Weapons',value:(D.weapons||[]).length,total:R.weapons},
    {label:'Armor',value:(D.armor||[]).length,total:R.armor},
    {label:'Armor sets',value:(D.armorSets||[]).length,total:R.armorSets},
    {label:'Mods',value:(D.mods||[]).length,total:R.mods},
    {label:'Combat deviations',value:(D.deviations||[]).filter(x=>x.role==='Combat').length,total:R.combatDeviations},
    {label:'Attachments',value:(D.attachments||[]).length,total:R.attachments},
    {label:'Cradles',value:(D.cradles||[]).length,total:R.cradles}
  ];
  const metrics=rows.map(r=>{
    const hasRef=Number.isFinite(Number(r.total))&&Number(r.total)>0,stale=hasRef&&r.value>Number(r.total);
    const pct=hasRef&&!stale?Math.min(100,Math.round(r.value/Number(r.total)*100)):0;
    return `<div class="catalog-metric ${stale?'stale':''}" title="${stale?'The community reference count is older than the official records already indexed by Dead Signal.':'Dead Signal indexed records compared with a community reference snapshot.'}"><div class="catalog-metric-head"><span>${esc(r.label)}</span>${stale?'<em>REF STALE</em>':''}</div><div class="catalog-value"><strong>${r.value}</strong>${hasRef?`<small>/ ${r.total} ref</small>`:'<small>indexed</small>'}</div>${hasRef&&!stale?`<div class="catalog-meter"><i style="width:${pct}%"></i></div>`:'<div class="catalog-meter stale"><i></i></div>'}</div>`;
  }).join('');
  el.innerHTML=`<div class="catalog-intro"><div class="catalog-kicker"><b>COMMUNITY CORPUS</b><span>v${esc(PLANNER_VERSION)}</span></div><p>Dead Signal indexed records. Reference counts are community snapshots and can lag official updates; provenance stays visible without outbound links.</p></div><div class="catalog-counts">${metrics}</div>`;
}'''
    return s[:start]+block+s[end:]
rw('app.js',patch_app)

# New/current official records; keep unknown comparable T5 values blank instead of inventing them.
p=root/'data/community-data.js'
raw=p.read_text(); data=json.loads(raw.split('=',1)[1].strip().rstrip(';'))
data['meta']['version']='1.2.1-community'
data['meta']['note']='Community-first Ultimate Planner corpus. Source names are retained for transparency; no outbound source URLs are shipped in the client data. Reference totals are community snapshots and may lag newer official records.'

def addu(arr,obj):
    if not any(x.get('id')==obj['id'] for x in arr): arr.append(obj)

for w in [
 {"id":"fp-9","name":"FP-9","type":"SMG","rarity":"Uncommon","stats":{},"tags":["SMG","Tech Unlock"],"coverage":"official-basic","dataNote":"Official current weapon record. Comparable T5 planner stats are still pending verification, so Dead Signal does not invent them.","feature":"Low-fire-rate full-auto SMG intended for early-game close-range use.","sources":[{"site":"Once Human Official"}]},
 {"id":"ebr-14-octopus-grilled-rings","name":"EBR-14 - Octopus! Grilled Rings!","type":"Sniper Rifle","rarity":"Legendary","stats":{"damage":310,"rpm":300,"magazine":20,"critRate":5,"critDamage":40,"weakspot":50},"tags":["Burn","Blaze","Semi-Auto"],"coverage":"verified-current","feature":"Hits can apply Burn. At maximum Burn stacks it creates a fire ring for area damage; its trait also interacts with Blaze damage and Crit Rate.","sources":[{"site":"Once Human Official"},{"site":"OnceHumanDB"}]},
 {"id":"qbj97-fiery-trees-silver-flowers","name":"QBJ97 - Fiery Trees and Silver Flowers","type":"LMG","rarity":"Legendary","stats":{},"tags":["Unstable Bomber","Missile","Anniversary"],"coverage":"official-current","dataNote":"Official current weapon record. Comparable T5 planner stats are still pending verification.","feature":"Hits can apply Unstable Bomber. Sustained fire can launch missiles; missile explosions build Spark stacks that improve handling and increase Unstable Bomber trigger potential at full stacks.","sources":[{"site":"Once Human Official"}]},
 {"id":"sn700-finale","name":"SN700 - Finale","type":"Sniper Rifle","rarity":"Legendary","stats":{},"tags":["Shrapnel","Weakspot","Reverb"],"coverage":"official-current","dataNote":"Official current weapon record. Comparable T5 planner stats are still pending verification.","feature":"Hits can trigger Shrapnel and weakspot hits guarantee it. Shrapnel builds Reverb, improving multi-part Shrapnel behavior and the final shot of the magazine.","sources":[{"site":"Once Human Official"}]}
]: addu(data['weapons'],w)

for a in [
 {"id":"wind-interpreter-cap","name":"Wind Interpreter Cap","slot":"Helmet","hp":None,"pollution":None,"setId":None,"setName":"Standalone Key Armor","rarity":"Legendary","keyArmor":True,"coverage":"official-current","feature":"When Unstable Bomber explodes, automatically loads 1 bullet and increases Unstable Bomber DMG Rate by 25%.","sources":[{"site":"Once Human Official"}]},
 {"id":"ankh-mask","name":"Ankh Mask","slot":"Mask","hp":None,"pollution":None,"setId":None,"setName":"Standalone Key Armor","rarity":"Legendary","keyArmor":True,"coverage":"official-current","feature":"When the current magazine empties, it can consume reserve ammunition to refill part of the magazine.","sources":[{"site":"Once Human Official"}]}
]: addu(data['armor'],a)

if not any(x.get('id')=='ghost-link' for x in data['armorSets']):
    gl={"id":"ghost-link","name":"Ghost Link Set","rarity":"Legendary","pieces":[["Helmet","Ghost Link Hat",None,None],["Mask","Ghost Link Mask",None,None],["Top","Ghost Link Vest",None,None],["Gloves","Ghost Link Gloves",None,None],["Pants","Ghost Link Pants",None,None],["Shoes","Ghost Link Shoes",None,None]],"bonuses":[{"pieces":1,"text":"Crit Rate increases. Exact current percentage pending verification."},{"pieces":2,"text":"Reload Efficiency increases. Exact current percentage pending verification."},{"pieces":3,"text":"Weapon hits can grant Synchronize, a stacking Weapon DMG Boost, up to 10 stacks for 10 seconds."},{"pieces":4,"text":"At 10 Synchronize stacks, attacking an enemy can apply Overload, causing repeated damage to that enemy and nearby targets for 5 seconds."}],"coverage":"official-current","dataNote":"Official July 2026 set. Exact 1pc/2pc values are intentionally left qualitative until verified.","sources":[{"site":"Once Human Official"}]}
    data['armorSets'].append(gl)
    ids={'Helmet':'helmet','Mask':'mask','Top':'vest','Gloves':'gloves','Pants':'pants','Shoes':'shoes'}
    for slot,name,hp,pol in gl['pieces']:
        addu(data['armor'],{"id":f"ghost-link-{ids[slot]}","name":name,"slot":slot,"hp":None,"pollution":None,"setId":"ghost-link","setName":"Ghost Link Set","rarity":"Legendary","coverage":"official-current","dataNote":"Official current set piece; defensive base stats pending verification.","sources":[{"site":"Once Human Official"}]})

data['meta']['coverage'].update({'weapons':len(data['weapons']),'armorSets':len(data['armorSets']),'armorPieces':len(data['armor']),'mods':len(data.get('mods',[])),'combatDeviations':sum(1 for x in data.get('deviations',[]) if x.get('role')=='Combat'),'cradles':len(data.get('cradles',[])),'calibrations':len(data.get('calibrations',[])),'ammo':len(data.get('ammo',[]))})
p.write_text('window.DS_COMMUNITY = '+json.dumps(data,separators=(',',':'),ensure_ascii=False)+';\n')

# Development-phase cache policy: force revalidation so an old CSS file cannot pair with a new app.js.
def patch_ht(s):
    s=s.replace('ExpiresByType text/css "access plus 7 days"','ExpiresByType text/css "access plus 5 minutes"').replace('ExpiresByType application/javascript "access plus 7 days"','ExpiresByType application/javascript "access plus 5 minutes"').replace('ExpiresByType text/html "access plus 5 minutes"','ExpiresByType text/html "access plus 1 minute"')
    block='''\n<IfModule mod_headers.c>\n  <FilesMatch "\\.(html|css|js)$">\n    Header set Cache-Control "no-cache, must-revalidate"\n  </FilesMatch>\n</IfModule>\n'''
    if 'Cache-Control "no-cache, must-revalidate"' not in s:s+=block
    return s
rw('.htaccess',patch_ht)

css=r'''

/* v1.2.1 corpus status layout + cache-safe responsive polish */
.catalog-strip{width:min(1680px,100%);max-width:none;margin:12px auto 0;padding:0 18px;display:grid;grid-template-columns:minmax(250px,330px) minmax(0,1fr);gap:12px;align-items:stretch;color:var(--muted);font-size:10px}
.catalog-intro{min-width:0;padding:12px 14px;border:1px solid var(--line);border-radius:12px;background:linear-gradient(135deg,rgba(225,29,46,.075),rgba(13,15,19,.98) 42%);display:flex;flex-direction:column;justify-content:center}
.catalog-kicker{display:flex;align-items:center;justify-content:space-between;gap:10px}.catalog-kicker b{color:#f2f3f5;font-size:10px;letter-spacing:.14em}.catalog-kicker span{flex:none;color:#ff8c97;border:1px solid #5b2630;background:#241116;border-radius:999px;padding:2px 7px;font-weight:850;letter-spacing:.06em}
.catalog-intro p{margin:6px 0 0;color:#9da4af;font-size:10px;line-height:1.45;max-width:46ch}
.catalog-counts{min-width:0;display:grid;grid-template-columns:repeat(7,minmax(96px,1fr));gap:7px;align-items:stretch;justify-content:stretch}
.catalog-metric{min-width:0;border:1px solid var(--line);background:#0d0f13;border-radius:11px;padding:9px 10px;overflow:hidden}.catalog-metric.stale{border-color:#684b29;background:#15110c}.catalog-metric-head{display:flex;align-items:center;justify-content:space-between;gap:5px;min-width:0}.catalog-metric-head>span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#9aa1ac;font-size:8px;text-transform:uppercase;letter-spacing:.08em;font-weight:850}.catalog-metric-head em{flex:none;font-style:normal;color:#efbd72;font-size:6px;line-height:1;border:1px solid #654820;border-radius:999px;padding:2px 4px;letter-spacing:.05em}
.catalog-value{display:flex;align-items:baseline;gap:4px;min-width:0;margin-top:4px}.catalog-value strong{color:#fff;font-size:16px;line-height:1}.catalog-value small{min-width:0;color:#717985;font-size:8px;white-space:nowrap}.catalog-metric.stale .catalog-value small{color:#bd9867}
.catalog-meter{height:3px;margin-top:7px;border-radius:999px;background:#171b21;overflow:hidden}.catalog-meter i{display:block;height:100%;background:linear-gradient(90deg,#72131d,#e11d2e);border-radius:inherit}.catalog-meter.stale i{width:100%;background:repeating-linear-gradient(90deg,#6b4a22 0 6px,#2a2117 6px 10px)}
@media(max-width:1450px){.catalog-strip{grid-template-columns:1fr}.catalog-intro{display:grid;grid-template-columns:minmax(160px,auto) 1fr;align-items:center;gap:12px}.catalog-intro p{margin:0;max-width:none}.catalog-counts{grid-template-columns:repeat(4,minmax(120px,1fr))}}
@media(max-width:760px){.catalog-strip{padding:0 9px;margin-top:9px;gap:8px}.catalog-intro{display:block;padding:10px 11px}.catalog-intro p{margin-top:5px}.catalog-counts{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}.catalog-metric{padding:8px 9px}.catalog-value strong{font-size:15px}}
@media(max-width:390px){.catalog-counts{grid-template-columns:1fr 1fr}.catalog-metric-head em{display:none}}
'''
p=root/'styles.css'; s=p.read_text()
if 'v1.2.1 corpus status layout' not in s:p.write_text(s+css)
print('Dead Signal v1.2.1 patch applied')
