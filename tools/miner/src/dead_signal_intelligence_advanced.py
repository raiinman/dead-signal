"""Advanced Dead Signal Data Intelligence workspace tabs."""

from __future__ import annotations

import json
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from dead_signal_analytics import DeadSignalAnalytics, dependency_status
from dead_signal_evidence_graph import DeadSignalEvidenceGraph
from dead_signal_pipeline_inspector import inspect_existing_run
from dead_signal_publication_gate import build_gate_report
from dead_signal_workflow_lab import DeadSignalWorkflowLab, default_description_workflow
from dead_signal_trace_workspace import install_weapon_identity_trace
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
        self._identity_scan_running = False
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
        self.trace_workspace = install_weapon_identity_trace(frame, self.output, self.host)

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
        export_bar = tk.Frame(frame, bg=PANEL)
        export_bar.pack(fill="x", pady=(0, 8))
        self.identity_scan_button = self._button(
            export_bar,
            "SCAN ALL CONNECTED DATA + EXPORT ZIP",
            self._start_identity_scan,
        )
        self.identity_scan_button.pack(side="left")
        self.identity_scan_status = tk.StringVar(value="Exact-reference neighborhood export ready")
        tk.Label(
            export_bar,
            textvariable=self.identity_scan_status,
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(12, 0))
        tk.Label(
            export_bar,
            text="READ-ONLY SNAPSHOT / STREAMING JSONL / NO FUZZY JOINS",
            bg=PANEL,
            fg=AMBER,
            font=("Segoe UI", 8, "bold"),
        ).pack(side="right")
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
            lines.extend([
                "",
                "FULL EXPORT",
                "Use SCAN ALL CONNECTED DATA + EXPORT ZIP to recursively walk every exact connected record from these seed identities.",
                "Every scalar in discovered records is exported; only identifier-like fields are recursively expanded.",
                "",
                "POLICY",
                result.get("policy") or "",
            ])
            self.identity_text.insert("1.0", "\n".join(lines))
        except Exception as error:
            messagebox.showerror("Dead Signal Identity Map", str(error), parent=self.host.window)

    def _start_identity_scan(self):
        if self._identity_scan_running:
            return
        identity = self._identity(self.identity_weapon.get())
        if not identity:
            messagebox.showinfo(
                "Dead Signal Identity Map",
                "Choose a Weapon first, then run the full connected-data export.",
                parent=self.host.window,
            )
            return
        self._identity_scan_running = True
        self.identity_scan_button.configure(state="disabled")
        self.identity_scan_status.set("Starting full exact-reference scan…")
        self.identity_text.delete("1.0", "end")
        self.identity_text.insert(
            "1.0",
            "FULL IDENTITY SCAN RUNNING\n\n"
            "The Reference Tracer is walking exact connected records and streaming the export to disk.\n"
            "The UI remains available while the scan runs.\n",
        )

        def activity(message):
            self.host.window.after(0, lambda text=str(message): self.identity_scan_status.set(text))

        def worker():
            try:
                result = self.graph.scan_identity_everything(identity, activity=activity)
            except Exception as error:
                self.host.window.after(0, lambda exc=error: self._identity_scan_failed(exc))
                return
            self.host.window.after(0, lambda payload=result: self._identity_scan_complete(payload))

        threading.Thread(target=worker, name="DeadSignalIdentityScan", daemon=True).start()

    def _identity_scan_failed(self, error):
        self._identity_scan_running = False
        self.identity_scan_button.configure(state="normal")
        self.identity_scan_status.set("Identity scan failed — progress breadcrumb preserved")
        messagebox.showerror("Dead Signal Identity Map", str(error), parent=self.host.window)

    def _identity_scan_complete(self, result):
        self._identity_scan_running = False
        self.identity_scan_button.configure(state="normal")
        counts = result.get("record_counts") or {}
        archive = str(result.get("archive") or "")
        self.identity_scan_status.set(
            f"DONE — {int(counts.get('connected_records') or 0):,} records / "
            f"{int(counts.get('connected_tables') or 0):,} tables"
        )
        summary = {
            "weapon": result.get("weapon"),
            "record_counts": counts,
            "depth_counts": result.get("depth_counts"),
            "limits": result.get("limits"),
            "truncated": result.get("truncated"),
            "truncated_reasons": result.get("truncated_reasons"),
            "archive": archive,
            "archive_size": result.get("archive_size"),
            "policy": result.get("policy"),
        }
        self.identity_text.delete("1.0", "end")
        self.identity_text.insert("1.0", json.dumps(summary, ensure_ascii=False, indent=2))
        messagebox.showinfo(
            "Dead Signal Identity Map",
            f"Full connected-data ZIP export complete.\n\n{archive}",
            parent=self.host.window,
        )

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
