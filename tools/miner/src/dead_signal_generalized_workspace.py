"""Phase 13 generalized Miner intelligence interface.

Presentation/orchestration only. All truth comes from registered adapters, Phase 11
invalidation state, and Phase 12 deterministic assessment/review machinery.
"""
from __future__ import annotations

import json
import threading
import tkinter as tk
from collections import Counter
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable

from dead_signal_entity_selector import EntityRegistrySelector
from dead_signal_evidence_review import navigation_targets
from dead_signal_generalized_graph import DeadSignalGeneralizedGraph

BG = "#07090b"; PANEL = "#0e1317"; PANEL_2 = "#131a20"; INK = "#eef4f6"
MUTED = "#7f8b93"; CYAN = "#24c7d9"; RED = "#ef3944"; GREEN = "#60d394"
AMBER = "#e3aa48"; BORDER = "#26323a"; NA = "#66717a"


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


class IntelligenceWorkspaceModel:
    """Headless Phase-13 model used by Overview, Evidence Graph, and Review Queue."""
    def __init__(self, output: Path | str):
        self.output = Path(output).expanduser().resolve()
        self.graph = DeadSignalGeneralizedGraph(self.output)
        self.registry_summary = self.graph.rebuild_entity_registry()

    def all_graphs(self, *, entity_type: str | None = None, limit: int = 1000) -> list[dict[str, Any]]:
        rows = self.graph.search_entities("", entity_type=entity_type, limit=limit)
        result = []
        for row in rows:
            try:
                result.append(self.graph.entity_graph(row["entity_type"], row["canonical_id"]))
            except (KeyError, ValueError):
                continue
        return result

    def overview(self) -> dict[str, Any]:
        dep = self.graph.invalidation.load()
        claim_rows = list((dep.get("claims") or {}).values())
        state_counts = Counter(str(row.get("result") or "UNRESOLVED") for row in claim_rows if isinstance(row, dict))
        invalidation = _load(self.output / "reports" / "claim-invalidation.json")
        review = self.graph.evidence_review_queue(self.all_graphs(), invalidation_report=invalidation)
        snapshot = _load(self.output / "reports" / "snapshot-data-diff.json")
        return {
            "registry": self.registry_summary,
            "claim_states": dict(state_counts),
            "invalidated": len(invalidation.get("review_queue") or []),
            "affected_pages": list(invalidation.get("affected_website_pages") or []),
            "missing_groups": list(review.get("shared_missing_groups") or [])[:12],
            "review_items": len(review.get("items") or []),
            "snapshot": snapshot.get("table_counts") or {},
        }

    def queue(self, domain: str | None = None) -> dict[str, Any]:
        invalidation = _load(self.output / "reports" / "claim-invalidation.json")
        return self.graph.evidence_review_queue(self.all_graphs(entity_type=domain), invalidation_report=invalidation, domain=domain)


class OverviewPanel(tk.Frame):
    def __init__(self, parent: tk.Misc, output: Path | str, open_graph: Callable[[], None]):
        super().__init__(parent, bg=BG)
        self.output = Path(output); self.open_graph = open_graph
        self._build(); self.refresh()

    def _build(self):
        header = tk.Frame(self, bg=BG); header.pack(fill="x", pady=(4, 12))
        tk.Label(header, text="INTELLIGENCE OVERVIEW", bg=BG, fg=INK, font=("Bahnschrift SemiCondensed", 22, "bold")).pack(side="left")
        tk.Button(header, text="OPEN EVIDENCE GRAPH", command=self.open_graph, bg=CYAN, fg="#041013", relief="flat", padx=12, pady=7, font=("Segoe UI",8,"bold")).pack(side="right")
        tk.Button(header, text="REFRESH", command=self.refresh, bg=PANEL_2, fg=INK, relief="flat", padx=12, pady=7).pack(side="right", padx=8)
        self.status = tk.Label(header, text="", bg=BG, fg=CYAN, font=("Segoe UI", 8, "bold")); self.status.pack(side="right", padx=12)
        self.cards = tk.Frame(self, bg=BG); self.cards.pack(fill="x")
        body = tk.PanedWindow(self, orient="horizontal", bg=BORDER, sashwidth=4, bd=0); body.pack(fill="both", expand=True, pady=(12,0))
        left = tk.Frame(body, bg=PANEL, padx=14, pady=12); right = tk.Frame(body, bg=PANEL, padx=14, pady=12)
        body.add(left, minsize=520, stretch="always"); body.add(right, minsize=420, stretch="always")
        tk.Label(left,text="DOMAIN INVENTORY",bg=PANEL,fg=INK,font=("Segoe UI",10,"bold")).pack(anchor="w")
        self.domains = ttk.Treeview(left, columns=("domain","entities"), show="headings", height=12)
        self.domains.heading("domain",text="DOMAIN"); self.domains.heading("entities",text="ENTITIES"); self.domains.pack(fill="both",expand=True,pady=(8,0))
        tk.Label(right,text="HIGH-IMPACT MISSING OWNERS / REASONS",bg=PANEL,fg=INK,font=("Segoe UI",10,"bold")).pack(anchor="w")
        self.missing = ttk.Treeview(right,columns=("count","reason"),show="headings",height=12)
        self.missing.heading("count",text="CLAIMS"); self.missing.heading("reason",text="MISSING OWNER / REASON"); self.missing.column("count",width=65,stretch=False); self.missing.pack(fill="both",expand=True,pady=(8,0))
        self.footer = tk.Label(self,bg=BG,fg=MUTED,justify="left",font=("Cascadia Mono",8)); self.footer.pack(fill="x",pady=(10,0))

    def refresh(self):
        self.status.configure(text="REFRESHING…")
        def worker():
            try: data = IntelligenceWorkspaceModel(self.output).overview()
            except Exception as exc: self.after(0, lambda: self.status.configure(text=f"UNAVAILABLE: {exc}")); return
            self.after(0, lambda: self._render(data))
        threading.Thread(target=worker,name="DeadSignalOverview",daemon=True).start()

    def _render(self,data):
        self.status.configure(text="READY")
        for child in self.cards.winfo_children(): child.destroy()
        states=data.get("claim_states") or {}
        cards=(("ENTITIES",data["registry"].get("total",0),CYAN),("PROVEN",states.get("PROVEN",0),GREEN),("REVIEW",data.get("review_items",0),AMBER),("INVALIDATED",data.get("invalidated",0),RED))
        for label,value,color in cards:
            card=tk.Frame(self.cards,bg=PANEL,highlightbackground=BORDER,highlightthickness=1,padx=18,pady=12); card.pack(side="left",fill="x",expand=True,padx=(0,8))
            tk.Label(card,text=str(value),bg=PANEL,fg=color,font=("Segoe UI",20,"bold")).pack(); tk.Label(card,text=label,bg=PANEL,fg=MUTED,font=("Segoe UI",8,"bold")).pack()
        self.domains.delete(*self.domains.get_children())
        for domain,count in sorted((data["registry"].get("by_entity_type") or {}).items()): self.domains.insert("","end",values=(domain,count))
        self.missing.delete(*self.missing.get_children())
        for row in data.get("missing_groups") or []: self.missing.insert("","end",values=(row.get("count"),row.get("missing_owner_or_reason")))
        snap=data.get("snapshot") or {}; affected=data.get("affected_pages") or []
        self.footer.configure(text=f"Snapshot tables: +{snap.get('added',0)} / Δ{snap.get('changed',0)} / patch-absent {snap.get('removed_or_patch_absent',0)}    Affected page keys: {len(affected)}")


class GeneralizedEvidencePanel(tk.Frame):
    """All-domain typed graph/claim/assessment inspector."""
    def __init__(self,parent:tk.Misc,output:Path|str,on_open_review:Callable[[],None]|None=None):
        super().__init__(parent,bg=BG); self.output=Path(output); self.engine=DeadSignalGeneralizedGraph(output); self.current_graph={}; self.current_claim=None; self.on_open_review=on_open_review
        self.subject_var=tk.StringVar(); self.status_var=tk.StringVar(value="READY"); self._build(); self.selector.set_initial("last valor")

    def _build(self):
        top=tk.Frame(self,bg=BG); top.pack(fill="x",pady=(2,8))
        tk.Label(top,text="EVIDENCE GRAPH",bg=BG,fg=INK,font=("Bahnschrift SemiCondensed",22,"bold")).pack(side="left")
        tk.Label(top,textvariable=self.status_var,bg=BG,fg=CYAN,font=("Segoe UI",8,"bold")).pack(side="right")
        self.selector=EntityRegistrySelector(self,self.output,subject_var=self.subject_var,on_select=self.run_trace); self.selector.pack(fill="x",pady=(0,8))
        split=tk.PanedWindow(self,orient="horizontal",bg=BORDER,sashwidth=4,bd=0); split.pack(fill="both",expand=True)
        left=tk.Frame(split,bg=PANEL,padx=10,pady=10); right=tk.Frame(split,bg=PANEL,padx=10,pady=10); split.add(left,minsize=690,stretch="always"); split.add(right,minsize=390,stretch="always")
        entitybar=tk.Frame(left,bg=PANEL); entitybar.pack(fill="x")
        self.entity_title=tk.Label(entitybar,text="SELECT AN ENTITY",bg=PANEL,fg=INK,font=("Segoe UI",12,"bold")); self.entity_title.pack(side="left")
        tk.Button(entitybar,text="RUN TRACE",command=self.run_trace,bg=CYAN,fg="#041013",relief="flat",padx=12,pady=6,font=("Segoe UI",8,"bold")).pack(side="right")
        tk.Label(left,text="CLAIMS",bg=PANEL,fg=MUTED,font=("Segoe UI",8,"bold")).pack(anchor="w",pady=(10,4))
        self.claims=ttk.Treeview(left,columns=("state","claim"),show="headings",height=12); self.claims.heading("state",text="STATE"); self.claims.heading("claim",text="CLAIM"); self.claims.column("state",width=110,stretch=False); self.claims.pack(fill="both",expand=True); self.claims.bind("<<TreeviewSelect>>",self._claim_selected)
        tk.Label(left,text="EDGES",bg=PANEL,fg=MUTED,font=("Segoe UI",8,"bold")).pack(anchor="w",pady=(10,4))
        self.edges=ttk.Treeview(left,columns=("state","relationship","destination"),show="headings",height=8)
        for c in ("state","relationship","destination"): self.edges.heading(c,text=c.upper())
        self.edges.column("state",width=100,stretch=False); self.edges.pack(fill="both",expand=True); self.edges.bind("<<TreeviewSelect>>",self._edge_selected)
        tk.Label(right,text="CLAIM ASSESSMENT / PROVENANCE",bg=PANEL,fg=INK,font=("Segoe UI",10,"bold")).pack(anchor="w")
        self.detail=tk.Text(right,bg=BG,fg=INK,insertbackground=INK,relief="flat",wrap="word",font=("Cascadia Mono",8),padx=10,pady=10); self.detail.pack(fill="both",expand=True,pady=(8,0))
        actions=tk.Frame(right,bg=PANEL); actions.pack(fill="x",pady=(8,0))
        tk.Button(actions,text="RECOMPUTE",command=self.run_trace,bg=PANEL_2,fg=INK,relief="flat",padx=10,pady=6).pack(side="left")
        if self.on_open_review: tk.Button(actions,text="OPEN REVIEW QUEUE",command=self.on_open_review,bg=PANEL_2,fg=INK,relief="flat",padx=10,pady=6).pack(side="left",padx=6)

    def set_target(self,entity_type:str,canonical_id:str):
        self.selector.entity_type_var.set(entity_type); self.selector.search_var.set(str(canonical_id)); self.selector.refresh(); self.run_trace()

    def run_trace(self):
        try: target=self.selector.selected_target()
        except Exception as exc: messagebox.showinfo("Evidence Graph",str(exc),parent=self); return
        self.status_var.set("TRACING…")
        def worker():
            try: graph=self.engine.entity_graph(target["entity_type"],target["canonical_id"])
            except Exception as exc: self.after(0,lambda:self._failed(exc)); return
            self.after(0,lambda:self._render(graph))
        threading.Thread(target=worker,name="DeadSignalGeneralizedTrace",daemon=True).start()

    def _failed(self,exc): self.status_var.set("TRACE FAILED"); messagebox.showerror("Evidence Graph",str(exc),parent=self)
    def _render(self,graph):
        self.current_graph=graph; self.current_claim=None; ent=graph.get("entity") or {}; self.entity_title.configure(text=f"{ent.get('name') or ent.get('canonical_id')}  ·  {ent.get('entity_type')}  [{ent.get('canonical_id')}]"); self.status_var.set("SCAN COMPLETE")
        self.claims.delete(*self.claims.get_children()); self.edges.delete(*self.edges.get_children())
        for i,claim in enumerate(graph.get("claims") or []): self.claims.insert("","end",iid=str(i),values=(claim.get("result"),claim.get("claim_type")))
        for i,edge in enumerate(graph.get("edges") or []): self.edges.insert("","end",iid=str(i),values=(edge.get("state"),edge.get("relationship_type"),edge.get("destination")))
        self._show_json({"entity":ent,"source_records":ent.get("source_records")})
    def _claim_selected(self,_evt=None):
        sel=self.claims.selection()
        if not sel:return
        claim=(self.current_graph.get("claims") or [])[int(sel[0])]; self.current_claim=claim
        assessment=self.engine.assess_claim(self.current_graph,claim)
        self._show_json({"assessment":assessment,"claim":claim,"navigation":navigation_targets(self.current_graph,claim)})
    def _edge_selected(self,_evt=None):
        sel=self.edges.selection()
        if not sel:return
        edge=(self.current_graph.get("edges") or [])[int(sel[0])]; self._show_json(edge)
    def _show_json(self,value): self.detail.delete("1.0","end"); self.detail.insert("1.0",json.dumps(value,ensure_ascii=False,indent=2,default=str))


class ReviewQueuePanel(tk.Frame):
    def __init__(self,parent:tk.Misc,output:Path|str,open_entity:Callable[[str,str],None]):
        super().__init__(parent,bg=BG); self.output=Path(output); self.open_entity=open_entity; self.model:IntelligenceWorkspaceModel|None=None; self.queue={}; self.domain=tk.StringVar(value="ALL"); self._build(); self.refresh()
    def _build(self):
        bar=tk.Frame(self,bg=BG); bar.pack(fill="x",pady=(2,8)); tk.Label(bar,text="REVIEW QUEUE",bg=BG,fg=INK,font=("Bahnschrift SemiCondensed",22,"bold")).pack(side="left")
        self.domain_combo=ttk.Combobox(bar,textvariable=self.domain,state="readonly",width=18); self.domain_combo.pack(side="right"); self.domain_combo.bind("<<ComboboxSelected>>",lambda _e:self.refresh())
        tk.Button(bar,text="REFRESH",command=self.refresh,bg=PANEL_2,fg=INK,relief="flat",padx=10,pady=6).pack(side="right",padx=8)
        split=tk.PanedWindow(self,orient="horizontal",bg=BORDER,sashwidth=4,bd=0); split.pack(fill="both",expand=True)
        left=tk.Frame(split,bg=PANEL,padx=10,pady=10); right=tk.Frame(split,bg=PANEL,padx=10,pady=10); split.add(left,minsize=700,stretch="always"); split.add(right,minsize=380,stretch="always")
        self.rows=ttk.Treeview(left,columns=("impact","state","domain","entity","claim"),show="headings")
        for c in ("impact","state","domain","entity","claim"): self.rows.heading(c,text=c.upper())
        self.rows.column("impact",width=65,stretch=False); self.rows.column("state",width=95,stretch=False); self.rows.column("domain",width=100,stretch=False); self.rows.pack(fill="both",expand=True); self.rows.bind("<<TreeviewSelect>>",self._selected); self.rows.bind("<Double-1>",lambda _e:self._open_selected())
        tk.Label(right,text="SHARED MISSING OWNERS",bg=PANEL,fg=INK,font=("Segoe UI",10,"bold")).pack(anchor="w")
        self.groups=ttk.Treeview(right,columns=("count","reason"),show="headings",height=10); self.groups.heading("count",text="COUNT"); self.groups.heading("reason",text="OWNER / REASON"); self.groups.column("count",width=60,stretch=False); self.groups.pack(fill="x",pady=(8,12))
        self.detail=tk.Text(right,bg=BG,fg=INK,relief="flat",wrap="word",font=("Cascadia Mono",8),padx=8,pady=8); self.detail.pack(fill="both",expand=True)
        actions=tk.Frame(right,bg=PANEL); actions.pack(fill="x",pady=(8,0)); tk.Button(actions,text="OPEN ENTITY",command=self._open_selected,bg=CYAN,fg="#041013",relief="flat",padx=10,pady=6).pack(side="left")
        tk.Button(actions,text="RECORD REVIEW",command=self._record,bg=PANEL_2,fg=INK,relief="flat",padx=10,pady=6).pack(side="left",padx=6); tk.Button(actions,text="REMOVE REVIEW",command=self._remove,bg=PANEL_2,fg=INK,relief="flat",padx=10,pady=6).pack(side="left")
    def refresh(self):
        try:
            self.model=IntelligenceWorkspaceModel(self.output); types=list(self.model.registry_summary.get("adapter_types") or []); self.domain_combo.configure(values=["ALL"]+types); domain=None if self.domain.get()=="ALL" else self.domain.get(); self.queue=self.model.queue(domain)
        except Exception as exc: messagebox.showerror("Review Queue",str(exc),parent=self); return
        self.rows.delete(*self.rows.get_children()); self.groups.delete(*self.groups.get_children())
        for i,row in enumerate(self.queue.get("items") or []): self.rows.insert("","end",iid=str(i),values=(row.get("launch_impact"),row.get("result"),row.get("entity_type"),row.get("canonical_id"),row.get("claim_type")))
        for row in self.queue.get("shared_missing_groups") or []: self.groups.insert("","end",values=(row.get("count"),row.get("missing_owner_or_reason")))
    def _item(self):
        sel=self.rows.selection(); return (self.queue.get("items") or [])[int(sel[0])] if sel else None
    def _selected(self,_e=None):
        row=self._item()
        if not row:return
        self.detail.delete("1.0","end"); self.detail.insert("1.0",json.dumps(row,ensure_ascii=False,indent=2,default=str))
    def _open_selected(self):
        row=self._item()
        if row:self.open_entity(str(row.get("entity_type")),str(row.get("canonical_id")))
    def _record(self):
        row=self._item()
        if not row or self.model is None:return
        reviewer=simpledialog.askstring("Manual Review","Reviewer name:",parent=self); note=simpledialog.askstring("Manual Review","Evidence note:",parent=self)
        if not reviewer or not note:return
        state=messagebox.askyesno("Manual Review","Record as CONFLICT?\n\nYes = CONFLICT\nNo = VERIFIED",parent=self); chosen="CONFLICT" if state else "VERIFIED"
        try:self.model.graph.record_manual_review(row["claim_key"],state=chosen,reviewer=reviewer,note=note); self.refresh()
        except Exception as exc:messagebox.showerror("Manual Review",str(exc),parent=self)
    def _remove(self):
        row=self._item()
        if row and self.model:self.model.graph.remove_manual_review(row["claim_key"]); self.refresh()
