"""Unified Dead Signal Data Intelligence workspace."""

from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from dead_signal_compiler_tab import install_compiler_tab
from dead_signal_description_flow_tab import install_description_flow_tab
from dead_signal_discovery_tab import install_discovery_tab
from dead_signal_intelligence_advanced import install_advanced_tabs
from dead_signal_intelligence_window import (
    BG,
    TEXT,
    DataIntelligenceWindow,
)
from dead_signal_schema_trace_tab import install_schema_trace_tab
from dead_signal_verification_tab import install_verification_tab


PANEL = "#111519"
PANEL_2 = "#171c21"
MUTED = "#9aa3ac"
RED = "#e52b32"
GREEN = "#4ed083"
BORDER = "#2a3138"

WORKSPACES = {
    "Explore": (
        ("NeoX Explorer", "Browse every structured table, record, and field."),
        ("Table Profiler", "Profile field shapes and compare table structure."),
        ("Identity Map", "Scan exact connected identities without fuzzy joins."),
        ("Analytics", "Query the read-only intelligence warehouse."),
    ),
    "Trace & Resolve": (
        ("Source Finder", "Review weapon-description candidates and evidence state."),
        ("Evidence Graph", "Visualize exact typed identity relationships."),
        ("Schema Trace", "Follow exact owners and typed next identifiers."),
        ("Description Flow", "Trace static UI description consumers offline."),
        ("Discovery", "Generate structural leads without promoting evidence."),
    ),
    "Review & Publish": (
        ("Workflow Lab", "Run repeatable read-only evidence workflows."),
        ("Verification", "Record explicit manual evidence decisions."),
        ("Publication Gate", "Inspect candidate readiness and blockers."),
        ("Launch Coverage", "Review post-promotion coverage by field."),
        ("Pipeline Inspector", "Inspect extraction-to-publication telemetry."),
    ),
    "Build": (
        ("Compiler", "Compile changed intelligence stages and export bundles."),
    ),
}


class DeadSignalDataIntelligence(DataIntelligenceWindow):
    """Complete Dead Signal research workspace over one local Miner snapshot."""

    @staticmethod
    def _tree(parent, columns, widths):
        """Build a Treeview with always-visible grab-and-drag scrollbars."""
        tree = ttk.Treeview(parent, columns=columns, show="headings", style="DSI.Treeview")
        for name, width in zip(columns, widths):
            tree.heading(name, text=name.upper())
            tree.column(name, width=width, stretch=True)

        vertical = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        vertical.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        return tree

    @staticmethod
    def _json_text(parent):
        """Build a text viewer with visible vertical and horizontal scrollbars."""
        text = tk.Text(
            parent,
            bg=BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            padx=10,
            pady=9,
            font=("Cascadia Mono", 9),
            wrap="none",
        )
        vertical = ttk.Scrollbar(parent, orient="vertical", command=text.yview)
        horizontal = ttk.Scrollbar(parent, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        vertical.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        return text

    def _build(self):
        super()._build()
        notebook = next(
            (child for child in self.window.winfo_children() if isinstance(child, ttk.Notebook)),
            None,
        )
        if notebook is None:
            raise RuntimeError("Dead Signal Data Intelligence notebook was not created")
        install_advanced_tabs(notebook, self)
        install_schema_trace_tab(notebook, self)
        install_discovery_tab(notebook, self)
        install_verification_tab(notebook, self)
        install_description_flow_tab(notebook, self)
        install_compiler_tab(notebook, self)
        self._install_task_shell(notebook)

    def _install_task_shell(self, notebook: ttk.Notebook) -> None:
        self.intelligence_notebook = notebook
        self.tool_tabs = {notebook.tab(tab, "text"): tab for tab in notebook.tabs()}
        style = ttk.Style(self.window)
        style.configure("DSIHub.TNotebook", background=BG, borderwidth=0, tabmargins=0)
        style.layout("DSIHub.TNotebook.Tab", [])
        notebook.configure(style="DSIHub.TNotebook")
        notebook.pack_forget()

        self.hub_tabs: dict[str, str] = {}
        overview = self._build_overview(notebook)
        notebook.insert(0, overview, text="Overview")
        self.hub_tabs["Overview"] = str(overview)
        for name, tools in WORKSPACES.items():
            frame = self._build_task_hub(notebook, name, tools)
            notebook.insert(len(self.hub_tabs), frame, text=name)
            self.hub_tabs[name] = str(frame)

        rail = tk.Frame(self.window, bg="#0d1013", width=205, highlightbackground=BORDER, highlightthickness=1)
        rail.pack(side="left", fill="y", padx=(22, 10), pady=(0, 22))
        rail.pack_propagate(False)
        tk.Label(rail, text="INTELLIGENCE", bg="#0d1013", fg=MUTED,
                 font=("Segoe UI", 8, "bold"), padx=18, pady=14).pack(anchor="w")
        self.hub_buttons = {}
        for name, glyph in (("Overview", "◉"), ("Explore", "⌕"), ("Trace & Resolve", "⌁"),
                            ("Review & Publish", "✓"), ("Build", "▶")):
            button = tk.Button(
                rail, text=f"  {glyph}   {name}", anchor="w",
                command=lambda target=name: self._show_hub(target), bg="#0d1013",
                activebackground=PANEL_2, fg="#c9ced3", activeforeground="white",
                relief="flat", bd=0, padx=16, pady=16, font=("Segoe UI", 10, "bold"), cursor="hand2",
            )
            button.pack(fill="x")
            self.hub_buttons[name] = button
        tk.Frame(rail, bg="#0d1013").pack(fill="both", expand=True)
        self._button(rail, "OPEN RESEARCH CONSOLE", self._open_evidence, muted=True).pack(fill="x", padx=12, pady=12)

        notebook.pack(side="left", fill="both", expand=True, padx=(0, 22), pady=(0, 22))
        for hub, tools in WORKSPACES.items():
            for title, _description in tools:
                tab = self.tool_tabs.get(title)
                if tab:
                    self._add_context_bar(notebook.nametowidget(tab), hub, title)
        self._show_hub("Overview")

    def _build_overview(self, notebook: ttk.Notebook) -> tk.Frame:
        frame = tk.Frame(notebook, bg=BG, padx=18, pady=18)
        tk.Label(frame, text="Intelligence Overview", bg=BG, fg=TEXT,
                 font=("Segoe UI", 21, "bold")).pack(anchor="w")
        tk.Label(frame, text="One view of the current snapshot, evidence health, and next useful actions.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 15))
        metrics = tk.Frame(frame, bg=BG)
        metrics.pack(fill="x")
        coverage = self._read_json(self.output / "published" / "reports" / "dead-signal-coverage-dashboard.json")
        registry = self._read_json(self.output / "published" / "reports" / "table-registry-summary.json")
        consumer = self._read_json(self.output / "published" / "reports" / "consumer-index-summary.json")
        graph = self._read_json(self.output / "published" / "reports" / "reference-graph-summary.json")
        fields = {str(row.get("field")): row for row in coverage.get("fields", []) if isinstance(row, dict)}
        values = (
            (self._count(registry, "tables", "table_files"), "structured tables", GREEN),
            (self._count(consumer, "files", "pyc_files"), "bytecode files", GREEN),
            (self._count(graph, "edges", "reference_edges"), "typed edges", GREEN),
            ((coverage.get("record_counts") or {}).get("blocker_slots", "—"), "unresolved slots", "#d5a23a"),
        )
        for value, label, color in values:
            card = tk.Frame(metrics, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=18, pady=15)
            card.pack(side="left", fill="x", expand=True, padx=(0, 10))
            tk.Label(card, text=f"{value:,}" if isinstance(value, int) else str(value), bg=PANEL, fg=color,
                     font=("Segoe UI", 18, "bold")).pack(anchor="w")
            tk.Label(card, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")

        lower = tk.Frame(frame, bg=BG)
        lower.pack(fill="both", expand=True, pady=(12, 0))
        health = tk.Frame(lower, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=18, pady=15)
        health.pack(side="left", fill="both", expand=True, padx=(0, 10))
        tk.Label(health, text="Evidence Health", bg=PANEL, fg=TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w")
        for field in ("Weapons", "Descriptions", "Tier-I ranged gun stats", "Firing mode", "Projectile semantics", "Cradle compatibility", "Special Skill"):
            row = fields.get(field, {})
            line = tk.Frame(health, bg=PANEL)
            line.pack(fill="x", pady=5)
            tk.Label(line, text=field, bg=PANEL, fg="#cbd1d6", font=("Segoe UI", 9)).pack(side="left")
            tk.Label(line, text=str(row.get("display") or "—"), bg=PANEL,
                     fg=GREEN if row.get("resolved") == row.get("applicable") else "#d5a23a",
                     font=("Segoe UI", 9, "bold")).pack(side="right")

        next_actions = tk.Frame(lower, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=18, pady=15)
        next_actions.pack(side="left", fill="both", expand=True)
        tk.Label(next_actions, text="Next Actions", bg=PANEL, fg=TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w")
        for title, copy, target in (
            ("Investigate unresolved evidence", "Trace exact owners and static consumers.", "Trace & Resolve"),
            ("Review publication blockers", "Inspect coverage, verification, and the gate.", "Review & Publish"),
            ("Compile changed stages", "Reuse cached work and export a fresh bundle.", "Build"),
        ):
            card = tk.Frame(next_actions, bg=PANEL_2, padx=12, pady=10)
            card.pack(fill="x", pady=(9, 0))
            tk.Label(card, text=title, bg=PANEL_2, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w")
            tk.Label(card, text=copy, bg=PANEL_2, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 6))
            self._button(card, "OPEN", lambda name=target: self._show_hub(name), muted=True).pack(anchor="e")
        return frame

    def _build_task_hub(self, notebook: ttk.Notebook, name: str, tools) -> tk.Frame:
        frame = tk.Frame(notebook, bg=BG, padx=18, pady=18)
        tk.Label(frame, text=name, bg=BG, fg=TEXT, font=("Segoe UI", 21, "bold")).pack(anchor="w")
        tk.Label(frame, text="Choose a focused tool; all work remains local and evidence-gated.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 15))
        grid = tk.Frame(frame, bg=BG)
        grid.pack(fill="both", expand=True)
        for index, (title, description) in enumerate(tools):
            card = tk.Frame(grid, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=18, pady=17)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=(0, 10), pady=(0, 10))
            tk.Label(card, text=title, bg=PANEL, fg=TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w")
            tk.Label(card, text=description, bg=PANEL, fg=MUTED, wraplength=390, justify="left",
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(7, 15))
            self._button(card, "OPEN TOOL", lambda target=title, hub=name: self._open_tool(target, hub),
                         muted=index != 0).pack(anchor="w")
        for column in range(2):
            grid.grid_columnconfigure(column, weight=1)
        for row in range((len(tools) + 1) // 2):
            grid.grid_rowconfigure(row, weight=1)
        return frame

    def _add_context_bar(self, frame: tk.Frame, hub: str, title: str) -> None:
        bar = tk.Frame(frame, bg="#0d1013", padx=10, pady=7)
        first = frame.winfo_children()[0] if frame.winfo_children() else None
        bar.pack(fill="x", pady=(0, 10), before=first)
        self._button(bar, f"← {hub.upper()}", lambda target=hub: self._show_hub(target), muted=True).pack(side="left")
        tk.Label(bar, text=title, bg="#0d1013", fg=TEXT, font=("Segoe UI", 11, "bold")).pack(side="left", padx=12)

    def _show_hub(self, name: str) -> None:
        self.intelligence_notebook.select(self.hub_tabs[name])
        for label, button in self.hub_buttons.items():
            button.configure(bg=PANEL_2 if label == name else "#0d1013", fg="white" if label == name else "#c9ced3")

    def _open_tool(self, title: str, hub: str) -> None:
        tab = self.tool_tabs.get(title)
        if tab:
            self.intelligence_notebook.select(tab)
        for label, button in self.hub_buttons.items():
            button.configure(bg=PANEL_2 if label == hub else "#0d1013", fg="white" if label == hub else "#c9ced3")

    @staticmethod
    def _read_json(path: Path) -> dict:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    @staticmethod
    def _count(payload: dict, *keys: str):
        counts = payload.get("record_counts") or {}
        for key in keys:
            if key in counts:
                return counts[key]
        return "—"


def open_data_intelligence(parent, output: Path, open_evidence_console):
    return DeadSignalDataIntelligence(parent, output, open_evidence_console)
