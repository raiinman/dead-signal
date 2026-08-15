"""Unified Dead Signal Data Intelligence workspace."""

from __future__ import annotations

from pathlib import Path
from tkinter import ttk

from dead_signal_compiler_tab import install_compiler_tab
from dead_signal_discovery_tab import install_discovery_tab
from dead_signal_intelligence_advanced import install_advanced_tabs
from dead_signal_intelligence_window import DataIntelligenceWindow
from dead_signal_verification_tab import install_verification_tab


class DeadSignalDataIntelligence(DataIntelligenceWindow):
    """Complete Dead Signal research workspace over one local Miner snapshot."""

    def _build(self):
        super()._build()
        notebook = next(
            (child for child in self.window.winfo_children() if isinstance(child, ttk.Notebook)),
            None,
        )
        if notebook is None:
            raise RuntimeError("Dead Signal Data Intelligence notebook was not created")
        install_advanced_tabs(notebook, self)
        install_discovery_tab(notebook, self)
        install_verification_tab(notebook, self)
        install_compiler_tab(notebook, self)


def open_data_intelligence(parent, output: Path, open_evidence_console):
    return DeadSignalDataIntelligence(parent, output, open_evidence_console)
