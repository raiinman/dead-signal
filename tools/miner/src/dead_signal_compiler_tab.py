"""Dead Signal Data Intelligence Compiler UI tab."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from dead_signal_intelligence_compiler import compile_intelligence
from dead_signal_intelligence_window import BG, BORDER, MUTED, PANEL, PANEL_2, RED, TEXT


def _open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class CompilerTab:
    def __init__(self, notebook: ttk.Notebook, host):
        self.host = host
        self.output = Path(host.output).expanduser().resolve()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.last_bundle: Path | None = None

        self.frame = tk.Frame(notebook, bg=PANEL, padx=18, pady=18)
        notebook.add(self.frame, text="Compiler")
        self.status_var = tk.StringVar(value="Ready to compile the completed snapshot")
        self.progress_var = tk.IntVar(value=0)
        self._build()
        self.frame.after(100, self._poll)

    def _build(self):
        tk.Label(
            self.frame,
            text="DEAD SIGNAL INTELLIGENCE COMPILER",
            bg=PANEL,
            fg=RED,
            font=("Bahnschrift SemiCondensed", 18, "bold"),
        ).pack(anchor="w")
        tk.Label(
            self.frame,
            text=(
                "Re-run every Data Intelligence extension against the completed local snapshot. "
                "No game mining is performed and no player-facing dataset is published."
            ),
            bg=PANEL,
            fg=MUTED,
            justify="left",
            wraplength=1000,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 16))

        actions = tk.Frame(self.frame, bg=PANEL)
        actions.pack(fill="x")
        self.run_button = tk.Button(
            actions,
            text="COMPILE DATA INTELLIGENCE",
            command=self._start,
            bg=RED,
            activebackground="#ff4047",
            fg="white",
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=20,
            pady=10,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )
        self.run_button.pack(side="left")
        self.open_button = tk.Button(
            actions,
            text="OPEN INTELLIGENCE BUNDLES",
            command=lambda: _open_folder(self.output / "intelligence"),
            bg=PANEL_2,
            activebackground=BORDER,
            fg=TEXT,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            padx=16,
            pady=10,
            font=("Segoe UI", 9, "bold"),
        )
        self.open_button.pack(side="left", padx=(10, 0))

        status = tk.Frame(self.frame, bg=PANEL_2, highlightbackground=BORDER, highlightthickness=1, padx=14, pady=13)
        status.pack(fill="x", pady=(18, 10))
        tk.Label(status, textvariable=self.status_var, bg=PANEL_2, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Progressbar(status, variable=self.progress_var, maximum=100).pack(fill="x", pady=(9, 0))

        self.log = tk.Text(
            self.frame,
            bg=BG,
            fg="#c9d0d6",
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            padx=12,
            pady=10,
            font=("Cascadia Mono", 9),
            wrap="word",
            state="disabled",
        )
        self.log.pack(fill="both", expand=True)
        self._append("Compiler is independent of the game harvest. Existing snapshots can be reprocessed at any time.")

    def _append(self, message: object):
        self.log.configure(state="normal")
        self.log.insert("end", str(message).rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _start(self):
        if self.worker and self.worker.is_alive():
            return
        self.run_button.configure(state="disabled")
        self.progress_var.set(0)
        self.status_var.set("Starting Data Intelligence compiler")
        self._append("\n=== DATA INTELLIGENCE COMPILE ===")

        def worker():
            try:
                result = compile_intelligence(
                    self.output,
                    log=lambda value: self.events.put(("log", value)),
                    progress=lambda value, label: self.events.put(("progress", (value, label))),
                )
                self.events.put(("complete", result))
            except Exception as error:
                self.events.put(("error", f"{type(error).__name__}: {error}"))

        self.worker = threading.Thread(target=worker, name="dead-signal-intelligence-compiler", daemon=True)
        self.worker.start()

    def _poll(self):
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "log":
                    self._append(payload)
                elif event == "progress":
                    value, label = payload  # type: ignore[misc]
                    self.progress_var.set(int(value))
                    self.status_var.set(str(label))
                elif event == "complete":
                    result = payload  # type: ignore[assignment]
                    self.progress_var.set(100)
                    self.status_var.set("Data Intelligence bundle ready")
                    self.run_button.configure(state="normal")
                    bundle = Path(str(result.get("bundle")))
                    self.last_bundle = bundle
                    self._append(f"Bundle: {bundle}")
                    counts = result.get("record_counts") or {}
                    self._append(f"Profiled tables: {counts.get('profiled_tables', 0)}")
                    self._append(f"Description hotspots: {counts.get('description_hotspots', 0)}")
                    self._append(f"Description leads: {counts.get('description_leads', 0)}")
                    messagebox.showinfo(
                        "Dead Signal Data Intelligence",
                        f"Compilation complete.\n\nBundle ready at:\n{bundle}",
                        parent=self.host.window,
                    )
                elif event == "error":
                    self.run_button.configure(state="normal")
                    self.status_var.set("Compilation stopped — see details")
                    self._append(payload)
                    messagebox.showerror("Dead Signal Data Intelligence", str(payload), parent=self.host.window)
        except queue.Empty:
            pass
        if self.frame.winfo_exists():
            self.frame.after(100, self._poll)


def install_compiler_tab(notebook: ttk.Notebook, host) -> CompilerTab:
    tab = CompilerTab(notebook, host)
    host.compiler_tab = tab
    return tab
