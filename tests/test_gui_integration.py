"""
Integration tests for the DEEAC Tk GUI state handling.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import pytest

from deeac.GUI.app import DeeacGui, DynawoRuntimeValidationResult


def _build_gui(monkeypatch: pytest.MonkeyPatch, dynawo_available: bool) -> DeeacGui:
    """
    Build a GUI instance with deterministic Dynawo runtime validation.

    :param monkeypatch: Pytest monkeypatch fixture.
    :param dynawo_available: Runtime availability injected into the GUI.
    :return: GUI instance.
    """
    if dynawo_available:
        validation_result = DynawoRuntimeValidationResult(
            is_available=True,
            error_text=None,
            dynawo_install_dir="/opt/dynawo",
            dynawo_binary_path="/opt/dynawo/bin/dynawo",
        )
    else:
        validation_result = DynawoRuntimeValidationResult(
            is_available=False,
            error_text="Dynawo not installed.",
            dynawo_install_dir=None,
            dynawo_binary_path=None,
        )

    monkeypatch.setattr(
        DeeacGui,
        "validate_dynawo_runtime",
        staticmethod(lambda _install, _binary: validation_result),
    )
    try:
        app = DeeacGui()
    except tk.TclError as exc:
        pytest.skip(f"Tk is unavailable in this environment: {exc}")
    app.withdraw()
    return app


def test_dynawo_post_run_tab_is_disabled_when_runtime_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure the Dynawo post-run tab is not selectable when runtime is missing.

    :param monkeypatch: Pytest monkeypatch fixture.
    :return: Return value.
    """
    app = _build_gui(monkeypatch, dynawo_available=False)
    try:
        tab_state = app._workflow_tabs.tab(app._dynawo_post_run_tab, "state")
        assert tab_state == "disabled"
    finally:
        app.destroy()


def test_reload_failure_keeps_previous_loaded_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure a failed reload does not wipe a previously loaded GUI state.

    :param monkeypatch: Pytest monkeypatch fixture.
    :return: Return value.
    """
    app = _build_gui(monkeypatch, dynawo_available=True)
    try:
        previous_network = object()
        previous_plan = object()
        previous_faults = list([object()])

        app._network = previous_network  # type: ignore[assignment]
        app._execution_plan = previous_plan  # type: ignore[assignment]
        app._faults = previous_faults  # type: ignore[assignment]

        app._workflow_tabs.select(app._eurostag_tab)
        monkeypatch.setattr("deeac.GUI.app.messagebox.showerror", lambda *_args, **_kwargs: None)

        app.load_faults()

        assert app._network is previous_network
        assert app._execution_plan is previous_plan
        assert app._faults is previous_faults
    finally:
        app.destroy()


def test_failed_eurostag_global_config_does_not_mutate_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure Eurostag global-config application is transactional on parse failure.

    :param monkeypatch: Pytest monkeypatch fixture.
    :param tmp_path: Temporary directory fixture.
    :return: Return value.
    """
    app = _build_gui(monkeypatch, dynawo_available=True)
    try:
        app._e_ech.set("before_ech")
        app._e_dta.set("before_dta")
        app._e_lf.set("before_lf")
        app._e_seq.set("before_seq")

        case1_dir = Path(__file__).parent / "data" / "case1"
        config_path = tmp_path / "bad_global_config.json"
        config_path.write_text(
            (
                "{\n"
                f"  \"ech-file\": \"{(case1_dir / 'case1.ech').as_posix()}\",\n"
                f"  \"dta-file\": \"{(case1_dir / 'case1.dta').as_posix()}\",\n"
                f"  \"lf-file\": \"{(case1_dir / 'case1.lf').as_posix()}\",\n"
                f"  \"seq-file\": \"{(case1_dir / 'case1_line.seq').as_posix()}\",\n"
                "  \"execution-tree-file\": \"missing_execution_plan.json\"\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        app._e_plan.set(str(config_path))

        with pytest.raises(Exception):
            app.apply_eurostag_global_config()

        assert app._e_ech.get() == "before_ech"
        assert app._e_dta.get() == "before_dta"
        assert app._e_lf.get() == "before_lf"
        assert app._e_seq.get() == "before_seq"
    finally:
        app.destroy()
