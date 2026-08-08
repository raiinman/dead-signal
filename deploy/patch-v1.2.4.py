#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
app_path=root/'app.js'; index_path=root/'index.html'; data_path=root/'data/community-data.js'
app=app_path.read_text(encoding='utf-8')
index=index_path.read_text(encoding='utf-8')
data=data_path.read_text(encoding='utf-8')

app=app.replace("const SCHEMA=14, PLANNER_VERSION='1.2.3', MAX_CRADLES=8;","const SCHEMA=14, PLANNER_VERSION='1.2.4', MAX_CRADLES=8;")

start=app.find('function selectedRecords(){')
end=app.find('function renderSummary(){', start)
if start == -1 or end == -1:
    raise RuntimeError('Data audit function block not found')
app=app[:start]+app[end:]

audit_line='  <div class="summary-section"><h3>Data audit</h3>${renderDataAudit()}</div>\n'
if audit_line not in app:
    raise RuntimeError('Data audit report section not found')
app=app.replace(audit_line,'',1)

index=index.replace('1.2.3','1.2.4')
data=data.replace('"version":"1.2.3-community"','"version":"1.2.4-community"',1)

app_path.write_text(app,encoding='utf-8')
index_path.write_text(index,encoding='utf-8')
data_path.write_text(data,encoding='utf-8')
print('Dead Signal v1.2.4 removes user-facing Data Audit from Loadout Report')
