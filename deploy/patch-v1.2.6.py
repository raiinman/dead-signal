#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
app_path=root/'app.js'; index_path=root/'index.html'; data_path=root/'data/community-data.js'
app=app_path.read_text(encoding='utf-8'); index=index_path.read_text(encoding='utf-8'); data=data_path.read_text(encoding='utf-8')

app=app.replace("const SCHEMA=14, PLANNER_VERSION='1.2.5', MAX_CRADLES=8;","const SCHEMA=14, PLANNER_VERSION='1.2.6', MAX_CRADLES=8;")

restore="""function applyPick(id){
  const {type,slot,subslot}=pick;
  if(type==='weapon'){state.weapons[slot]=id;state.weaponConfig[slot]=defaultWeaponConfig();clampProgression(state.weaponConfig[slot],byId(D.weapons,id))}
  else if(type==='armorSet'){for(const s of armorSlots){state.armor[s]=null;state.armorMods[s]=null;state.armorModConfig[s]=defaultModConfig();state.armorConfig[s]=defaultArmorConfig();const piece=(D.armor||[]).find(x=>x.setId===id&&x.slot===s);if(piece){state.armor[s]=piece.id;clampProgression(state.armorConfig[s],piece)}}}
  else if(type==='armor'){state.armor[slot]=id;state.armorMods[slot]=null;state.armorConfig[slot]=defaultArmorConfig();clampProgression(state.armorConfig[slot],byId(D.armor,id))}
  else if(type==='armorMod'){state.armorMods[slot]=id;state.armorModConfig[slot]=defaultModConfig();}
  else if(type==='deviation')state.deviation=id;
  else if(type==='consumable')state.consumables[subslot]=id;
  else if(type==='attachment')state.weaponConfig[slot].attachments[subslot]=id;
  else {state.weaponConfig[slot][subslot]=id;if(type==='mod'){state.weaponConfig[slot].weaponModConfig=defaultModConfig();}if(type==='calibration'){initCalibration(slot,id)}}
  addRecent(type,id);$('picker').close();render();
}
function initCalibration(slot,id){initCurrentCalibration(slot,id)}
"""
marker='function clearPick(){'
if 'function applyPick(id){' not in app:
    if marker not in app: raise RuntimeError('clearPick anchor missing')
    app=app.replace(marker,restore+marker,1)

index=index.replace('1.2.5','1.2.6')
data=data.replace('"version":"1.2.5-community"','"version":"1.2.6-community"',1)

app_path.write_text(app,encoding='utf-8'); index_path.write_text(index,encoding='utf-8'); data_path.write_text(data,encoding='utf-8')
print('Dead Signal v1.2.6 picker selection patch applied')
