# Dead Signal Miner packaged startup regression — 2026-08-21

Observed failure:

- packaged Miner process remained responsive but showed no window after 30+ seconds
- memory climbed to roughly 1.7 GB
- no new Miner output/log files were created
- no Windows crash event was recorded
- last known-good packaged launch reported by the operator was v1.5.14.61

Root cause boundary:

`DeadSignalMinerApp.__init__()` builds the Evidence workspace before Tk enters `mainloop()`. The entity selector previously rebuilt the full cross-domain entity registry in `RegistrySelectorModel.__init__`, then refreshed/searches immediately. The legacy weapon Evidence workspace and the Phase 13 generalized workspace both construct this selector during UI creation, so a large real snapshot could trigger full registry indexing before Windows had any chance to paint the Miner window.

Hotfix:

- registry construction is deferred until the first explicit browse/search
- selector construction reads only the registered adapter type names
- canonical-ID routing does not require the browse registry; the typed adapter remains the identity/proof boundary
- recent-list lookup stays empty until the registry has actually been built
- initial selector setup records the preferred search term but performs no registry scan

Regression tests assert that model construction and canonical-ID routing perform zero registry rebuilds, while the first browse builds the registry exactly once.

This change does not alter evidence states, adapter proof logic, publication authority, normalized data, or Miner output.
