"""Advanced Dead Signal Data Intelligence workspace tabs."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk

from dead_signal_analytics import DeadSignalAnalytics, dependency_status
from dead_signal_evidence_graph import DeadSignalEvidenceGraph
from dead_signal_pipeline_inspector import inspect_existing_run
from dead_signal_publication_gate import build_gate_report
from dead_signal_workflow_lab import DeadSignalWorkflowLab, default_description_workflow
from research_console import ResearchConsole


BG = "#090b0d"
PANEL = "#111519"
PANEL_2 = "#171c21"
TEXT = "#eef1f4"
MUTED = "#9aa3ac"
RED = "#e52b32"
BORDER = "#2a3138"
GREEN = "#4ed083"
AMBER = "#d5a23a"


class AdvancedIntelligenceTabs:
    def __init__(self, notebook: ttk.Notebook, host):
        self.notebook = notebook
        self.host = host
        self.output = host.output
        self.console = ResearchConsole(self.output)
        self.graph = DeadSignalEvidenceGraph(self.output)
        self.analytics = DeadSignalAnalytics(self.output)
        self.workflow = DeadSignalWorkflowLab(self.output)
        self.weapon_choices = [
            f"{row.get('name')}  [{row.get('canonical_id') or row.get('blueprint_id')}]"
            for row in self.console.weapons()
        ]
        self._build_evidence_graph()
        self._build_identity_map()
        self._build_analytics()
        self._build_workflow_lab()
        self._build_pipeline_inspector()
        self._build_publication_gate()

    def _tab(self, title):
        return self.host._tab(self.notebook, title)

    def _button(self, parent, text, command, *, muted=False):
        return self.host._button(parent, text, command, muted=muted)

    def _text(self, parent):
        return self.host._json_text(parent)

    @staticmethod
    def _identity(value: str) -> str:
        value = str(value).strip()
        if value.endswith("]") and "[" in value:
            return value.rsplit("[", 1)[1][:-1]
        return value

    def _weapon_bar(self, parent, command, button_text):
        bar = tk.Frame(parent, bg=PANEL)
        bar.pack(fill="x", pady=(0, 8))
        variable = tk.StringVar()
        box = ttk.Combobox(bar, textvariable=variable, values=self.weapon_choices, state="normal")
        box.pack(side="left", fill="x", expand=True, ipady=4)
        self._button(bar, button_text, lambda: command(self._identity(variable.get()))).pack(side="left", padx=(8, 0))
        return variable

    def _build_evidence_graph(self):
        frame = self._tab("Evidence Graph")
        self.graph_weapon = self._weapon_bar(frame, self._load_graph, "BUILD EXACT GRAPH")
        split = tk.PanedWindow(frame, orient="horizontal", bg=BORDER, sashwidth=5)
        split.pack(fill="both", expand=True)
        canvas_panel = tk.Frame(split, bg=BG)
        detail_panel = tk.Frame(split, bg=PANEL_2)
        split.add(canvas_panel, minsize=700, stretch="always")
        split.add(detail_panel, minsize=390, stretch="always")
        self.graph_canvas = tk.Canvas(canvas_panel, bg=BG, highlightthickness=0)
        self.graph_canvas.pack(fill="both", expand=True)
        self.graph_detail = self._text(detail_panel)
        self.graph_detail.pack(fill="both", expand=True, padx=7, pady=7)
        self.graph_canvas.create_text(30, 30, anchor="nw", text="Choose a Weapon to build its exact evidence graph.", fill=MUTED, font=("Segoe UI", 11, "bold"))

    def _load_graph(self, identity):
        if not identity:
            return
        try:
            result = self.graph.weapon_graph(identity)
            self.graph_detail.delete("1.0", "end")
            self.graph_detail.insert("1.0", json.dumps(result, ensure_ascii=False, indent=2))
            self._draw_graph(result)
        except Exception as error:
            messagebox.showerror("Dead Signal Evidence Graph", str(error), parent=self.host.window)

    def _draw_graph(self, result):
        canvas = self.graph_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 720)
        root = next((node for node in result.get("nodes") or [] if node.get("kind") == "weapon"), None)
        if not root:
            return
        cx = width // 2
        canvas.create_rectangle(cx - 175, 38, cx + 175, 112, fill=PANEL_2, outline=RED, width=3)
        canvas.create_text(cx, 66, text=str(root.get("label") or "WEAPON").upper(), fill=TEXT, font=("Bahnschrift SemiCondensed", 16, "bold"))
        canvas.create_text(cx, 92, text="EXACT IDENTITY ROOT", fill=RED, font=("Segoe UI", 8, "bold"))
        identities = [node for node in result.get("nodes") or [] if node.get("kind") not in {"weapon", "record"}]
        record_lookup = {node["id"]: node for node in result.get("nodes") or [] if node.get("kind") == "record"}
        edge_lookup = {}
        for edge in result.get("edges") or []:
            edge_lookup.setdefault(edge.get("from"), []).append(edge)
        y = 160
        for index, node in enumerate(identities[:18]):
            side = -1 if index % 2 == 0 else 1
            row = index // 2
            x = cx + side * 245
            ny = y + row * 88
            state = str(node.get("state") or "UNRESOLVED")
            color = GREEN if state == "VERIFIED" else RED
            canvas.create_line(cx, 112, x, ny, fill="#43505b", width=2)
            canvas.create_rectangle(x - 150, ny - 27, x + 150, ny + 27, fill="#13181d", outline=color, width=2)
            canvas.create_text(x - 137, ny - 10, anchor="w", text=str(node.get("kind") or "ID").replace("_", " ").upper(), fill=TEXT, font=("Segoe UI", 8, "bold"))
            canvas.create_text(x - 137, ny + 10, anchor="w", text=str(node.get("label") or "")[:32], fill=color, font=("Cascadia Mono", 8))
            refs = [edge for edge in edge_lookup.get(node.get("id"), []) if edge.get("to") in record_lookup]
            canvas.create_text(x + 137, ny + 10, anchor="e", text=f"{len(refs)} refs", fill=MUTED, font=("Segoe UI", 8))
        canvas.configure(scrollregion=(0, 0, width, max(780, y + ((len(identities) + 1) // 2) * 88 + 60)))

    def _build_identity_map(self):
        frame = self._tab("Identity Map")
        self.identity_weapon = self._weapon_bar(frame, self._load_identity_map, "MAP EXACT IDENTITY")
        self.identity_text = self._text(frame)
        self.identity_text.pack(fill="both", expand=True)

    def _load_identity_map(self, identity):
        if not identity:
            return
        try:
            result = self.graph.identity_map(identity)
            self.identity_text.delete("1.0", "end")
            weapon = result.get("weapon") or {}
            lines = [str(weapon.get("name") or "").upper(), "═" * 72]
            for family in result.get("families") or []:
                lines.append(f"\n{str(family.get('kind') or '').replace('_', ' ').upper()}")
                for value in family.get("values") or []:
                    lines.append(f"  {value.get('value')}  [{value.get('state')}]  {value.get('exact_reference_count')} exact refs")
                    for table in (value.get("tables") or [])[:12]:
                        lines.append(f"    • {table.get('table')}  ×{table.get('occurrences')}")
            lines.extend(["", "POLICY", result.get("policy") or ""])
            self.identity_text.insert("1.0", "\n".join(lines))
        except Exception as error:
            messagebox.showerror("Dead Signal Identity Map", str(error), parent=self.host.window)

    def _build_analytics(self):
        frame = self._tab("Analytics")
        bar = tk.Frame(frame, bg=PANEL)
        bar.pack(fill="x", pady=(0, 8))
        self._button(bar, "BUILD / REFRESH ANALYTICS", self._build_warehouse).pack(side="left")
        self._button(bar, "DESCRIPTION LEADS", self._analytics_leads, muted=True).pack(side="left", padx=(8, 0))
        self._button(bar, "DESCRIPTION FIELD PROFILE", self._analytics_fields, muted=True).pack(side="left", padx=(8, 0))
        deps = dependency_status()
        status = "  ".join(f"{name.upper()}: {'READY' if row.get('available') else 'MISSING'}" for name, row in deps.items())
        tk.Label(bar, text=status, bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(side="right")
        self.analytics_sql = tk.Text(frame, height=5, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0, padx=10, pady=8, font=("Cascadia Mono", 9))
        self.analytics_sql.pack(fill="x")
        self.analytics_sql.insert("1.0", "SELECT weapon, candidate_state, score, table_name, field, text FROM source_finder ORDER BY score DESC")
        self._button(frame, "RUN READ-ONLY QUERY", self._run_analytics_query).pack(anchor="e", pady=7)
        self.analytics_text = self._text(frame)
        self.analytics_text.pack(fill="both", expand=True)

    def _show_analytics(self, payload):
        self.analytics_text.delete("1.0", "end")
        self.analytics_text.insert("1.0", json.dumps(payload, ensure_ascii=False, indent=2))

    def _build_warehouse(self):
        try:
            self._show_analytics(self.analytics.build())
        except Exception as error:
            messagebox.showerror("Dead Signal Analytics", str(error), parent=self.host.window)

    def _analytics_leads(self):
        try:
            self._show_analytics(self.analytics.description_leads())
        except Exception as error:
            messagebox.showerror("Dead Signal Analytics", str(error), parent=self.host.window)

    def _analytics_fields(self):
        try:
            self._show_analytics(self.analytics.suspicious_description_fields())
        except Exception as error:
            messagebox.showerror("Dead Signal Analytics", str(error), parent=self.host.window)

    def _run_analytics_query(self):
        try:
            self._show_analytics(self.analytics.query(self.analytics_sql.get("1.0", "end")))
        except Exception as error:
            messagebox.showerror("Dead Signal Analytics", str(error), parent=self.host.window)

    def _build_workflow_lab(self):
        frame = self._tab("Workflow Lab")
        self.workflow_weapon = self._weapon_bar(frame, self._run_default_workflow, "RUN DESCRIPTION TRACE")
        bar = tk.Frame(frame, bg=PANEL)
        bar.pack(fill="x", pady=(0, 8))
        self._button(bar, "SHOW WORKFLOW", self._show_default_workflow, muted=True).pack(side="left")
        tk.Label(bar, text="READ-ONLY / VERIFIED CANNOT BE ASSIGNED HERE", bg=PANEL, fg=AMBER, font=("Segoe UI", 8, "bold")).pack(side="right")
        self.workflow_text = self._text(frame)
        self.workflow_text.pack(fill="both", expand=True)
        self._show_default_workflow()

    def _show_default_workflow(self):
        self.workflow_text.delete("1.0", "end")
        self.workflow_text.insert("1.0", json.dumps(default_description_workflow(), ensure_ascii=False, indent=2))

    def _run_default_workflow(self, identity):
        if not identity:
            return
        try:
            result = self.workflow.run(default_description_workflow(), context={"weapon_identity": identity})
            self.workflow_text.delete("1.0", "end")
            self.workflow_text.insert("1.0", json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as error:
            messagebox.showerror("Dead Signal Workflow Lab", str(error), parent=self.host.window)

    def _build_pipeline_inspector(self):
        frame = self._tab("Pipeline Inspector")
        bar = tk.Frame(frame, bg=PANEL)
        bar.pack(fill="x", pady=(0, 8))
        self._button(bar, "REFRESH PIPELINE", self._refresh_pipeline, muted=True).pack(side="left")
        tk.Label(bar, text="EXTRACTION / NORMALIZATION / RESEARCH / PUBLISH TELEMETRY", bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(side="right")
        self.pipeline_text = self._text(frame)
        self.pipeline_text.pack(fill="both", expand=True)
        self._refresh_pipeline()

    def _refresh_pipeline(self):
        payload = inspect_existing_run(self.output)
        self.pipeline_text.delete("1.0", "end")
        self.pipeline_text.insert("1.0", json.dumps(payload, ensure_ascii=False, indent=2))

    def _build_publication_gate(self):
        frame = self._tab("Publication Gate")
        bar = tk.Frame(frame, bg=PANEL)
        bar.pack(fill="x", pady=(0, 8))
        self._button(bar, "RUN GATE REVIEW", self._refresh_gate).pack(side="left")
        tk.Label(bar, text="EXTRACTED ≠ RESOLVED ≠ CANDIDATE ≠ VERIFIED ≠ PUBLISHABLE", bg=PANEL, fg=RED, font=("Segoe UI", 8, "bold")).pack(side="right")
        self.gate_text = self._text(frame)
        self.gate_text.pack(fill="both", expand=True)
        self._refresh_gate()

    def _refresh_gate(self):
        try:
            payload = build_gate_report(self.output / "published" / "reports")
            self.gate_text.delete("1.0", "end")
            self.gate_text.insert("1.0", json.dumps(payload, ensure_ascii=False, indent=2))
        except Exception as error:
            self.gate_text.delete("1.0", "end")
            self.gate_text.insert("1.0", f"Publication Gate unavailable: {error}")


def install_advanced_tabs(notebook: ttk.Notebook, host) -> AdvancedIntelligenceTabs:
    controller = AdvancedIntelligenceTabs(notebook, host)
    host.advanced_intelligence = controller
    return controller
