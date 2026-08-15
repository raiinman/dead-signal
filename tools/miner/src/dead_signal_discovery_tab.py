"""Dead Signal Discovery tab for Data Intelligence."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk

from dead_signal_discovery import DeadSignalDiscovery


PANEL = "#111519"
TEXT = "#eef1f4"
MUTED = "#9aa3ac"
AMBER = "#d5a23a"


class DiscoveryTab:
    def __init__(self, notebook: ttk.Notebook, host):
        self.host = host
        self.discovery = DeadSignalDiscovery(host.output)
        frame = host._tab(notebook, "Discovery")
        bar = tk.Frame(frame, bg=PANEL)
        bar.pack(fill="x", pady=(0, 8))
        host._button(bar, "RUN DISCOVERY SUITE", self._run).pack(side="left")
        host._button(bar, "DESCRIPTION HOTSPOTS", self._hotspots, muted=True).pack(side="left", padx=(8, 0))
        host._button(bar, "SCHEMA CLUSTERS", self._clusters, muted=True).pack(side="left", padx=(8, 0))
        host._button(bar, "STRUCTURAL OUTLIERS", self._outliers, muted=True).pack(side="left", padx=(8, 0))
        tk.Label(
            bar,
            text="DISCOVERY LEADS ONLY / NEVER IDENTITY EVIDENCE",
            bg=PANEL, fg=AMBER, font=("Segoe UI", 8, "bold"),
        ).pack(side="right")
        self.text = host._json_text(frame)
        self.text.pack(fill="both", expand=True)
        self.text.insert("1.0", "Run the Dead Signal Discovery Suite to cluster NeoX schemas, surface outliers, and rank description hotspots.\n")

    def _show(self, payload):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", json.dumps(payload, ensure_ascii=False, indent=2))

    def _run(self):
        try:
            self._show(self.discovery.run_all())
        except Exception as error:
            messagebox.showerror("Dead Signal Discovery", str(error), parent=self.host.window)

    def _cached(self):
        path = self.host.output / "published" / "reports" / "dead-signal-discovery.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return self.discovery.run_all()

    def _hotspots(self):
        try:
            self._show(self._cached().get("description_hotspots") or {})
        except Exception as error:
            messagebox.showerror("Dead Signal Discovery", str(error), parent=self.host.window)

    def _clusters(self):
        try:
            self._show(self._cached().get("schema_clusters") or {})
        except Exception as error:
            messagebox.showerror("Dead Signal Discovery", str(error), parent=self.host.window)

    def _outliers(self):
        try:
            self._show(self._cached().get("structural_outliers") or {})
        except Exception as error:
            messagebox.showerror("Dead Signal Discovery", str(error), parent=self.host.window)


def install_discovery_tab(notebook: ttk.Notebook, host) -> DiscoveryTab:
    controller = DiscoveryTab(notebook, host)
    host.discovery_tab = controller
    return controller
