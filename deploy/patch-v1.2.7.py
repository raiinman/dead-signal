from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
app_path=root/'app.js'; css_path=root/'styles.css'; index_path=root/'index.html'; data_path=root/'data/community-data.js'
app=app_path.read_text(encoding='utf-8'); css=css_path.read_text(encoding='utf-8'); index=index_path.read_text(encoding='utf-8'); data=data_path.read_text(encoding='utf-8')

# Version bump
app=app.replace("const SCHEMA=14, PLANNER_VERSION='1.2.6', MAX_CRADLES=8;", "const SCHEMA=14, PLANNER_VERSION='1.2.7', MAX_CRADLES=8;")
index=index.replace('1.2.6','1.2.7')
data=data.replace('"version":"1.2.6-community"','"version":"1.2.7-community"',1)

# Remove the UI helper that renders per-item source badges.
app=app.replace("const sourcePills=x=>(x?.sources||[]).map(s=>`<span class=\"source-pill\" title=\"Community data provenance\">Source: ${esc(s.site)}</span>`).join('');\n","")

# Remove quality/status and provenance displays from player-facing item UI.
app=app.replace("${w?`${rarityBadge(w)}${coverageBadge(w)}`:''}", "${w?rarityBadge(w):''}")
app=app.replace("<div>${sourcePills(w)}</div>", "")
app=app.replace("<div>${coverageBadge(cal)}${sourcePills(cal)}</div>", "")
app=app.replace("<div>${sourcePills(a)}</div>", "")
app=app.replace("${x?`<div>${sourcePills(x)}</div>`:''}", "")
app=app.replace("${coverageBadge(x)}", "")
app=app.replace("<div>${sourcePills(x)}</div>", "")
app=app.replace("<div>${sourcePills(xs[0])}</div>", "")

# Remove the no-longer-needed UI status helper after removing all calls.
import re
app=re.sub(r"\nfunction coverageBadge\(x\)\{.*?\}\nfunction pickerCard", "\nfunction pickerCard", app, count=1, flags=re.S)

# Update catalog strip copy so it no longer claims per-item provenance is visible.
old="Dead Signal indexed records. Reference counts are community snapshots and can lag official updates; provenance stays visible without outbound links."
new="Dead Signal indexed records. Reference counts are community snapshots and can lag official updates."
if old not in app:
    raise RuntimeError('catalog strip copy not found')
app=app.replace(old,new)

# Add a single site-wide reference footer.
footer='''
<footer class="site-footer">
  <div class="footer-inner">
    <div>
      <b>DEAD SIGNAL</b>
      <span>Independent Once Human community planner.</span>
    </div>
    <p><strong>Community &amp; reference resources:</strong> Once Human Official · OnceHumanDB · Wikily. Resource names are provided as plain-text attribution only. Dead Signal is not affiliated with or endorsed by these services.</p>
  </div>
</footer>
'''
anchor='</main>\n\n<dialog id="picker">'
if anchor not in index:
    raise RuntimeError('footer anchor missing')
index=index.replace(anchor, '</main>'+footer+'\n<dialog id="picker">',1)

# Footer styling and remove legacy source-pill styling if present.
css=re.sub(r'\.source-pill\{[^}]*\}', '', css)
marker='/* v1.2.7 site-wide attribution footer */'
if marker not in css:
    css += '''

/* v1.2.7 site-wide attribution footer */
.site-footer{border-top:1px solid var(--line);background:#08090b;padding:22px 24px 28px;color:#777f8b}.footer-inner{max-width:1540px;margin:0 auto;display:flex;justify-content:space-between;gap:28px;align-items:flex-start}.footer-inner>div{display:grid;gap:3px;min-width:max-content}.footer-inner b{font-size:10px;letter-spacing:.18em;color:#aeb4bd}.footer-inner span{font-size:10px}.footer-inner p{max-width:850px;font-size:10px;line-height:1.55;text-align:right}.footer-inner strong{color:#9aa1ac;font-weight:800}@media(max-width:760px){.footer-inner{display:grid;gap:12px}.footer-inner p{text-align:left}}
'''

app_path.write_text(app,encoding='utf-8'); css_path.write_text(css,encoding='utf-8'); index_path.write_text(index,encoding='utf-8'); data_path.write_text(data,encoding='utf-8')
print('Dead Signal v1.2.7 provenance/footer patch applied')
