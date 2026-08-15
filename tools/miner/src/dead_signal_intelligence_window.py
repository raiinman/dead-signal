"""Dead Signal Data Intelligence workspace.

A branded read-only research surface over the completed Miner snapshot. It
combines the NeoX Explorer, Table Profiler, and Source Finder while preserving the
existing exact-evidence Research Console as a dedicated deep-investigation view.
"""

from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from dead_signal_table_profiler import compare_profiles, profile_table
from neox_data_explorer import NeoXDataExplorer


BG = "#090b0d"
PANEL = "#111519"
PANEL_2 = "#171c21"
TEXT = "#eef1f4"
MUTED = "#9aa3ac"
RED = "#e52b32"
BORDER = "#2a3138"
GREEN = "#4ed083"
AMBER = "#d5a23a"


class DataIntelligenceWindow:
    def __init__(self, parent: tk.Misc, output: Path, open_evidence_console):
        self.parent = parent
        self.output = Path(output).expanduser().resolve()
        self.explorer = NeoXDataExplorer(self.output)
        self.open_evidence_console = open_evidence_console
        self.window = tk.Toplevel(parent)
        self.window.title("Dead Signal / Data Intelligence")
        self.window.geometry("1420x900")
        self.window.minsize(1080, 720)
        self.window.configure(bg=BG)
        self.selected_table = ""
        self.selected_layer = "current"
        self._build()
        self._load_tables()
        self._load_source_finder()

    @staticmethod
    def _button(parent, text, command, *, muted=False):
        return tk.Button(
            parent, text=text, command=command,
            bg=PANEL_2 if muted else RED,
            activebackground=BORDER if muted else "#ff4047",
            fg=TEXT if muted else "white", activeforeground="white",
            relief="flat", bd=0, padx=13, pady=7,
            font=("Segoe UI", 8, "bold"), cursor="hand2",
        )

    @staticmethod
    def _tree(parent, columns, widths):
        tree = ttk.Treeview(parent, columns=columns, show="headings", style="DSI.Treeview")
        for name, width in zip(columns, widths):
            tree.heading(name, text=name.upper())
            tree.column(name, width=width, stretch=True)
        return tree

    @staticmethod
    def _json_text(parent):
        return tk.Text(
            parent, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
            padx=10, pady=9, font=("Cascadia Mono", 9), wrap="none",
        )

    def _build(self):
        header = tk.Frame(self.window, bg=BG, padx=22, pady=15)
        header.pack(fill="x")
        tk.Label(header, text="DEAD SIGNAL", bg=BG, fg=TEXT,
                 font=("Bahnschrift SemiCondensed", 24, "bold")).pack(side="left")
        tk.Label(header, text="  /  DATA INTELLIGENCE", bg=BG, fg=RED,
                 font=("Bahnschrift SemiCondensed", 17, "bold")).pack(side="left", pady=(7, 0))
        self._button(header, "OPEN EXACT EVIDENCE CONSOLE", self._open_evidence, muted=True).pack(side="right")
        tk.Label(
            header,
            text="Explore NeoX tables, profile structures, and review research candidates. Discovery never publishes data.",
            bg=BG, fg=MUTED, font=("Segoe UI", 9),
        ).pack(side="right", padx=(0, 14), pady=(9, 0))

        style = ttk.Style(self.window)
        style.configure("DSI.Notebook", background=BG, borderwidth=0)
        style.configure("DSI.Notebook.Tab", background=PANEL, foreground=TEXT, padding=(13, 8))
        style.map("DSI.Notebook.Tab", background=[("selected", RED)], foreground=[("selected", "white")])
        style.configure("DSI.Treeview", background=BG, fieldbackground=BG, foreground=TEXT,
                        bordercolor=BORDER, rowheight=25)
        style.configure("DSI.Treeview.Heading", background="#d8d6d1", foreground="#15181b",
                        font=("Segoe UI", 8, "bold"))
        style.map("DSI.Treeview", background=[("selected", RED)], foreground=[("selected", "white")])

        notebook = ttk.Notebook(self.window, style="DSI.Notebook")
        notebook.pack(fill="both", expand=True, padx=22, pady=(0, 22))
        self._build_explorer(notebook)
        self._build_profiler(notebook)
        self._build_source_finder(notebook)

    def _tab(self, notebook, title):
        frame = tk.Frame(notebook, bg=PANEL, padx=13, pady=13)
        notebook.add(frame, text=title)
        return frame

    def _build_explorer(self, notebook):
        frame = self._tab(notebook, "NeoX Explorer")
        bar = tk.Frame(frame, bg=PANEL)
        bar.pack(fill="x", pady=(0, 8))
        self.table_query = tk.StringVar()
        entry = tk.Entry(bar, textvariable=self.table_query, bg=BG, fg=TEXT, insertbackground=TEXT,
                         relief="flat", highlightbackground=BORDER, highlightcolor=RED, highlightthickness=1)
        entry.pack(side="left", fill="x", expand=True, ipady=7)
        entry.bind("<Return>", lambda _event: self._load_tables())
        self.domain_var = tk.StringVar(value="")
        domain = ttk.Combobox(bar, textvariable=self.domain_var,
                              values=("", "weapons", "armor", "items_materials", "crafting", "mods_build_components"),
                              state="readonly", width=22)
        domain.pack(side="left", padx=(8, 0))
        self._button(bar, "FILTER TABLES", self._load_tables).pack(side="left", padx=(8, 0))

        body = tk.PanedWindow(frame, orient="horizontal", bg=BORDER, sashwidth=5)
        body.pack(fill="both", expand=True)
        table_panel = tk.Frame(body, bg=PANEL_2)
        record_panel = tk.Frame(body, bg=PANEL_2)
        field_panel = tk.Frame(body, bg=PANEL_2)
        body.add(table_panel, minsize=330, stretch="always")
        body.add(record_panel, minsize=300, stretch="always")
        body.add(field_panel, minsize=430, stretch="always")

        tk.Label(table_panel, text="STRUCTURED TABLES", bg=PANEL_2, fg=RED,
                 font=("Segoe UI", 9, "bold"), padx=8, pady=7).pack(anchor="w")
        self.tables = self._tree(table_panel, ("table", "layer", "records"), (310, 120, 80))
        self.tables.pack(fill="both", expand=True, padx=7, pady=(0, 7))
        self.tables.bind("<<TreeviewSelect>>", self._table_selected)

        record_header = tk.Frame(record_panel, bg=PANEL_2)
        record_header.pack(fill="x", padx=7, pady=7)
        tk.Label(record_header, text="RECORDS", bg=PANEL_2, fg=RED,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.layer_var = tk.StringVar(value="current")
        layer = ttk.Combobox(record_header, textvariable=self.layer_var, values=("current", "base"),
                             state="readonly", width=9)
        layer.pack(side="right")
        layer.bind("<<ComboboxSelected>>", lambda _event: self._load_records())
        self.record_query = tk.StringVar()
        record_entry = tk.Entry(record_panel, textvariable=self.record_query, bg=BG, fg=TEXT,
                                insertbackground=TEXT, relief="flat", highlightbackground=BORDER,
                                highlightcolor=RED, highlightthickness=1)
        record_entry.pack(fill="x", padx=7, pady=(0, 7), ipady=5)
        record_entry.bind("<Return>", lambda _event: self._load_records())
        self.records = self._tree(record_panel, ("id", "preview"), (110, 360))
        self.records.pack(fill="both", expand=True, padx=7, pady=(0, 7))
        self.records.bind("<<TreeviewSelect>>", self._record_selected)

        field_header = tk.Frame(field_panel, bg=PANEL_2)
        field_header.pack(fill="x", padx=7, pady=7)
        tk.Label(field_header, text="PROPERTIES", bg=PANEL_2, fg=RED,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self._button(field_header, "FIND EXACT REFERENCES", self._send_selected_value, muted=True).pack(side="right")
        self.fields = self._tree(field_panel, ("field", "type", "value"), (180, 80, 420))
        self.fields.pack(fill="both", expand=True, padx=7, pady=(0, 7))

    def _build_profiler(self, notebook):
        frame = self._tab(notebook, "Table Profiler")
        bar = tk.Frame(frame, bg=PANEL)
        bar.pack(fill="x")
        tk.Label(bar, text="PROFILE THE CURRENTLY SELECTED NEOX TABLE", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self._button(bar, "PROFILE TABLE", self._profile_selected).pack(side="right")
        self.profile_text = self._json_text(frame)
        self.profile_text.pack(fill="both", expand=True, pady=(10, 0))
        self.profile_text.insert("1.0", "Select a table in NeoX Explorer, then choose PROFILE TABLE.\n")

    def _build_source_finder(self, notebook):
        frame = self._tab(notebook, "Source Finder")
        bar = tk.Frame(frame, bg=PANEL)
        bar.pack(fill="x", pady=(0, 8))
        tk.Label(bar, text="WEAPON DESCRIPTION / RESEARCH REVIEW QUEUE", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self._button(bar, "REFRESH", self._load_source_finder, muted=True).pack(side="right")
        self.source_summary = tk.Label(bar, text="", bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        self.source_summary.pack(side="right", padx=12)
        split = tk.PanedWindow(frame, orient="horizontal", bg=BORDER, sashwidth=5)
        split.pack(fill="both", expand=True)
        left = tk.Frame(split, bg=PANEL_2)
        right = tk.Frame(split, bg=PANEL_2)
        split.add(left, minsize=520, stretch="always")
        split.add(right, minsize=480, stretch="always")
        self.source_rows = self._tree(left, ("state", "weapon", "category", "candidates"), (110, 280, 150, 90))
        self.source_rows.pack(fill="both", expand=True, padx=7, pady=7)
        self.source_rows.bind("<<TreeviewSelect>>", self._source_selected)
        self.source_detail = self._json_text(right)
        self.source_detail.pack(fill="both", expand=True, padx=7, pady=7)

    def _open_evidence(self):
        self.open_evidence_console(self.parent, self.output)

    def _load_tables(self):
        try:
            result = self.explorer.list_tables(self.table_query.get(), domain=self.domain_var.get())
            self.tables.delete(*self.tables.get_children())
            for row in result["tables"]:
                self.tables.insert("", "end", values=(
                    row["relative_path"], row["layer_status"],
                    max(row["base_records"], row["current_records"]),
                ))
        except Exception as error:
            messagebox.showerror("Dead Signal NeoX Explorer", str(error), parent=self.window)

    def _table_selected(self, _event=None):
        selected = self.tables.selection()
        if not selected:
            return
        values = self.tables.item(selected[0], "values")
        self.selected_table = str(values[0])
        summary = self.explorer.table_summary(self.selected_table)
        preferred = "current" if summary["current_present"] else "base"
        self.layer_var.set(preferred)
        self._load_records()

    def _load_records(self):
        if not self.selected_table:
            return
        try:
            self.selected_layer = self.layer_var.get()
            result = self.explorer.list_records(
                self.selected_table, layer=self.selected_layer,
                query=self.record_query.get(), limit=300,
            )
            self.records.delete(*self.records.get_children())
            self.fields.delete(*self.fields.get_children())
            for row in result["records"]:
                self.records.insert("", "end", values=(row["record_id"], row["preview"]))
        except Exception as error:
            messagebox.showerror("Dead Signal NeoX Explorer", str(error), parent=self.window)

    def _record_selected(self, _event=None):
        selected = self.records.selection()
        if not selected or not self.selected_table:
            return
        record_id = str(self.records.item(selected[0], "values")[0])
        try:
            result = self.explorer.record(self.selected_table, record_id, layer=self.selected_layer)
            self.fields.delete(*self.fields.get_children())
            for field in result["fields"]:
                self.fields.insert("", "end", values=(field["json_pointer"], field["value_type"], str(field["value"])))
        except Exception as error:
            messagebox.showerror("Dead Signal NeoX Explorer", str(error), parent=self.window)

    def _send_selected_value(self):
        selected = self.fields.selection()
        if not selected:
            messagebox.showinfo("Exact References", "Select one property value first.", parent=self.window)
            return
        value = str(self.fields.item(selected[0], "values")[2])
        self._open_evidence()
        messagebox.showinfo(
            "Exact References",
            f"Exact Evidence Console opened. Search this exact value:\n\n{value}",
            parent=self.window,
        )

    def _profile_selected(self):
        if not self.selected_table:
            messagebox.showinfo("Dead Signal Table Profiler", "Select a table in NeoX Explorer first.", parent=self.window)
            return
        try:
            summary = self.explorer.table_summary(self.selected_table)
            base_profile = None
            current_profile = None
            if summary["base_present"]:
                base_profile = profile_table(self.explorer.base / self.selected_table, layer="base", table=self.selected_table)
            if summary["current_present"]:
                current_profile = profile_table(self.explorer.current / self.selected_table, layer="current", table=self.selected_table)
            payload = {"table": self.selected_table, "base": base_profile, "current": current_profile}
            if base_profile and current_profile:
                payload["diff"] = compare_profiles(base_profile, current_profile)
            self.profile_text.delete("1.0", "end")
            self.profile_text.insert("1.0", json.dumps(payload, ensure_ascii=False, indent=2))
        except Exception as error:
            messagebox.showerror("Dead Signal Table Profiler", str(error), parent=self.window)

    def _load_source_finder(self):
        path = self.output / "published" / "reports" / "dead-signal-source-finder.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            payload = {"weapons": [], "record_counts": {}}
        self.source_payload = payload
        if hasattr(self, "source_rows"):
            self.source_rows.delete(*self.source_rows.get_children())
            for index, row in enumerate(payload.get("weapons") or []):
                self.source_rows.insert("", "end", iid=str(index), values=(
                    row.get("state"), row.get("name"), row.get("category"), row.get("candidate_count"),
                ))
        counts = payload.get("record_counts") or {}
        if hasattr(self, "source_summary"):
            self.source_summary.configure(
                text=f"Reviewable {counts.get('reviewable_candidates', 0)}  /  Conflicts {counts.get('conflict_candidates', 0)}"
            )

    def _source_selected(self, _event=None):
        selected = self.source_rows.selection()
        if not selected:
            return
        try:
            row = (self.source_payload.get("weapons") or [])[int(selected[0])]
        except (ValueError, IndexError):
            return
        self.source_detail.delete("1.0", "end")
        self.source_detail.insert("1.0", json.dumps(row, ensure_ascii=False, indent=2))


def open_data_intelligence(parent: tk.Misc, output: Path, open_evidence_console) -> DataIntelligenceWindow:
    return DataIntelligenceWindow(parent, output, open_evidence_console)
