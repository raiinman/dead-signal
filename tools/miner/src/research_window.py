"""Tk research console window backed by :mod:`research_console`."""

from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from research_console import FILTERS, ResearchConsole


BG = "#090b0d"
PANEL = "#111519"
TEXT = "#eef1f4"
MUTED = "#9aa3ac"
RED = "#e52b32"
BORDER = "#2a3138"


class ResearchWindow:
    def __init__(self, parent: tk.Misc, output: Path):
        self.parent = parent
        self.service = ResearchConsole(output)
        self.window = tk.Toplevel(parent)
        self.window.title("Dead Signal Miner / Research Console")
        self.window.geometry("1280x820")
        self.window.minsize(980, 680)
        self.window.configure(bg=BG)
        self.last_evidence: dict = {}
        self._build()

    @staticmethod
    def _button(parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=RED, activebackground="#ff4047",
                         fg="white", activeforeground="white", relief="flat", bd=0,
                         padx=14, pady=7, font=("Segoe UI", 9, "bold"), cursor="hand2")

    @staticmethod
    def _text(parent):
        return tk.Text(parent, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                       padx=12, pady=10, font=("Cascadia Mono", 9), wrap="word")

    def _build(self):
        header = tk.Frame(self.window, bg=BG, padx=20, pady=14)
        header.pack(fill="x")
        tk.Label(header, text="RESEARCH CONSOLE", bg=BG, fg=TEXT,
                 font=("Bahnschrift SemiCondensed", 22, "bold")).pack(side="left")
        tk.Label(header, text="READ-ONLY SNAPSHOT WORKSTATION", bg=BG, fg=RED,
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=14, pady=(8, 0))
        tk.Label(header, text="Exact evidence is authoritative. Related results are leads only.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="right", pady=(8, 0))

        style = ttk.Style(self.window)
        style.configure("Research.TNotebook", background=BG, borderwidth=0)
        style.configure("Research.TNotebook.Tab", background=PANEL, foreground=TEXT, padding=(12, 7))
        style.map("Research.TNotebook.Tab", background=[("selected", RED)], foreground=[("selected", "white")])
        notebook = ttk.Notebook(self.window, style="Research.TNotebook")
        notebook.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self._build_search(notebook)
        self._build_investigator(notebook)
        self._build_queue(notebook)
        self._build_diff(notebook)
        self._build_notes_integrity(notebook)

    def _tab(self, notebook, title):
        frame = tk.Frame(notebook, bg=PANEL, padx=14, pady=14)
        notebook.add(frame, text=title)
        return frame

    def _build_search(self, notebook):
        frame = self._tab(notebook, "Evidence Search")
        row = tk.Frame(frame, bg=PANEL)
        row.pack(fill="x")
        self.query = tk.StringVar()
        entry = tk.Entry(row, textvariable=self.query, bg=BG, fg=TEXT, insertbackground=TEXT,
                         relief="flat", highlightbackground=BORDER, highlightcolor=RED,
                         highlightthickness=1, font=("Segoe UI", 11))
        entry.pack(side="left", fill="x", expand=True, ipady=7)
        entry.bind("<Return>", lambda _event: self._search(False))
        self._button(row, "EXACT SEARCH", lambda: self._search(False)).pack(side="left", padx=(8, 0))
        related = self._button(row, "RELATED SEARCH", lambda: self._search(True))
        related.configure(bg="#4b5158")
        related.pack(side="left", padx=(8, 0))
        filters = tk.Frame(frame, bg=PANEL)
        filters.pack(fill="x", pady=8)
        self.filter_vars = {}
        for label in FILTERS:
            var = tk.BooleanVar(value=True)
            self.filter_vars[label] = var
            tk.Checkbutton(filters, text=label, variable=var, bg=PANEL, fg=TEXT,
                           activebackground=PANEL, activeforeground=TEXT, selectcolor=BG).pack(side="left", padx=(0, 12))
        tk.Label(filters, text="Related mode never establishes identity.", bg=PANEL, fg=MUTED).pack(side="right")
        columns = ("mode", "category", "source", "field", "value")
        self.results = ttk.Treeview(frame, columns=columns, show="headings")
        for name, width in (("mode", 90), ("category", 110), ("source", 260), ("field", 150), ("value", 420)):
            self.results.heading(name, text=name.upper())
            self.results.column(name, width=width, stretch=True)
        self.results.pack(fill="both", expand=True)
        self.results.bind("<Button-3>", self._search_menu)

    def _search(self, related):
        try:
            selected = [name for name, var in self.filter_vars.items() if var.get()]
            self.last_evidence = self.service.search(self.query.get(), selected, related=related)
            self.results.delete(*self.results.get_children())
            for row in self.last_evidence["results"]:
                self.results.insert("", "end", values=(row.get("match"), row.get("category") or "Tables",
                                    row.get("table") or row.get("source"), row.get("field"), row.get("value") or self.query.get()))
        except Exception as error:
            messagebox.showerror("Research Search", str(error), parent=self.window)

    def _search_menu(self, event):
        item = self.results.identify_row(event.y)
        if not item:
            return
        self.results.selection_set(item)
        values = self.results.item(item, "values")
        value = values[4] if len(values) > 4 else ""
        menu = tk.Menu(self.window, tearoff=False)
        menu.add_command(label="Find References (exact ID)", command=lambda: self._reverse_lookup(value))
        menu.tk_popup(event.x_root, event.y_root)

    def _reverse_lookup(self, value):
        self.query.set(value)
        self._search(False)

    def _build_investigator(self, notebook):
        frame = self._tab(notebook, "Weapon Investigator / Graph")
        row = tk.Frame(frame, bg=PANEL)
        row.pack(fill="x")
        self.weapon_var = tk.StringVar()
        choices = [f"{row.get('name')}  [{row.get('canonical_id') or row.get('blueprint_id')}]" for row in self.service.weapons()]
        box = ttk.Combobox(row, textvariable=self.weapon_var, values=choices, state="normal")
        box.pack(side="left", fill="x", expand=True, ipady=4)
        self._button(row, "INVESTIGATE", self._investigate).pack(side="left", padx=(8, 0))
        self._button(row, "EXPORT EVIDENCE", self._export).pack(side="left", padx=(8, 0))
        self.investigation = self._text(frame)
        self.investigation.pack(fill="both", expand=True, pady=(10, 0))

    def _investigate(self):
        identity = self.weapon_var.get().strip()
        if identity.endswith("]") and "[" in identity:
            identity = identity.rsplit("[", 1)[1][:-1]
        try:
            self.last_evidence = self.service.investigate_weapon(identity)
            self.investigation.delete("1.0", "end")
            self.investigation.insert("1.0", json.dumps(self.last_evidence, ensure_ascii=False, indent=2))
        except Exception as error:
            messagebox.showerror("Weapon Investigator", str(error), parent=self.window)

    def _build_queue(self, notebook):
        frame = self._tab(notebook, "Unresolved Queue")
        bar = tk.Frame(frame, bg=PANEL)
        bar.pack(fill="x")
        self._button(bar, "REFRESH", self._queue).pack(side="left")
        self.queue_text = self._text(frame)
        self.queue_text.pack(fill="both", expand=True, pady=(10, 0))
        self._queue()

    def _queue(self):
        self.last_evidence = self.service.unresolved_queue()
        self.queue_text.delete("1.0", "end")
        for group, rows in self.last_evidence["groups"].items():
            self.queue_text.insert("end", f"{group.upper()}  ({len(rows)})\n")
            for row in rows:
                self.queue_text.insert("end", f"  • {row.get('name') or row.get('identity')} — {row.get('status') or row.get('variants')}\n")
            self.queue_text.insert("end", "\n")

    def _build_diff(self, notebook):
        frame = self._tab(notebook, "Snapshot Diff")
        self.before = tk.StringVar()
        self.after = tk.StringVar(value=str(self.service.published))
        for label, variable in (("BEFORE SNAPSHOT/PUBLISHED", self.before), ("AFTER SNAPSHOT/PUBLISHED", self.after)):
            row = tk.Frame(frame, bg=PANEL)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, width=28, anchor="w", bg=PANEL, fg=MUTED).pack(side="left")
            tk.Entry(row, textvariable=variable, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat").pack(side="left", fill="x", expand=True, ipady=6)
            self._button(row, "BROWSE", lambda var=variable: self._browse(var)).pack(side="left", padx=(8, 0))
        self._button(frame, "COMPARE", self._diff).pack(anchor="w", pady=8)
        self.diff_text = self._text(frame)
        self.diff_text.pack(fill="both", expand=True)

    def _browse(self, variable):
        value = filedialog.askdirectory(initialdir=str(self.service.output), parent=self.window)
        if value:
            variable.set(value)

    def _diff(self):
        try:
            self.last_evidence = self.service.diff_snapshots(self.before.get(), self.after.get())
            self.diff_text.delete("1.0", "end")
            self.diff_text.insert("1.0", json.dumps(self.last_evidence, indent=2))
        except Exception as error:
            messagebox.showerror("Snapshot Diff", str(error), parent=self.window)

    def _build_notes_integrity(self, notebook):
        frame = self._tab(notebook, "Notes / Integrity")
        split = tk.PanedWindow(frame, orient="horizontal", bg=PANEL, sashwidth=5)
        split.pack(fill="both", expand=True)
        notes = tk.Frame(split, bg=PANEL)
        integrity = tk.Frame(split, bg=PANEL)
        split.add(notes, stretch="always")
        split.add(integrity, stretch="always")
        tk.Label(notes, text="RESEARCH BOOKMARK / NOTE", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.note_target = tk.StringVar()
        tk.Entry(notes, textvariable=self.note_target, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat").pack(fill="x", pady=6, ipady=6)
        self.note_text = self._text(notes)
        self.note_text.pack(fill="both", expand=True)
        self._button(notes, "SAVE NOTE", self._save_note).pack(anchor="w", pady=(8, 0))
        tk.Label(integrity, text="INTEGRITY & COVERAGE", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.integrity_text = self._text(integrity)
        self.integrity_text.pack(fill="both", expand=True, pady=(6, 0))
        self.integrity_text.insert("1.0", json.dumps(self.service.integrity_dashboard(), indent=2))

    def _save_note(self):
        try:
            item = self.service.save_note(self.note_target.get(), self.note_text.get("1.0", "end"))
            messagebox.showinfo("Research Notes", f"Saved {item['id']} locally.", parent=self.window)
        except Exception as error:
            messagebox.showerror("Research Notes", str(error), parent=self.window)

    def _export(self):
        if not self.last_evidence:
            messagebox.showinfo("Evidence Export", "Run a search or investigation first.", parent=self.window)
            return
        try:
            path = self.service.export_evidence(self.last_evidence)
            messagebox.showinfo("Evidence Export", f"Saved compact research evidence to:\n{path}", parent=self.window)
        except Exception as error:
            messagebox.showerror("Evidence Export", str(error), parent=self.window)


def open_research_console(parent: tk.Misc, output: Path) -> ResearchWindow:
    return ResearchWindow(parent, output)

