"""
Small entrypoint checks for CLI versus GUI startup.
"""

from __future__ import annotations

import sys
import types

import deeac.main as main


def test_run_uses_gui_only_without_args(monkeypatch) -> None:
    """
    Start the GUI only when no CLI arguments are provided.
    """
    called = {"gui": False}
    fake_gui = types.ModuleType("deeac.GUI")
    fake_gui.run_gui = lambda: called.__setitem__("gui", True)

    monkeypatch.setattr(sys, "argv", ["deeac"])
    monkeypatch.setitem(sys.modules, "deeac.GUI", fake_gui)

    main.run()

    assert called["gui"] is True


def test_run_uses_cli_without_importing_gui(monkeypatch) -> None:
    """
    Route CLI arguments to the CLI handler without touching the GUI import.
    """
    captured = {"args": None}

    monkeypatch.setattr(sys, "argv", ["deeac", "--help"])
    monkeypatch.setattr(main, "deeac", lambda args: captured.__setitem__("args", args))

    main.run()

    assert captured["args"] == ["--help"]
