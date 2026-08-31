(()=>{
'use strict';

/* PLAYER v1.5.2 — build transition isolation
   The calibration presentation modules historically cached state by weapon/
   calibration identity. Reset them before a different build becomes active so
   a new/template/imported/loaded build cannot inherit values from the prior
   build before planner-state-bridge restores the target build extension. */

let resetting=false;

function setSafeDefaultMode(){
  if(window.DSBuildMode&&typeof window.DSBuildMode.set==='function'){
    window.DSBuildMode.set('gear',{confirmGod:false,persist:true});
    return;
  }
  try{localStorage.setItem('dead-signal-build-mode','gear');}catch(_){}
}
function resetSidecars(){
  if(resetting)return;
  resetting=true;
  try{
    window.DSWeaponModelUI?.reset?.();
    window.DSCalibrationDetailsUI?.reset?.();
  }finally{resetting=false;}
}
function resetForIncomingBuild(){
  setSafeDefaultMode();
  resetSidecars();
}

/* Capture phase intentionally runs before the core planner's bubble handlers. */
document.addEventListener('click',event=>{
  const target=event.target.closest?.('#resetBtn,[data-template],[data-load-id],[data-clone-id]');
  if(!target)return;
  resetForIncomingBuild();
},true);

document.addEventListener('change',event=>{
  if(event.target?.id==='importFile'&&event.target.files?.length)resetForIncomingBuild();
},true);

/* app.js consumes a share hash before these enhancement scripts load. Clear
   old sidecars immediately; planner-state-bridge will then restore the hash's
   own extension, or MY GEAR for a legacy link with no extension. */
if(/^#b=/.test(location.hash))resetForIncomingBuild();

window.DSPlannerTransitionReset={reset:resetForIncomingBuild};
})();
