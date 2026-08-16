"""Dead Signal Data Intelligence Compiler UI tab."""

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

from dead_signal_intelligence_compiler import compile_intelligence, compile_weapon_description_ui_trace
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
    if hours:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class CompilerTab:
    def __init__(self, notebook: ttk.Notebook, host):
        self.host = host
        self.output = Path(host.output).expanduser().resolve()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.last_bundle: Path | None = None
        self.started_at: float | None = None
        self.last_activity_at: float | None = None
        self.activity_count = 0
        self.current_stage = "Ready"
        self.current_detail = "Waiting for compiler start"
        self.active_mode = ""

        self.frame = tk.Frame(notebook, bg=PANEL, padx=18, pady=18)
        notebook.add(self.frame, text="Compiler")
        self.status_var = tk.StringVar(value="Ready to compile the completed snapshot")
        self.detail_var = tk.StringVar(value=self.current_detail)
        self.elapsed_var = tk.StringVar(value="Elapsed 00:00")
        self.heartbeat_var = tk.StringVar(value="Idle")
        self.progress_var = tk.IntVar(value=0)
        self.percent_var = tk.StringVar(value="0%")
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
                "Use the fast Weapon UI trace for the current description investigation, or run the complete "
                "Data Intelligence suite. Heavy unchanged research stages are cached. No game mining is performed."
            ),
            bg=PANEL,
            fg=MUTED,
            justify="left",
            wraplength=1000,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 16))

        actions = tk.Frame(self.frame, bg=PANEL)
        actions.pack(fill="x")
        self.trace_button = tk.Button(
            actions,
            text="TRACE WEAPON UI DESCRIPTION",
            command=self._start_ui_trace,
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
        self.trace_button.pack(side="left")
        self.run_button = tk.Button(
            actions,
            text="COMPILE DATA INTELLIGENCE",
            command=self._start,
            bg=PANEL_2,
            activebackground=BORDER,
            fg=TEXT,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            padx=20,
            pady=10,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )
        self.run_button.pack(side="left", padx=(10, 0))
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

        stage_row = tk.Frame(status, bg=PANEL_2)
        stage_row.pack(fill="x")
        tk.Label(stage_row, textvariable=self.status_var, bg=PANEL_2, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(stage_row, textvariable=self.percent_var, bg=PANEL_2, fg=RED,
                 font=("Segoe UI", 10, "bold")).pack(side="right")

        tk.Label(
            status,
            textvariable=self.detail_var,
            bg=PANEL_2,
            fg="#d0d6dc",
            anchor="w",
            justify="left",
            font=("Cascadia Mono", 9),
        ).pack(fill="x", pady=(7, 0))

        telemetry = tk.Frame(status, bg=PANEL_2)
        telemetry.pack(fill="x", pady=(6, 0))
        tk.Label(telemetry, textvariable=self.elapsed_var, bg=PANEL_2, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="left")
        tk.Label(telemetry, textvariable=self.heartbeat_var, bg=PANEL_2, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="right")

        ttk.Progressbar(status, variable=self.progress_var, maximum=100).pack(fill="x", pady=(9, 0))

        tk.Label(
            self.frame,
            text="LIVE ACTIVITY",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w", pady=(3, 4))

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
        self._append("Fast UI trace: exact prototype_id -> weapon_prototype_data -> prototype_desc -> English translation.")
        self._append("Full Compiler: complete Data Intelligence suite; unchanged heavy stages are reused from cache.")

    def _append(self, message: object):
        self.log.configure(state="normal")
        self.log.insert("end", str(message).rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _prepare_run(self, mode: str, stage: str, detail: str):
        now = time.monotonic()
        self.active_mode = mode
        self.started_at = now
        self.last_activity_at = now
        self.activity_count = 0
        self.current_stage = stage
        self.current_detail = detail
        self.run_button.configure(state="disabled")
        self.trace_button.configure(state="disabled")
        self.progress_var.set(0)
        self.percent_var.set("0%")
        self.status_var.set(stage)
        self.detail_var.set(detail)
        self.elapsed_var.set("Elapsed 00:00")
        self.heartbeat_var.set("Working • activity 0")

    def _start(self):
        if self.worker and self.worker.is_alive():
            return
        self._prepare_run("full", "Starting Data Intelligence compiler", "Resolving completed Miner snapshot")
        self._append("\n=== DATA INTELLIGENCE COMPILE ===")

        def worker():
            try:
                result = compile_intelligence(
                    self.output,
                    log=lambda value: self.events.put(("log", value)),
                    progress=lambda value, label: self.events.put(("progress", (value, label))),
                    activity=lambda value: self.events.put(("activity", value)),
                )
                self.events.put(("complete", result))
            except Exception as error:
                self.events.put(("error", f"{type(error).__name__}: {error}"))

        self.worker = threading.Thread(target=worker, name="dead-signal-intelligence-compiler", daemon=True)
        self.worker.start()

    def _start_ui_trace(self):
        if self.worker and self.worker.is_alive():
            return
        self._prepare_run("ui-trace", "Starting Weapon UI description trace", "Opening exact Weapon prototype source")
        self._append("\n=== WEAPON UI DESCRIPTION TRACE ===")

        def worker():
            try:
                result = compile_weapon_description_ui_trace(
                    self.output,
                    log=lambda value: self.events.put(("log", value)),
                    progress=lambda value, label: self.events.put(("progress", (value, label))),
                    activity=lambda value: self.events.put(("activity", value)),
                )
                self.events.put(("complete", result))
            except Exception as error:
                self.events.put(("error", f"{type(error).__name__}: {error}"))

        self.worker = threading.Thread(target=worker, name="dead-signal-weapon-ui-trace", daemon=True)
        self.worker.start()

    def _refresh_heartbeat(self):
        if not (self.worker and self.worker.is_alive()) or self.started_at is None:
            return
        now = time.monotonic()
        elapsed = now - self.started_at
        idle_for = now - (self.last_activity_at or self.started_at)
        self.elapsed_var.set(f"Elapsed {_format_elapsed(elapsed)}")
        if idle_for < 2:
            pulse = "Working • live"
        elif idle_for < 10:
            pulse = f"Working • {int(idle_for)}s since detail"
        else:
            pulse = f"Still working • {int(idle_for)}s since detail"
        self.heartbeat_var.set(f"{pulse} • activity {self.activity_count}")

    def _enable_actions(self):
        self.run_button.configure(state="normal")
        self.trace_button.configure(state="normal")

    def _poll(self):
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "log":
                    self._append(payload)
                elif event == "activity":
                    self.activity_count += 1
                    self.last_activity_at = time.monotonic()
                    self.current_detail = str(payload)
                    self.detail_var.set(self.current_detail)
                    self._append(f"> {payload}")
                elif event == "progress":
                    value, label = payload  # type: ignore[misc]
                    self.progress_var.set(int(value))
                    self.percent_var.set(f"{int(value)}%")
                    self.current_stage = str(label)
                    self.status_var.set(self.current_stage)
                elif event == "complete":
                    result = payload  # type: ignore[assignment]
                    mode = self.active_mode
                    self.worker = None
                    self.progress_var.set(100)
                    self.percent_var.set("100%")
                    if mode == "ui-trace":
                        self.status_var.set("Weapon UI description trace ready")
                        self.detail_var.set("Targeted prototype/consumer trace complete")
                    else:
                        self.status_var.set("Data Intelligence bundle ready")
                        self.detail_var.set("All extensions completed and bundle compiled")
                    if self.started_at is not None:
                        self.elapsed_var.set(f"Elapsed {_format_elapsed(time.monotonic() - self.started_at)}")
                    self.heartbeat_var.set(f"Complete • {self.activity_count} activity events")
                    self._enable_actions()
                    bundle = Path(str(result.get("bundle")))
                    self.last_bundle = bundle
                    self._append(f"Bundle: {bundle}")
                    counts = result.get("record_counts") or {}
                    if mode == "ui-trace":
                        self._append(f"Prototype description fields: {counts.get('prototype_desc_fields_found', 0)}")
                        self._append(f"Consistent translations: {counts.get('consistent_resolutions', 0)}")
                        self._append(f"Consumer-backed candidates: {counts.get('consumer_backed_candidates', 0)}")
                        title = "Dead Signal Weapon UI Trace"
                        body = f"Targeted Weapon UI trace complete.\n\nBundle ready at:\n{bundle}"
                    else:
                        self._append(f"Profiled tables: {counts.get('profiled_tables', 0)}")
                        self._append(f"UI consumer candidates: {counts.get('ui_consumer_candidates', 0)}")
                        self._append(f"Description hotspots: {counts.get('description_hotspots', 0)}")
                        self._append(f"Description leads: {counts.get('description_leads', 0)}")
                        title = "Dead Signal Data Intelligence"
                        body = f"Compilation complete.\n\nBundle ready at:\n{bundle}"
                    messagebox.showinfo(title, body, parent=self.host.window)
                    self.active_mode = ""
                elif event == "error":
                    self.worker = None
                    self._enable_actions()
                    self.status_var.set("Compilation stopped — see details")
                    self.detail_var.set(str(payload))
                    if self.started_at is not None:
                        self.elapsed_var.set(f"Elapsed {_format_elapsed(time.monotonic() - self.started_at)}")
                    self.heartbeat_var.set("Stopped")
                    self._append(payload)
                    messagebox.showerror("Dead Signal Data Intelligence", str(payload), parent=self.host.window)
                    self.active_mode = ""
        except queue.Empty:
            pass
        self._refresh_heartbeat()
        if self.frame.winfo_exists():
            self.frame.after(250, self._poll)


def install_compiler_tab(notebook: ttk.Notebook, host) -> CompilerTab:
    tab = CompilerTab(notebook, host)
    host.compiler_tab = tab
    return tab