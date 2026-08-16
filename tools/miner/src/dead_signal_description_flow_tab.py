"""Dead Signal offline Weapon Description data-flow trace UI."""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from dead_signal_description_trace_compiler import compile_description_dataflow_trace
from dead_signal_intelligence_window import BG, BORDER, MUTED, PANEL, PANEL_2, RED, TEXT


def _open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def _format_elapsed(seconds: float) -> str:
    seconds = max(0, int(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


class DescriptionFlowTab:
    def __init__(self, notebook: ttk.Notebook, host):
        self.host = host
        self.output = Path(host.output).expanduser().resolve()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.started_at: float | None = None
        self.last_activity_at: float | None = None
        self.activity_count = 0

        self.frame = tk.Frame(notebook, bg=PANEL, padx=18, pady=18)
        notebook.add(self.frame, text="Description Flow")
        self.status_var = tk.StringVar(value="Ready for offline static trace")
        self.detail_var = tk.StringVar(value="No live game process access is used")
        self.elapsed_var = tk.StringVar(value="Elapsed 00:00")
        self.heartbeat_var = tk.StringVar(value="Idle")
        self.progress_var = tk.IntVar(value=0)
        self.percent_var = tk.StringVar(value="0%")
        self._build()
        self.frame.after(100, self._poll)

    def _build(self):
        tk.Label(
            self.frame,
            text="WEAPON DESCRIPTION / STATIC DATA FLOW",
            bg=PANEL,
            fg=RED,
            font=("Bahnschrift SemiCondensed", 18, "bold"),
        ).pack(anchor="w")
        tk.Label(
            self.frame,
            text=(
                "Trace the extracted client code around ItemDataTools.get_weapon_item_data, get_item_desc_text, "
                "prototype_desc, and BluePrintHelper without launching, attaching to, debugging, injecting, or reading "
                "memory from the live game process. Game bytecode is never executed."
            ),
            bg=PANEL,
            fg=MUTED,
            justify="left",
            wraplength=1000,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 16))

        safety = tk.Frame(self.frame, bg=PANEL_2, highlightbackground=BORDER, highlightthickness=1, padx=14, pady=12)
        safety.pack(fill="x", pady=(0, 14))
        tk.Label(safety, text="OFFLINE-ONLY SAFETY BOUNDARY", bg=PANEL_2, fg=TEXT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(
            safety,
            text=(
                "Reads only already-extracted PYC files referenced by the completed Miner snapshot. "
                "No process handle • no DLL injection • no debugger • no hooks • no memory reads • no anti-cheat interaction."
            ),
            bg=PANEL_2,
            fg=MUTED,
            justify="left",
            wraplength=1000,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(4, 0))

        actions = tk.Frame(self.frame, bg=PANEL)
        actions.pack(fill="x")
        self.run_button = tk.Button(
            actions,
            text="TRACE DESCRIPTION DATA FLOW",
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
        tk.Button(
            actions,
            text="OPEN TRACE BUNDLES",
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
        ).pack(side="left", padx=(10, 0))

        status = tk.Frame(self.frame, bg=PANEL_2, highlightbackground=BORDER, highlightthickness=1, padx=14, pady=13)
        status.pack(fill="x", pady=(18, 10))
        top = tk.Frame(status, bg=PANEL_2)
        top.pack(fill="x")
        tk.Label(top, textvariable=self.status_var, bg=PANEL_2, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(top, textvariable=self.percent_var, bg=PANEL_2, fg=RED,
                 font=("Segoe UI", 10, "bold")).pack(side="right")
        tk.Label(status, textvariable=self.detail_var, bg=PANEL_2, fg="#d0d6dc",
                 anchor="w", justify="left", font=("Cascadia Mono", 9)).pack(fill="x", pady=(7, 0))
        telemetry = tk.Frame(status, bg=PANEL_2)
        telemetry.pack(fill="x", pady=(6, 0))
        tk.Label(telemetry, textvariable=self.elapsed_var, bg=PANEL_2, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="left")
        tk.Label(telemetry, textvariable=self.heartbeat_var, bg=PANEL_2, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="right")
        ttk.Progressbar(status, variable=self.progress_var, maximum=100).pack(fill="x", pady=(9, 0))

        tk.Label(self.frame, text="LIVE ACTIVITY", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(3, 4))
        self.log = tk.Text(
            self.frame, bg=BG, fg="#c9d0d6", insertbackground=TEXT, relief="flat", bd=0,
            padx=12, pady=10, font=("Cascadia Mono", 9), wrap="word", state="disabled",
        )
        self.log.pack(fill="both", expand=True)
        self._append("This trace is intentionally independent of the live Once Human process.")

    def _append(self, message: object):
        self.log.configure(state="normal")
        self.log.insert("end", str(message).rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _start(self):
        if self.worker and self.worker.is_alive():
            return
        now = time.monotonic()
        self.started_at = now
        self.last_activity_at = now
        self.activity_count = 0
        self.run_button.configure(state="disabled")
        self.progress_var.set(0)
        self.percent_var.set("0%")
        self.status_var.set("Starting static description trace")
        self.detail_var.set("Resolving completed snapshot")
        self.elapsed_var.set("Elapsed 00:00")
        self.heartbeat_var.set("Working • activity 0")
        self._append("\n=== OFFLINE DESCRIPTION DATA FLOW ===")

        def worker():
            try:
                result = compile_description_dataflow_trace(
                    self.output,
                    log=lambda value: self.events.put(("log", value)),
                    progress=lambda value, label: self.events.put(("progress", (value, label))),
                    activity=lambda value: self.events.put(("activity", value)),
                )
                self.events.put(("complete", result))
            except Exception as error:
                self.events.put(("error", f"{type(error).__name__}: {error}"))

        self.worker = threading.Thread(target=worker, name="dead-signal-description-dataflow", daemon=True)
        self.worker.start()

    def _refresh_heartbeat(self):
        if not (self.worker and self.worker.is_alive()) or self.started_at is None:
            return
        now = time.monotonic()
        elapsed = now - self.started_at
        idle_for = now - (self.last_activity_at or self.started_at)
        self.elapsed_var.set(f"Elapsed {_format_elapsed(elapsed)}")
        pulse = "Working • live" if idle_for < 2 else f"Working • {int(idle_for)}s since detail"
        self.heartbeat_var.set(f"{pulse} • activity {self.activity_count}")

    def _poll(self):
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "log":
                    self._append(payload)
                elif event == "activity":
                    self.activity_count += 1
                    self.last_activity_at = time.monotonic()
                    self.detail_var.set(str(payload))
                    self._append(f"> {payload}")
                elif event == "progress":
                    value, label = payload  # type: ignore[misc]
                    self.progress_var.set(int(value))
                    self.percent_var.set(f"{int(value)}%")
                    self.status_var.set(str(label))
                elif event == "complete":
                    result = payload  # type: ignore[assignment]
                    self.worker = None
                    self.progress_var.set(100)
                    self.percent_var.set("100%")
                    self.status_var.set("Description Data Flow ready")
                    counts = result.get("record_counts") or {}
                    self.detail_var.set(
                        f"{counts.get('selected_code_objects', 0)} code objects • "
                        f"{counts.get('prototype_desc_get_item_desc_text_cooccurrences', 0)} direct co-occurrence signals"
                    )
                    if self.started_at is not None:
                        self.elapsed_var.set(f"Elapsed {_format_elapsed(time.monotonic() - self.started_at)}")
                    self.heartbeat_var.set(f"Complete • {self.activity_count} activity events")
                    self.run_button.configure(state="normal")
                    bundle = Path(str(result.get("bundle")))
                    self._append(f"Bundle: {bundle}")
                    messagebox.showinfo(
                        "Dead Signal Description Data Flow",
                        f"Offline static trace complete.\n\nBundle ready at:\n{bundle}",
                        parent=self.host.window,
                    )
                elif event == "error":
                    self.worker = None
                    self.run_button.configure(state="normal")
                    self.status_var.set("Trace stopped — see details")
                    self.detail_var.set(str(payload))
                    if self.started_at is not None:
                        self.elapsed_var.set(f"Elapsed {_format_elapsed(time.monotonic() - self.started_at)}")
                    self.heartbeat_var.set("Stopped")
                    self._append(payload)
                    messagebox.showerror("Dead Signal Description Data Flow", str(payload), parent=self.host.window)
        except queue.Empty:
            pass
        self._refresh_heartbeat()
        if self.frame.winfo_exists():
            self.frame.after(250, self._poll)


def install_description_flow_tab(notebook: ttk.Notebook, host) -> DescriptionFlowTab:
    tab = DescriptionFlowTab(notebook, host)
    host.description_flow_tab = tab
    return tab
