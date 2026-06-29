"""
Tkinter GUI for Eurostag and Dynawo workflows.
"""

from __future__ import annotations

import json
import os
import queue
import threading
from typing import Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from joblib import Parallel, delayed

try:
    from deeac.DynawoPostProcess.coupling import DynawoCaseCoupler, DynawoFaultSelectionOptions
    _DYNAWO_POST_PROCESS_AVAILABLE = True
except ModuleNotFoundError:
    DynawoCaseCoupler = None
    DynawoFaultSelectionOptions = None
    _DYNAWO_POST_PROCESS_AVAILABLE = False
try:
    from deeac.DynawoPostProcess.runner import DynawoRunner
    _DYNAWO_RUNNER_AVAILABLE = True
except ModuleNotFoundError:
    DynawoRunner = None
    _DYNAWO_RUNNER_AVAILABLE = False
from deeac.IO.arguments_parser import (
    DynawoRunConfiguration,
    load_dynawo_configuration,
    load_global_configuration,
)
try:
    from deeac.IO.dynawo.parse_dynawo import parse_dynawo_configuration
    _DYNAWO_PARSE_AVAILABLE = True
except ModuleNotFoundError:
    parse_dynawo_configuration = None
    _DYNAWO_PARSE_AVAILABLE = False
from deeac.IO.eurostag.parse_eurostag import parse_eurostag
from deeac.IO.plan_loader import read_execution_plan
from deeac.IO.plan_models import ExecutionPlan
from deeac.Models.events.fault_events import FaultEvents
from deeac.Models.network import Network
from deeac.Simulations.results import EEACResult, EEACResults
from deeac.Utils.logger import Logger
from deeac.deeac_all_paths import run_fault
from deeac.enums import OMIBStabilityState


class FaultSelection:
    """
    Store a fault and the checkbox state associated with it.
    
    :ivar fault: Fault represented in the GUI list.
    :ivar var: Tkinter variable tracking the checkbox state.
    """

    __slots__ = ("fault", "var")

    def __init__(self, fault: FaultEvents, var: tk.BooleanVar) -> None:
        """
        Initialize the selection entry.
        
        :param fault: Fault represented by the checkbox.
        :param var: Selection state associated with the fault.
        """
        self.fault = fault
        self.var = var


class DynawoPostRunOptions:
    """
    Store optional Dynawo post-processing options from the GUI.

    :ivar enabled: Whether Dynawo post-processing is enabled.
    :ivar run_configuration: Dynawo input run configuration.
    :ivar generation_root_dir: Root directory for generated Dynawo cases.
    :ivar dynawo_install_dir: Optional Dynawo install directory.
    :ivar dynawo_binary_path: Optional explicit Dynawo executable path.
    :ivar timeout_seconds: Optional Dynawo timeout in seconds.
    :ivar cct_min: Optional minimum CCT for fault selection.
    :ivar cct_max: Optional maximum CCT for fault selection.
    :ivar selected_statuses: Selected EEAC final statuses to pass to Dynawo coupling.
    """

    __slots__ = (
        "enabled",
        "run_configuration",
        "generation_root_dir",
        "dynawo_install_dir",
        "dynawo_binary_path",
        "timeout_seconds",
        "cct_min",
        "cct_max",
        "selected_statuses",
    )

    def __init__(
        self,
        enabled: bool,
        run_configuration: Optional[DynawoRunConfiguration],
        generation_root_dir: Optional[str],
        dynawo_install_dir: Optional[str],
        dynawo_binary_path: Optional[str],
        timeout_seconds: Optional[float],
        cct_min: Optional[float],
        cct_max: Optional[float],
        selected_statuses: List[str],
    ) -> None:
        """
        Initialize optional Dynawo post-processing options.

        :param enabled: Whether Dynawo post-processing is enabled.
        :param run_configuration: Dynawo input run configuration.
        :param generation_root_dir: Root directory for generated Dynawo cases.
        :param dynawo_install_dir: Optional Dynawo install directory.
        :param dynawo_binary_path: Optional explicit Dynawo executable path.
        :param timeout_seconds: Optional Dynawo timeout in seconds.
        :param cct_min: Optional minimum CCT for fault selection.
        :param cct_max: Optional maximum CCT for fault selection.
        :param selected_statuses: Selected EEAC final statuses to pass to Dynawo coupling.
        :return: Return value.
        """
        self.enabled = enabled
        self.run_configuration = run_configuration
        self.generation_root_dir = generation_root_dir
        self.dynawo_install_dir = dynawo_install_dir
        self.dynawo_binary_path = dynawo_binary_path
        self.timeout_seconds = timeout_seconds
        self.cct_min = cct_min
        self.cct_max = cct_max
        self.selected_statuses = selected_statuses


class DynawoRuntimeValidationResult:
    """
    Store Dynawo runtime resolution and validation status.

    :ivar is_available: Whether Dynawo can be executed with the current settings.
    :ivar error_text: Human-readable validation failure, when unavailable.
    :ivar dynawo_install_dir: Resolved Dynawo installation directory.
    :ivar dynawo_binary_path: Resolved Dynawo executable path.
    """

    __slots__ = (
        "is_available",
        "error_text",
        "dynawo_install_dir",
        "dynawo_binary_path",
    )

    def __init__(
        self,
        is_available: bool,
        error_text: Optional[str],
        dynawo_install_dir: Optional[str],
        dynawo_binary_path: Optional[str],
    ) -> None:
        """
        Initialize Dynawo runtime validation result.

        :param is_available: Whether Dynawo can be executed with the current settings.
        :param error_text: Human-readable validation failure, when unavailable.
        :param dynawo_install_dir: Resolved Dynawo installation directory.
        :param dynawo_binary_path: Resolved Dynawo executable path.
        :return: Return value.
        """
        self.is_available = is_available
        self.error_text = error_text
        self.dynawo_install_dir = dynawo_install_dir
        self.dynawo_binary_path = dynawo_binary_path


def _all_eeac_final_status_values() -> List[str]:
    """
    Return all currently known EEAC final-status values.

    :return: Ordered EEAC final-status values.
    """
    values: List[str] = list()
    values.append(OMIBStabilityState.ALWAYS_UNSTABLE.value)
    values.append(OMIBStabilityState.POTENTIALLY_STABLE.value)
    values.append(OMIBStabilityState.ALWAYS_STABLE.value)
    values.append(OMIBStabilityState.UNKNOWN.value)
    values.append("COMPUTATION_FAILURE")
    values.append("Empty fault")
    values.append("Degraded protection")
    values.append("Impedant fault")
    values.append("Irrelevant Fault")
    values.append("Islanding")
    values.append("Error")
    return values


class BrowseVariableCommand:
    """
    Explicit callback object used by browse buttons.
    
    :ivar gui: GUI instance opening the file dialog.
    :ivar variable: Variable updated with the selected path.
    :ivar browse_folder: Whether the dialog targets a directory.
    """

    __slots__ = ("_gui", "_variable", "_browse_folder")

    def __init__(self, gui: "DeeacGui", variable: tk.StringVar, browse_folder: bool) -> None:
        """
        Initialize the browse callback.
        
        :param gui: GUI instance that owns the browse helpers.
        :param variable: Variable updated with the selected path.
        :param browse_folder: ``True`` for directories, ``False`` for files.
        """
        self._gui = gui
        self._variable = variable
        self._browse_folder = browse_folder

    def __call__(self) -> None:
        """
        Open the requested dialog and store the result.
        
        :return: Return value.
        """
        if self._browse_folder:
            self._gui.browse_folder(self._variable)
        else:
            self._gui.browse_file(self._variable)


class AutofillTraceCommand:
    """
    Explicit callback object used by Tk variable traces.
    
    :ivar gui: GUI instance executing the autofill.
    :ivar variable: Variable whose value triggered the callback.
    :ivar workflow: Workflow name deciding which autofill branch to use.
    """

    __slots__ = ("_gui", "_variable", "_workflow")

    def __init__(self, gui: "DeeacGui", variable: tk.StringVar, workflow: str) -> None:
        """
        Initialize the trace callback.
        
        :param gui: GUI instance executing the autofill.
        :param variable: Variable being observed.
        :param workflow: Workflow name, either ``"eurostag"`` or ``"dynawo"``.
        """
        self._gui = gui
        self._variable = variable
        self._workflow = workflow

    def __call__(self, *_args: object) -> None:
        """
        Trigger the workflow-specific autofill.
        
        :param _args: Unused Tk trace callback arguments.
        :return: Return value.
        """
        path = self._variable.get()
        if self._workflow == "eurostag":
            self._gui.maybe_autofill_eurostag(path)
        else:
            self._gui.maybe_autofill_dynawo(path)


class ScrollableChecks(ttk.Frame):
    """
    Display a scrollable frame used to list fault checkboxes.
    
    :ivar canvas: Canvas hosting the scrolling area.
    :ivar scroll: Vertical scrollbar linked to the canvas.
    :ivar frame: Inner frame containing the checkbuttons.
    """

    def __init__(self, master: tk.Widget) -> None:
        """
        Initialize the scrollable checkbox container.
        
        :param master: Parent widget.
        """
        super().__init__(master)
        self._canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self._scroll = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._frame = ttk.Frame(self._canvas)
        self._frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.create_window((0, 0), window=self._frame, anchor="nw")
        self._canvas.configure(yscrollcommand=self._scroll.set)

        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    @property
    def frame(self) -> ttk.Frame:
        """
        Return the inner frame that receives the checkbuttons.
        
        :return: Inner frame hosted in the canvas.
        """
        return self._frame

    def clear(self) -> None:
        """
        Remove every child widget from the inner frame.
        
        :return: Return value.
        """
        for child in self._frame.winfo_children():
            child.destroy()

    def _on_frame_configure(self, _event: tk.Event) -> None:
        """
        Keep the canvas scroll region synchronized with the frame size.
        
        :param _event: Tk configure event.
        :return: Return value.
        """
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))


class WidgetTooltip:
    """
    Show a tooltip window while the mouse hovers over a widget.

    :ivar _widget: Target widget.
    :ivar _text: Tooltip text.
    :ivar _window: Optional tooltip toplevel.
    :ivar _label: Optional label inside the tooltip.
    """

    __slots__ = ("_widget", "_text", "_window", "_label")

    def __init__(self, widget: tk.Widget, text: str) -> None:
        """
        Initialize a widget tooltip.

        :param widget: Target widget.
        :param text: Tooltip text.
        :return: Return value.
        """
        self._widget = widget
        self._text = text
        self._window: Optional[tk.Toplevel] = None
        self._label: Optional[ttk.Label] = None
        self._widget.bind("<Enter>", self._show)
        self._widget.bind("<Leave>", self._hide)
        self._widget.bind("<ButtonPress>", self._hide)

    def _show(self, _event: tk.Event) -> None:
        """
        Show the tooltip window.

        :param _event: Tk enter event.
        :return: Return value.
        """
        if self._window is None:
            pass
        else:
            return
        x_coord = self._widget.winfo_rootx() + 16
        y_coord = self._widget.winfo_rooty() + self._widget.winfo_height() + 6
        self._window = tk.Toplevel(self._widget)
        self._window.wm_overrideredirect(True)
        self._window.wm_geometry(f"+{x_coord}+{y_coord}")
        self._label = ttk.Label(
            self._window,
            text=self._text,
            justify="left",
            relief="solid",
            borderwidth=1,
            padding=(6, 4),
        )
        self._label.pack()

    def _hide(self, _event: tk.Event) -> None:
        """
        Hide the tooltip window.

        :param _event: Tk leave event.
        :return: Return value.
        """
        if self._window is None:
            pass
        else:
            self._window.destroy()
            self._window = None
            self._label = None


class DeeacGui(tk.Tk):
    def __init__(self) -> None:
        """
        Initialize the DEEAC GUI and build the full widget tree.

        :return: Return value.
        """
        super().__init__()

        # ----------------------
        # Window state
        # ----------------------
        self.title("DEEAC GUI")
        self.minsize(1024, 640)

        self._network: Optional[Network] = None
        self._execution_plan: Optional[ExecutionPlan] = None
        self._faults: List[FaultSelection] = list()
        self._result_queue: "queue.Queue[Tuple[str, object]]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._dynawo_runtime_validation_after_id: Optional[str] = None
        self._autofill_lock = False
        self._autoload_lock = False
        self._last_load_signature: Optional[Tuple[str, ...]] = None
        self._active_workflow_name = "eurostag"
        self._tooltips: List[WidgetTooltip] = list()
        self._dynawo_post_run_runtime_widgets: List[tk.Widget] = list()

        # ----------------------
        # Root layout
        # ----------------------
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._paned = ttk.Panedwindow(self, orient="horizontal")
        self._paned.grid(row=0, column=0, sticky="nsew")

        self._left = ttk.Frame(self._paned, padding=12)
        self._right = ttk.Frame(self._paned, padding=12)
        self._paned.add(self._left, weight=3)
        self._paned.add(self._right, weight=4)

        self._left.columnconfigure(0, weight=1)
        self._left.rowconfigure(0, weight=1)
        self._right.columnconfigure(0, weight=1)
        self._right.rowconfigure(0, weight=1)

        # ----------------------
        # Left workflow tabs
        # ----------------------
        self._workflow_tabs = ttk.Notebook(self._left)
        self._workflow_tabs.grid(row=0, column=0, sticky="nsew")

        self._eurostag_tab = ttk.Frame(self._workflow_tabs, padding=10)
        self._dynawo_tab = ttk.Frame(self._workflow_tabs, padding=10)
        self._faults_tab = ttk.Frame(self._workflow_tabs, padding=10)
        self._dynawo_post_run_tab = ttk.Frame(self._workflow_tabs, padding=10)
        self._workflow_tabs.add(self._eurostag_tab, text="Eurostag")
        self._workflow_tabs.add(self._dynawo_tab, text="Dynawo")
        self._workflow_tabs.add(self._faults_tab, text="Faults")
        self._workflow_tabs.add(self._dynawo_post_run_tab, text="Dynawo Post-Run")

        # ----------------------
        # Eurostag tab
        # ----------------------
        self._eurostag_tab.columnconfigure(1, weight=1)

        self._e_ech = tk.StringVar()
        self._e_dta = tk.StringVar()
        self._e_lf = tk.StringVar()
        self._e_seq = tk.StringVar()
        self._e_seq_folder = tk.StringVar()
        self._e_plan = tk.StringVar()
        self._e_output = tk.StringVar()
        self._e_island = tk.StringVar(value="10")
        self._e_delay = tk.StringVar(value="15")
        self._e_cores = tk.StringVar(value=str(os.cpu_count() or 1))
        self._e_verbose = tk.BooleanVar(value=False)
        self._e_warn = tk.BooleanVar(value=False)
        self._e_generate_output_files = tk.BooleanVar(value=True)
        self._e_use_folder = tk.BooleanVar(value=False)
        self.bind_eurostag_autofill()

        eurostag_row: int = 0
        eurostag_row = self.add_file_row(self._eurostag_tab, eurostag_row, "ECH file", self._e_ech, False)
        eurostag_row = self.add_file_row(self._eurostag_tab, eurostag_row, "DTA file", self._e_dta, False)
        eurostag_row = self.add_file_row(self._eurostag_tab, eurostag_row, "LF file", self._e_lf, False)

        seq_frame = ttk.Frame(self._eurostag_tab)
        seq_frame.grid(row=eurostag_row, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        seq_frame.columnconfigure(2, weight=1)
        ttk.Checkbutton(
            seq_frame,
            text="Use Seq Folder",
            variable=self._e_use_folder,
            command=self.toggle_seq_mode,
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(seq_frame, text="Seq file").grid(row=1, column=0, sticky="w")
        self._seq_entry = ttk.Entry(seq_frame, textvariable=self._e_seq)
        self._seq_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(8, 0))
        self.add_tooltip(self._seq_entry, "Eurostag .seq file for single-fault workflow.")
        seq_browse_button = ttk.Button(seq_frame, text="Browse", command=BrowseVariableCommand(self, self._e_seq, False))
        seq_browse_button.grid(row=1, column=3, padx=(6, 0))
        self.add_tooltip(seq_browse_button, "Browse for a Eurostag .seq file.")
        ttk.Label(seq_frame, text="Seq folder").grid(row=2, column=0, sticky="w")
        self._seq_folder_entry = ttk.Entry(seq_frame, textvariable=self._e_seq_folder, state="disabled")
        self._seq_folder_entry.grid(row=2, column=1, columnspan=2, sticky="ew", padx=(8, 0))
        self.add_tooltip(self._seq_folder_entry, "Folder containing multiple Eurostag .seq files.")
        seq_folder_browse_button = ttk.Button(
            seq_frame,
            text="Browse",
            command=BrowseVariableCommand(self, self._e_seq_folder, True),
        )
        seq_folder_browse_button.grid(row=2, column=3, padx=(6, 0))
        self.add_tooltip(seq_folder_browse_button, "Browse for a folder containing Eurostag .seq files.")
        eurostag_row += 1

        eurostag_row = self.add_file_row(self._eurostag_tab, eurostag_row, "Execution plan", self._e_plan, False)
        eurostag_row = self.add_file_row(self._eurostag_tab, eurostag_row, "Output dir", self._e_output, True)
        eurostag_row = self.add_entry_row(self._eurostag_tab, eurostag_row, "Island threshold (MW)", self._e_island)
        eurostag_row = self.add_entry_row(self._eurostag_tab, eurostag_row, "Protection delay (ms)", self._e_delay)
        eurostag_row = self.add_entry_row(self._eurostag_tab, eurostag_row, "Cores", self._e_cores)

        eurostag_options = ttk.Frame(self._eurostag_tab)
        eurostag_options.grid(row=eurostag_row, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Checkbutton(eurostag_options, text="Verbose", variable=self._e_verbose).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(
            eurostag_options,
            text="Warn on failure",
            variable=self._e_warn,
        ).grid(row=0, column=1, sticky="w", padx=(12, 0))
        ttk.Checkbutton(
            eurostag_options,
            text="Generate output files",
            variable=self._e_generate_output_files,
        ).grid(row=0, column=2, sticky="w", padx=(12, 0))

        # ----------------------
        # Dynawo tab
        # ----------------------
        self._dynawo_tab.columnconfigure(1, weight=1)

        self._d_mode = tk.StringVar(value="jobs")
        self._d_jobs = tk.StringVar()
        self._d_iidm = tk.StringVar()
        self._d_dyd = tk.StringVar()
        self._d_par = tk.StringVar()
        self._d_plan = tk.StringVar()
        self._d_output = tk.StringVar()
        self._d_island = tk.StringVar(value="10")
        self._d_cores = tk.StringVar(value=str(os.cpu_count() or 1))
        self._d_verbose = tk.BooleanVar(value=False)
        self._d_warn = tk.BooleanVar(value=False)
        self._d_generate_output_files = tk.BooleanVar(value=True)
        self._d_post_run_enabled = tk.BooleanVar(value=False)
        self._d_dynawo_install_dir = tk.StringVar()
        self._d_dynawo_binary_path = tk.StringVar()
        self._d_dynawo_timeout_seconds = tk.StringVar(value="120")
        self._d_dynawo_cct_min = tk.StringVar()
        self._d_dynawo_cct_max = tk.StringVar()
        self._d_dynawo_status_vars: Dict[str, tk.BooleanVar] = dict()
        for status_name in _all_eeac_final_status_values():
            default_value = status_name == OMIBStabilityState.ALWAYS_UNSTABLE.value
            self._d_dynawo_status_vars[status_name] = tk.BooleanVar(value=default_value)
        self.bind_dynawo_autofill()

        dynawo_row: int = 0
        dynawo_info_label = ttk.Label(
            self._dynawo_tab,
            text=(
                "Preferred workflow: provide the Dynawo .jobs case file. "
                "Manual IIDM/DYD/PAR input remains available as a fallback."
            ),
            wraplength=700,
            justify="left",
        )
        dynawo_info_label.grid(row=dynawo_row, column=0, columnspan=3, sticky="w", pady=(0, 8))
        dynawo_row += 1

        dynawo_mode_frame = ttk.Frame(self._dynawo_tab)
        dynawo_mode_frame.grid(row=dynawo_row, column=0, columnspan=3, sticky="w", pady=(0, 4))
        ttk.Radiobutton(
            dynawo_mode_frame,
            text="Use Dynawo .jobs file",
            variable=self._d_mode,
            value="jobs",
            command=self.toggle_dynawo_mode,
        ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            dynawo_mode_frame,
            text="Manual IIDM / DYD / PAR",
            variable=self._d_mode,
            value="manual",
            command=self.toggle_dynawo_mode,
        ).grid(row=0, column=1, sticky="w", padx=(16, 0))
        dynawo_row += 1

        ttk.Label(self._dynawo_tab, text="Jobs file").grid(row=dynawo_row, column=0, sticky="w", pady=(4, 0))
        self._d_jobs_entry = ttk.Entry(self._dynawo_tab, textvariable=self._d_jobs)
        self._d_jobs_entry.grid(row=dynawo_row, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self.add_tooltip(self._d_jobs_entry, "Dynawo .jobs file used to load and run the base Dynawo case.")
        self._d_jobs_button = ttk.Button(
            self._dynawo_tab,
            text="Browse",
            command=BrowseVariableCommand(self, self._d_jobs, False),
        )
        self._d_jobs_button.grid(row=dynawo_row, column=2, padx=(6, 0), pady=(4, 0))
        self.add_tooltip(self._d_jobs_button, "Browse for a Dynawo .jobs file.")
        dynawo_row += 1

        dynawo_manual_label = ttk.Label(self._dynawo_tab, text="Manual fallback inputs")
        dynawo_manual_label.grid(row=dynawo_row, column=0, columnspan=3, sticky="w", pady=(10, 0))
        dynawo_row += 1

        ttk.Label(self._dynawo_tab, text="IIDM file").grid(row=dynawo_row, column=0, sticky="w", pady=(4, 0))
        self._d_iidm_entry = ttk.Entry(self._dynawo_tab, textvariable=self._d_iidm)
        self._d_iidm_entry.grid(row=dynawo_row, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self.add_tooltip(self._d_iidm_entry, "Manual IIDM input for Dynawo when jobs mode is not used.")
        self._d_iidm_button = ttk.Button(
            self._dynawo_tab,
            text="Browse",
            command=BrowseVariableCommand(self, self._d_iidm, False),
        )
        self._d_iidm_button.grid(row=dynawo_row, column=2, padx=(6, 0), pady=(4, 0))
        self.add_tooltip(self._d_iidm_button, "Browse for a Dynawo IIDM file.")
        dynawo_row += 1

        ttk.Label(self._dynawo_tab, text="DYD file").grid(row=dynawo_row, column=0, sticky="w", pady=(4, 0))
        self._d_dyd_entry = ttk.Entry(self._dynawo_tab, textvariable=self._d_dyd)
        self._d_dyd_entry.grid(row=dynawo_row, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self.add_tooltip(self._d_dyd_entry, "Manual DYD input for Dynawo when jobs mode is not used.")
        self._d_dyd_button = ttk.Button(
            self._dynawo_tab,
            text="Browse",
            command=BrowseVariableCommand(self, self._d_dyd, False),
        )
        self._d_dyd_button.grid(row=dynawo_row, column=2, padx=(6, 0), pady=(4, 0))
        self.add_tooltip(self._d_dyd_button, "Browse for a Dynawo DYD file.")
        dynawo_row += 1

        ttk.Label(self._dynawo_tab, text="PAR file").grid(row=dynawo_row, column=0, sticky="w", pady=(4, 0))
        self._d_par_entry = ttk.Entry(self._dynawo_tab, textvariable=self._d_par)
        self._d_par_entry.grid(row=dynawo_row, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self.add_tooltip(self._d_par_entry, "Manual PAR input for Dynawo when jobs mode is not used.")
        self._d_par_button = ttk.Button(
            self._dynawo_tab,
            text="Browse",
            command=BrowseVariableCommand(self, self._d_par, False),
        )
        self._d_par_button.grid(row=dynawo_row, column=2, padx=(6, 0), pady=(4, 0))
        self.add_tooltip(self._d_par_button, "Browse for a Dynawo PAR file.")
        dynawo_row += 1

        dynawo_row = self.add_file_row(self._dynawo_tab, dynawo_row, "Execution plan", self._d_plan, False)
        dynawo_row = self.add_file_row(self._dynawo_tab, dynawo_row, "Output dir", self._d_output, True)
        dynawo_row = self.add_entry_row(self._dynawo_tab, dynawo_row, "Island threshold (MW)", self._d_island)
        dynawo_row = self.add_entry_row(self._dynawo_tab, dynawo_row, "Cores", self._d_cores)

        dynawo_options = ttk.Frame(self._dynawo_tab)
        dynawo_options.grid(row=dynawo_row, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Checkbutton(dynawo_options, text="Verbose", variable=self._d_verbose).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(
            dynawo_options,
            text="Warn on failure",
            variable=self._d_warn,
        ).grid(row=0, column=1, sticky="w", padx=(12, 0))
        ttk.Checkbutton(
            dynawo_options,
            text="Generate output files",
            variable=self._d_generate_output_files,
        ).grid(row=0, column=2, sticky="w", padx=(12, 0))

        # ----------------------
        # Faults tab
        # ----------------------
        self._faults_tab.columnconfigure(0, weight=1)
        self._faults_tab.rowconfigure(0, weight=1)
        faults_frame = ttk.LabelFrame(self._faults_tab, text="Faults", padding=8)
        faults_frame.grid(row=0, column=0, sticky="nsew")
        faults_frame.columnconfigure(0, weight=1)
        faults_frame.rowconfigure(0, weight=1)

        self._fault_list = ScrollableChecks(faults_frame)
        self._fault_list.grid(row=0, column=0, sticky="nsew")
        self.add_tooltip(self._fault_list, "List of loaded faults. Select which faults to run.")

        # ----------------------
        # Dynawo post-run tab
        # ----------------------
        self._dynawo_post_run_tab.columnconfigure(0, weight=1)
        self._dynawo_post_run_tab.rowconfigure(0, weight=1)

        post_run_frame = ttk.LabelFrame(self._dynawo_post_run_tab, text="Dynawo Post-Run (Optional)", padding=8)
        post_run_frame.grid(row=0, column=0, sticky="nsew")
        post_run_frame.columnconfigure(1, weight=1)

        dynawo_post_run_checkbutton = ttk.Checkbutton(
            post_run_frame,
            text="Generate and run Dynawo cases from unstable EEAC results",
            variable=self._d_post_run_enabled,
        )
        dynawo_post_run_checkbutton.grid(row=0, column=0, columnspan=3, sticky="w")
        self._dynawo_post_run_runtime_widgets.append(dynawo_post_run_checkbutton)

        status_frame = ttk.Frame(post_run_frame)
        status_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        status_frame.columnconfigure(0, weight=1)
        ttk.Label(status_frame, text="EEAC statuses to include").grid(row=0, column=0, sticky="w")

        status_list = ScrollableChecks(status_frame)
        status_list.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        status_list._canvas.configure(height=180)
        self.add_tooltip(status_list, "Check EEAC final statuses that should be converted to Dynawo cases.")
        for status_name in _all_eeac_final_status_values():
            status_checkbutton = ttk.Checkbutton(
                status_list.frame,
                text=status_name,
                variable=self._d_dynawo_status_vars[status_name],
            )
            status_checkbutton.pack(anchor="w")
            self._dynawo_post_run_runtime_widgets.append(status_checkbutton)

        ttk.Label(post_run_frame, text="Dynawo install dir").grid(row=2, column=0, sticky="w", pady=(8, 0))
        dynawo_install_entry = ttk.Entry(post_run_frame, textvariable=self._d_dynawo_install_dir)
        dynawo_install_entry.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self.add_tooltip(dynawo_install_entry, "Dynawo install directory containing bin/lib/share/ddb.")
        self.add_tooltip(post_run_frame, "Optional settings for generating and running Dynawo cases after EEAC.")
        dynawo_install_button = ttk.Button(
            post_run_frame,
            text="Browse",
            command=BrowseVariableCommand(self, self._d_dynawo_install_dir, True),
        )
        dynawo_install_button.grid(row=2, column=2, padx=(6, 0), pady=(4, 0))
        self.add_tooltip(dynawo_install_button, "Browse for Dynawo install directory.")

        ttk.Label(post_run_frame, text="Dynawo binary (optional)").grid(row=3, column=0, sticky="w", pady=(4, 0))
        dynawo_binary_entry = ttk.Entry(post_run_frame, textvariable=self._d_dynawo_binary_path)
        dynawo_binary_entry.grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self.add_tooltip(dynawo_binary_entry, "Optional explicit Dynawo executable path.")
        dynawo_binary_button = ttk.Button(
            post_run_frame,
            text="Browse",
            command=BrowseVariableCommand(self, self._d_dynawo_binary_path, False),
        )
        dynawo_binary_button.grid(row=3, column=2, padx=(6, 0), pady=(4, 0))
        self.add_tooltip(dynawo_binary_button, "Browse for explicit Dynawo executable.")

        ttk.Label(post_run_frame, text="Timeout (s)").grid(row=4, column=0, sticky="w", pady=(4, 0))
        dynawo_timeout_entry = ttk.Entry(post_run_frame, textvariable=self._d_dynawo_timeout_seconds)
        dynawo_timeout_entry.grid(row=4, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self.add_tooltip(dynawo_timeout_entry, "Timeout in seconds for each Dynawo run.")
        self._dynawo_post_run_runtime_widgets.append(dynawo_timeout_entry)

        ttk.Label(post_run_frame, text="CCT min (optional)").grid(row=5, column=0, sticky="w", pady=(4, 0))
        dynawo_cct_min_entry = ttk.Entry(post_run_frame, textvariable=self._d_dynawo_cct_min)
        dynawo_cct_min_entry.grid(row=5, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self.add_tooltip(dynawo_cct_min_entry, "Optional minimum CCT filter for selected EEAC statuses.")
        self._dynawo_post_run_runtime_widgets.append(dynawo_cct_min_entry)

        ttk.Label(post_run_frame, text="CCT max (optional)").grid(row=6, column=0, sticky="w", pady=(4, 0))
        dynawo_cct_max_entry = ttk.Entry(post_run_frame, textvariable=self._d_dynawo_cct_max)
        dynawo_cct_max_entry.grid(row=6, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self.add_tooltip(dynawo_cct_max_entry, "Optional maximum CCT filter for selected EEAC statuses.")
        self._dynawo_post_run_runtime_widgets.append(dynawo_cct_max_entry)

        # ----------------------
        # Left actions
        # ----------------------
        actions = ttk.Frame(self._left)
        actions.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        actions.columnconfigure(0, weight=1)

        self._status_var = tk.StringVar(value="Ready")
        self._status_label = ttk.Label(actions, textvariable=self._status_var)
        self._status_label.grid(row=0, column=0, sticky="w")

        self._load_button = ttk.Button(actions, text="Reload", command=self.load_faults)
        self._load_button.grid(row=0, column=1, padx=(8, 0))
        self.add_tooltip(self._load_button, "Reload faults from the currently selected workflow inputs.")

        self._clear_button = ttk.Button(actions, text="Clear", command=self.clear_inputs)
        self._clear_button.grid(row=0, column=2, padx=(6, 0))
        self.add_tooltip(
            self._clear_button,
            "Reset all inputs, loaded faults, results, and internal runtime state to defaults.",
        )

        self._select_all_button = ttk.Button(actions, text="Select All", command=self.select_all_faults)
        self._select_all_button.grid(row=0, column=3, padx=(6, 0))
        self.add_tooltip(self._select_all_button, "Select all loaded faults in the faults list.")

        self._select_none_button = ttk.Button(actions, text="Select None", command=self.select_none_faults)
        self._select_none_button.grid(row=0, column=4, padx=(6, 0))
        self.add_tooltip(self._select_none_button, "Unselect all loaded faults in the faults list.")

        self._run_button = ttk.Button(actions, text="Run Simulation", command=self.run_selected_faults)
        self._run_button.grid(row=0, column=5, padx=(12, 0))
        self.add_tooltip(self._run_button, "Run EEAC for selected faults and optional Dynawo post-run.")

        # ----------------------
        # Right results area
        # ----------------------
        self._results_tabs = ttk.Notebook(self._right)
        self._results_tabs.grid(row=0, column=0, sticky="nsew")

        results_frame = ttk.Frame(self._results_tabs, padding=8)
        logs_frame = ttk.Frame(self._results_tabs, padding=8)
        self._results_tabs.add(results_frame, text="Results")
        self._results_tabs.add(logs_frame, text="Logs")

        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        self._results_tree = ttk.Treeview(results_frame, columns=("value",), show="tree headings")
        self._results_tree.heading("#0", text="Item")
        self._results_tree.heading("value", text="Value")
        self._results_tree.column("value", width=240, anchor="w")
        results_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=self._results_tree.yview)
        self._results_tree.configure(yscrollcommand=results_scroll.set)
        self._results_tree.grid(row=0, column=0, sticky="nsew")
        results_scroll.grid(row=0, column=1, sticky="ns")
        self.add_tooltip(self._results_tree, "Result tree for each fault run and post-run summaries.")

        logs_frame.columnconfigure(0, weight=1)
        logs_frame.rowconfigure(0, weight=1)
        self._log_text = tk.Text(logs_frame, wrap="word", height=10, state="disabled")
        logs_scroll = ttk.Scrollbar(logs_frame, orient="vertical", command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=logs_scroll.set)
        self._log_text.grid(row=0, column=0, sticky="nsew")
        logs_scroll.grid(row=0, column=1, sticky="ns")
        self.add_tooltip(self._log_text, "Execution logs grouped by fault and Dynawo post-run.")

        # ----------------------
        # Initial widget state
        # ----------------------
        self.toggle_seq_mode()
        self.toggle_dynawo_mode()
        self.bind_dynawo_runtime_availability()
        self._autofill_system_dynawo_binary()
        self.refresh_dynawo_post_run_availability()

    def _autofill_system_dynawo_binary(self) -> None:
        """
        Prefill Dynawo binary path from `/usr/bin` when available.

        :return: Return value.
        """
        if self._d_dynawo_binary_path.get().strip() == "":
            pass
        else:
            return

        candidates: List[str] = list()
        candidates.append("/usr/bin/dynawo")
        try:
            usr_bin_entries = os.listdir("/usr/bin")
        except OSError:
            usr_bin_entries = list()
        for entry in sorted(usr_bin_entries):
            if entry.startswith("dynawo-"):
                candidates.append(os.path.join("/usr/bin", entry))
            else:
                pass

        for candidate in candidates:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                self._d_dynawo_binary_path.set(candidate)
                return
            else:
                pass


    def add_file_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        browse_folder: bool,
    ) -> int:
        """

        :param parent:
        :param row:
        :param label:
        :param variable:
        :param browse_folder:
        :return:
        """
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=(4, 0))
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self.add_tooltip(entry, f"{label} input.")
        button = ttk.Button(parent, text="Browse", command=BrowseVariableCommand(self, variable, browse_folder))
        button.grid(
            row=row, column=2, padx=(6, 0), pady=(4, 0)
        )
        if browse_folder:
            self.add_tooltip(button, f"Browse for {label.lower()} folder.")
        else:
            self.add_tooltip(button, f"Browse for {label.lower()} file.")
        return row + 1

    def add_entry_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
    ) -> int:
        """

        :param parent:
        :param row:
        :param label:
        :param variable:
        :return:
        """
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=(4, 0))
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self.add_tooltip(entry, f"{label} value.")
        return row + 1

    def add_tooltip(self, widget: tk.Widget, text: str) -> None:
        """
        Attach a tooltip to a widget and keep a strong reference.

        :param widget: Target widget.
        :param text: Tooltip text.
        :return: Return value.
        """
        tooltip = WidgetTooltip(widget, text)
        self._tooltips.append(tooltip)

    def bind_eurostag_autofill(self) -> None:
        """

        :return:
        """
        for variable in (self._e_ech, self._e_dta, self._e_lf, self._e_plan):
            variable.trace_add("write", AutofillTraceCommand(self, variable, "eurostag"))

    def bind_dynawo_autofill(self) -> None:
        """

        :return:
        """
        for variable in (self._d_jobs, self._d_iidm, self._d_dyd, self._d_par, self._d_plan):
            variable.trace_add("write", AutofillTraceCommand(self, variable, "dynawo"))

    def bind_dynawo_runtime_availability(self) -> None:
        """
        Refresh Dynawo post-run availability when Dynawo runtime inputs change.

        :return: Return value.
        """
        for variable in (self._d_dynawo_install_dir, self._d_dynawo_binary_path):
            variable.trace_add("write", self.schedule_dynawo_runtime_availability_refresh)

    def schedule_dynawo_runtime_availability_refresh(self, *_args: object) -> None:
        """
        Debounce Dynawo runtime availability refresh during text editing.

        :param _args: Unused Tk trace callback arguments.
        :return: Return value.
        """
        if self._dynawo_runtime_validation_after_id is None:
            pass
        else:
            self.after_cancel(self._dynawo_runtime_validation_after_id)
        self._dynawo_runtime_validation_after_id = self.after(300, self.refresh_dynawo_post_run_availability)

    def refresh_dynawo_post_run_availability(self, *_args: object) -> None:
        """
        Enable Dynawo post-run controls only when a runnable Dynawo is available.

        :param _args: Unused Tk trace callback arguments.
        :return: Return value.
        """
        self._dynawo_runtime_validation_after_id = None
        dynawo_install_dir: Optional[str] = self._d_dynawo_install_dir.get().strip() or None
        dynawo_binary_path: Optional[str] = self._d_dynawo_binary_path.get().strip() or None
        validation_result = self.validate_dynawo_runtime(
            dynawo_install_dir,
            dynawo_binary_path,
        )

        post_run_state: str
        if validation_result.is_available:
            post_run_state = "normal"
            self._workflow_tabs.tab(self._dynawo_post_run_tab, text="Dynawo Post-Run", state="normal")
        else:
            post_run_state = "disabled"
            self._d_post_run_enabled.set(False)
            self._workflow_tabs.tab(self._dynawo_post_run_tab, text="Dynawo Post-Run (Unavailable)", state="disabled")

        for widget in self._dynawo_post_run_runtime_widgets:
            widget.configure(state=post_run_state)

    def maybe_autofill_eurostag(self, path: str) -> None:
        """

        :param path:
        :return:
        """
        if self._autofill_lock:
            return
        if not path:
            return
        directory, stem = self.path_context(path)
        if not directory or not os.path.isdir(directory):
            return

        targets = [
            (".ech", self._e_ech),
            (".dta", self._e_dta),
            (".lf", self._e_lf),
            (".json", self._e_plan),
            (".seq", self._e_seq),
        ]
        matches = self.find_files_by_extension(directory, [ext for ext, _ in targets])
        seq_folders = self.find_seq_folders(directory)

        self._autofill_lock = True
        try:
            for extension, variable in targets:
                if extension == ".seq":
                    continue
                if variable.get().strip():
                    continue
                candidate = self.pick_candidate(matches.get(extension, []), stem)
                if candidate:
                    variable.set(candidate)

            self.apply_eurostag_seq_candidates(seq_folders, matches.get(".seq", []), stem)
            self.apply_eurostag_output_candidate(directory)
        finally:
            self._autofill_lock = False
        self.maybe_autoload_faults("eurostag")

    def maybe_autofill_dynawo(self, path: str) -> None:
        """

        :param path:
        :return:
        """
        if self._autofill_lock:
            return
        if not path:
            return

        directory, stem = self.path_context(path)
        if not directory or not os.path.isdir(directory):
            return

        path_extension = ""
        if os.path.isfile(path):
            path_extension = os.path.splitext(path)[1].lower()

        matches = self.find_files_by_extension(directory, [".jobs", ".iidm", ".dyd", ".par", ".json"])

        self._autofill_lock = True
        try:
            # The selected file tells the GUI which Dynawo workflow the user is following.
            if path_extension == ".jobs":
                self._d_mode.set("jobs")
            elif path_extension in {".iidm", ".dyd", ".par"}:
                self._d_mode.set("manual")

            if self.use_dynawo_jobs_mode():
                if not self._d_jobs.get().strip():
                    jobs_candidate = self.pick_candidate(matches.get(".jobs", []), stem)
                    if jobs_candidate:
                        self._d_jobs.set(jobs_candidate)
            else:
                manual_targets: List[Tuple[str, tk.StringVar]] = [
                    (".iidm", self._d_iidm),
                    (".dyd", self._d_dyd),
                    (".par", self._d_par),
                ]
                for extension, variable in manual_targets:
                    if variable.get().strip():
                        continue
                    candidate = self.pick_candidate(matches.get(extension, []), stem)
                    if candidate:
                        variable.set(candidate)

            if not self._d_plan.get().strip():
                plan_candidate = self.pick_candidate(matches.get(".json", []), stem)
                if plan_candidate:
                    self._d_plan.set(plan_candidate)

            self.apply_dynawo_output_candidate(directory)
            self.toggle_dynawo_mode()
        finally:
            self._autofill_lock = False

        self.maybe_autoload_faults("dynawo")

    def maybe_autofill(
        self,
        path: str,
        targets: List[Tuple[str, tk.StringVar]],
    ) -> None:
        """
        Autofill a group of related inputs from one selected path.

        :param path: User-selected path used as the autofill anchor.
        :param targets: Extension-to-variable mapping to populate.
        :return: Return value.
        """
        if self._autofill_lock:
            return
        if not path:
            return
        directory, stem = self.path_context(path)
        if not directory or not os.path.isdir(directory):
            return

        extensions = [ext for ext, _ in targets]
        matches = self.find_files_by_extension(directory, extensions)

        self._autofill_lock = True
        try:
            for extension, variable in targets:
                if variable.get().strip():
                    continue
                candidate = self.pick_candidate(matches.get(extension, []), stem)
                if candidate:
                    variable.set(candidate)
        finally:
            self._autofill_lock = False

    @staticmethod
    def path_context(path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolve the directory and filename stem behind one input path.

        :param path: File or directory path selected by the user.
        :return: Tuple of candidate directory and filename stem.
        """
        path = path.strip()
        if not path:
            return None, None
        if os.path.isdir(path):
            return path, None
        directory = os.path.dirname(path)
        if not directory:
            if os.path.exists(path):
                directory = os.getcwd()
            else:
                return None, None
        stem = os.path.splitext(os.path.basename(path))[0]
        return directory, stem

    @staticmethod
    def find_files_by_extension(
        directory: str,
        extensions: List[str],
    ) -> Dict[str, List[str]]:
        """
        Group files in one directory by extension.

        :param directory: Directory to inspect.
        :param extensions: Extensions to collect.
        :return: Mapping from extension to matching files.
        """
        wanted = {ext.lower() for ext in extensions}
        matches: Dict[str, List[str]] = {ext: [] for ext in wanted}
        for name in os.listdir(directory):
            _, ext = os.path.splitext(name)
            ext = ext.lower()
            if ext in wanted:
                matches[ext].append(os.path.join(directory, name))
        for ext in matches:
            matches[ext].sort()
        return matches

    @staticmethod
    def find_seq_folders(directory: str) -> List[str]:
        """
        Find child folders that contain at least one `.seq` file.

        :param directory: Parent directory to inspect.
        :return: Sorted candidate sequence folders.
        """
        candidates: List[str] = []
        for name in os.listdir(directory):
            path = os.path.join(directory, name)
            if not os.path.isdir(path):
                continue
            try:
                for entry in os.listdir(path):
                    if os.path.splitext(entry)[1].lower() == ".seq":
                        candidates.append(path)
                        break
            except OSError:
                continue
        candidates.sort()
        return candidates

    @staticmethod
    def pick_candidate(candidates: List[str], stem: Optional[str]) -> Optional[str]:
        """
        Pick the best single file candidate for autofill.

        :param candidates: Candidate file paths.
        :param stem: Preferred filename stem, when available.
        :return: Selected file path or ``None``.
        """
        if not candidates:
            return None
        if stem:
            for path in candidates:
                if os.path.splitext(os.path.basename(path))[0] == stem:
                    return path
        if len(candidates) == 1:
            return candidates[0]
        return None

    @staticmethod
    def pick_candidate_folder(candidates: List[str], stem: Optional[str]) -> Optional[str]:
        """
        Pick the best single folder candidate for autofill.

        :param candidates: Candidate directory paths.
        :param stem: Preferred folder name, when available.
        :return: Selected directory path or ``None``.
        """
        if not candidates:
            return None
        if stem:
            for path in candidates:
                if os.path.basename(path) == stem:
                    return path
        if len(candidates) == 1:
            return candidates[0]
        return None

    def apply_eurostag_seq_candidates(
        self,
        seq_folders: List[str],
        seq_files: List[str],
        stem: Optional[str],
    ) -> None:
        """
        Apply the best Eurostag sequence input discovered during autofill.

        :param seq_folders: Candidate sequence folders.
        :param seq_files: Candidate single `.seq` files.
        :param stem: Preferred filename stem, when available.
        :return: Return value.
        """
        if self._e_seq_folder.get().strip() or self._e_seq.get().strip():
            return
        seq_folder = self.pick_candidate_folder(seq_folders, stem)
        if seq_folder:
            self._e_use_folder.set(True)
            self.toggle_seq_mode()
            self._e_seq_folder.set(seq_folder)
            self._e_seq.set("")
            return
        seq_file = self.pick_candidate(seq_files, stem)
        if seq_file:
            self._e_use_folder.set(False)
            self.toggle_seq_mode()
            self._e_seq.set(seq_file)
            self._e_seq_folder.set("")

    def apply_eurostag_output_candidate(self, directory: str) -> None:
        """
        Populate the Eurostag output directory from the selected case directory.

        :param directory: Directory associated with the selected Eurostag input.
        :return: Return value.
        """
        if self._e_output.get().strip():
            return
        default_path = os.path.join(directory, "deeac_output")
        if os.path.isdir(default_path):
            self._e_output.set(default_path)
            return
        output_like = [
            os.path.join(directory, name)
            for name in os.listdir(directory)
            if os.path.isdir(os.path.join(directory, name)) and "output" in name.lower()
        ]
        if len(output_like) == 1:
            self._e_output.set(output_like[0])
            return
        self._e_output.set(default_path)

    def apply_dynawo_output_candidate(self, directory: str) -> None:
        """
        Populate the Dynawo output directory from the selected case directory.

        :param directory: Directory associated with the selected Dynawo input.
        :return: Return value.
        """
        if self._d_output.get().strip():
            return
        default_path = os.path.join(directory, "deeac_output")
        if os.path.isdir(default_path):
            self._d_output.set(default_path)
            return
        output_like: List[str] = [
            os.path.join(directory, name)
            for name in os.listdir(directory)
            if os.path.isdir(os.path.join(directory, name)) and "output" in name.lower()
        ]
        if len(output_like) == 1:
            self._d_output.set(output_like[0])
            return
        self._d_output.set(default_path)

    @staticmethod
    def browse_file(variable: tk.StringVar) -> None:
        """
        Open a file chooser and store the selected path.

        :param variable: Tk variable updated with the selected file path.
        :return: Return value.
        """
        path = filedialog.askopenfilename()
        if path:
            variable.set(path)

    @staticmethod
    def browse_folder(variable: tk.StringVar) -> None:
        """
        Open a folder chooser and store the selected path.

        :param variable: Tk variable updated with the selected directory path.
        :return: Return value.
        """
        path = filedialog.askdirectory()
        if path:
            variable.set(path)

    def toggle_seq_mode(self) -> None:
        """
        Enable either single-file or folder-based Eurostag sequence inputs.

        :return: Return value.
        """
        use_folder = self._e_use_folder.get()
        self._seq_entry.configure(state="disabled" if use_folder else "normal")
        self._seq_folder_entry.configure(state="normal" if use_folder else "disabled")

    def toggle_dynawo_mode(self) -> None:
        """
        Enable the widgets that belong to the selected Dynawo workflow.

        :return: Return value.
        """
        jobs_mode = self.use_dynawo_jobs_mode()
        jobs_state = "normal" if jobs_mode else "disabled"
        manual_state = "disabled" if jobs_mode else "normal"

        self._d_jobs_entry.configure(state=jobs_state)
        self._d_jobs_button.configure(state=jobs_state)

        self._d_iidm_entry.configure(state=manual_state)
        self._d_iidm_button.configure(state=manual_state)
        self._d_dyd_entry.configure(state=manual_state)
        self._d_dyd_button.configure(state=manual_state)
        self._d_par_entry.configure(state=manual_state)
        self._d_par_button.configure(state=manual_state)

    def use_dynawo_jobs_mode(self) -> bool:
        """
        Tell whether the Dynawo tab currently uses the `.jobs` workflow.

        :return: ``True`` when `.jobs` mode is selected.
        """
        return self._d_mode.get() == "jobs"

    def select_all_faults(self) -> None:
        """

        :return:
        """
        for item in self._faults:
            item.var.set(True)

    def select_none_faults(self) -> None:
        """

        :return:
        """
        for item in self._faults:
            item.var.set(False)

    def clear_inputs(self) -> None:
        """
        Reset GUI inputs and runtime state to a clean default baseline.

        :return: Return value.
        """
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("Run in progress", "Wait for the current run to finish before clearing.")
            return

        self._autofill_lock = True
        try:
            self._e_ech.set("")
            self._e_dta.set("")
            self._e_lf.set("")
            self._e_seq.set("")
            self._e_seq_folder.set("")
            self._e_plan.set("")
            self._e_output.set("")
            self._e_island.set("10")
            self._e_delay.set("15")
            self._e_cores.set(str(os.cpu_count() or 1))
            self._e_verbose.set(False)
            self._e_warn.set(False)
            self._e_generate_output_files.set(True)
            self._e_use_folder.set(False)
            self.toggle_seq_mode()

            self._d_iidm.set("")
            self._d_dyd.set("")
            self._d_par.set("")
            self._d_jobs.set("")
            self._d_plan.set("")
            self._d_output.set("")
            self._d_island.set("10")
            self._d_cores.set(str(os.cpu_count() or 1))
            self._d_verbose.set(False)
            self._d_warn.set(False)
            self._d_generate_output_files.set(True)
            self._d_post_run_enabled.set(False)
            self._d_dynawo_install_dir.set("")
            self._d_dynawo_binary_path.set("")
            self._d_dynawo_timeout_seconds.set("120")
            self._d_dynawo_cct_min.set("")
            self._d_dynawo_cct_max.set("")
            for status_name in _all_eeac_final_status_values():
                selected = status_name == OMIBStabilityState.ALWAYS_UNSTABLE.value
                self._d_dynawo_status_vars[status_name].set(selected)
            self._d_mode.set("jobs")
            self.toggle_dynawo_mode()
        finally:
            self._autofill_lock = False

        self._autofill_system_dynawo_binary()
        if self._dynawo_runtime_validation_after_id is None:
            pass
        else:
            self.after_cancel(self._dynawo_runtime_validation_after_id)
            self._dynawo_runtime_validation_after_id = None
        self.refresh_dynawo_post_run_availability()
        self.clear_results()
        self._result_queue = queue.Queue()
        self._worker = None
        self._fault_list.clear()
        self._faults = []
        self._network = None
        self._execution_plan = None
        self._last_load_signature = None
        self._autoload_lock = False
        self._active_workflow_name = "eurostag"
        self._workflow_tabs.select(self._eurostag_tab)
        self._results_tabs.select(0)
        self._status_var.set("Ready")

    def load_faults(self) -> None:
        """

        :return:
        """
        lock_owned = not self._autoload_lock
        if lock_owned:
            self._autoload_lock = True
        try:
            workflow_name = self._selected_workflow_name()
            if workflow_name == "eurostag":
                self.load_eurostag_faults()
            else:
                self.load_dynawo_faults()
        finally:
            if lock_owned:
                self._autoload_lock = False

    def load_eurostag_faults(self) -> None:
        """

        :return:
        """
        try:
            execution_plan_override = self.apply_eurostag_global_config()
        except ValueError as exc:
            messagebox.showerror("Load error", str(exc))
            return

        if not self._e_ech.get() or not self._e_dta.get() or not self._e_lf.get():
            messagebox.showerror("Missing input", "ECH, DTA, and LF files are required.")
            return
        if not self._e_plan.get():
            messagebox.showerror("Missing input", "Execution plan is required.")
            return
        if self._e_use_folder.get():
            if not self._e_seq_folder.get():
                messagebox.showerror("Missing input", "Seq folder is required.")
                return
        else:
            if not self._e_seq.get():
                messagebox.showerror("Missing input", "Seq file is required.")
                return

        try:
            if execution_plan_override is None:
                execution_plan = read_execution_plan(self._e_plan.get(), None)
            else:
                execution_plan = execution_plan_override
            if not isinstance(execution_plan, ExecutionPlan):
                raise ValueError("Execution plan must be parsed into an ExecutionPlan object.")

            seq_files = []
            if self._e_use_folder.get():
                seq_folder = self._e_seq_folder.get()
                for name in os.listdir(seq_folder):
                    if os.path.splitext(name)[1].lower() == ".seq":
                        seq_files.append(os.path.join(seq_folder, name))
                seq_files.sort()
            network = parse_eurostag(
                ech_file=self._e_ech.get(),
                dta_file=self._e_dta.get(),
                lf_file=self._e_lf.get(),
                seq_file=None if self._e_use_folder.get() else self._e_seq.get(),
                seq_files=seq_files,
                protection_delay=float(self._e_delay.get() or 0),
            )
        except Exception as exc:
            messagebox.showerror("Load error", str(exc))
            return

        self._network = network
        self._execution_plan = execution_plan
        self._active_workflow_name = "eurostag"
        self.clear_results()
        self._fault_list.clear()
        self._faults = []
        self.populate_faults(network.fault_events)
        self._status_var.set(f"Loaded {len(network.fault_events)} faults")

    def load_dynawo_faults(self) -> None:
        """

        :return:
        """
        if _DYNAWO_PARSE_AVAILABLE:
            pass
        else:
            messagebox.showerror(
                "Dynawo unavailable",
                "Dynawo workflow is optional and currently unavailable: missing Dynawo parser dependencies.",
            )
            return

        try:
            execution_plan_override = self.apply_dynawo_global_config()
        except ValueError as exc:
            messagebox.showerror("Load error", str(exc))
            return

        if not self._d_plan.get():
            messagebox.showerror("Missing input", "Execution plan is required.")
            return

        if self.use_dynawo_jobs_mode():
            if not self._d_jobs.get().strip():
                messagebox.showerror("Missing input", "Dynawo .jobs file is required.")
                return
        else:
            if not self._d_iidm.get() or not self._d_dyd.get() or not self._d_par.get():
                messagebox.showerror("Missing input", "IIDM, DYD, and PAR files are required in manual mode.")
                return

        try:
            if execution_plan_override is None:
                execution_plan = read_execution_plan(self._d_plan.get(), None)
            else:
                execution_plan = execution_plan_override
            if not isinstance(execution_plan, ExecutionPlan):
                raise ValueError("Execution plan must be parsed into an ExecutionPlan object.")

            config = self.build_dynawo_run_configuration(execution_plan)
            network = parse_dynawo_configuration(config)
        except ModuleNotFoundError as exc:
            messagebox.showerror(
                "Missing dependency",
                "pypowsybl is required to load IIDM networks: " + str(exc),
            )
            return
        except Exception as exc:
            messagebox.showerror("Load error", str(exc))
            return

        self._network = network
        self._execution_plan = execution_plan
        self._active_workflow_name = "dynawo"
        self.clear_results()
        self._fault_list.clear()
        self._faults = []
        self.populate_faults(network.fault_events)
        self._status_var.set(f"Loaded {len(network.fault_events)} faults")

    def apply_eurostag_global_config(self) -> Optional[ExecutionPlan]:
        """

        :return:
        """
        plan_path = self._e_plan.get()
        if not plan_path:
            return None
        config_data = self.read_plan_json(plan_path)
        if "ech-file" not in config_data:
            if "iidm-file" in config_data:
                raise ValueError("Dynawo configuration provided in Eurostag tab.")
            return None
        config = load_global_configuration(plan_path)
        resolved_execution_plan = read_execution_plan(config.execution_tree_file, config.execution_tree)

        self._e_ech.set(config.ech_file or "")
        self._e_dta.set(config.dta_file or "")
        self._e_lf.set(config.lf_file or "")
        if config.seq_file_folder:
            self._e_use_folder.set(True)
            self.toggle_seq_mode()
            self._e_seq_folder.set(config.seq_file_folder)
            self._e_seq.set("")
        else:
            self._e_use_folder.set(False)
            self.toggle_seq_mode()
            self._e_seq.set(config.seq_file or "")
            self._e_seq_folder.set("")
        if config.execution_tree_file:
            self._e_plan.set(config.execution_tree_file)
        self._e_output.set(config.output_dir or "")
        self._e_island.set(str(config.island_threshold))
        self._e_delay.set(str(config.protection_delay))
        self._e_cores.set(str(config.cores))
        self._e_verbose.set(config.verbose)
        self._e_warn.set(config.warn)
        self._e_generate_output_files.set(self.read_bool_from_config(config_data, "generate-output-files", True))

        return resolved_execution_plan

    def apply_dynawo_global_config(self) -> Optional[ExecutionPlan]:
        """

        :return:
        """
        plan_path = self._d_plan.get()
        if not plan_path:
            return None
        config_data = self.read_plan_json(plan_path)
        if not self.is_dynawo_config_data(config_data):
            if self.is_eurostag_config_data(config_data):
                raise ValueError("Eurostag configuration provided in Dynawo tab.")
            return None
        config = load_dynawo_configuration(plan_path)
        resolved_execution_plan = read_execution_plan(config.execution_tree_file, config.execution_tree)

        if config.jobs_file:
            self._d_mode.set("jobs")
            self._d_jobs.set(config.jobs_file or "")
            self._d_iidm.set("")
            self._d_dyd.set("")
            self._d_par.set("")
        else:
            self._d_mode.set("manual")
            self._d_jobs.set("")
            self._d_iidm.set(config.iidm_file or "")
            self._d_dyd.set(config.dynawo_dyd_file or "")
            self._d_par.set(config.dynawo_par_file or "")
        self.toggle_dynawo_mode()
        if config.execution_tree_file:
            self._d_plan.set(config.execution_tree_file)
        self._d_output.set(config.output_dir or "")
        self._d_island.set(str(config.island_threshold))
        self._d_cores.set(str(config.cores))
        self._d_verbose.set(config.verbose)
        self._d_warn.set(config.warn)
        self._d_generate_output_files.set(self.read_bool_from_config(config_data, "generate-output-files", True))
        self._d_post_run_enabled.set(self.read_bool_from_config(config_data, "dynawo-post-run-enabled", False))
        self._d_dynawo_install_dir.set(self.resolve_optional_path_from_config(plan_path, config_data, "dynawo-install-dir"))
        self._d_dynawo_binary_path.set(self.resolve_optional_path_from_config(plan_path, config_data, "dynawo-binary-path"))
        timeout_value = config_data.get("dynawo-timeout-seconds")
        if timeout_value is None:
            self._d_dynawo_timeout_seconds.set("120")
        else:
            self._d_dynawo_timeout_seconds.set(str(timeout_value))
        cct_min_value = config_data.get("dynawo-cct-min")
        if cct_min_value is None:
            self._d_dynawo_cct_min.set("")
        else:
            self._d_dynawo_cct_min.set(str(cct_min_value))
        cct_max_value = config_data.get("dynawo-cct-max")
        if cct_max_value is None:
            self._d_dynawo_cct_max.set("")
        else:
            self._d_dynawo_cct_max.set(str(cct_max_value))
        selected_statuses_from_config = self.read_statuses_from_config(config_data)
        for status_name in _all_eeac_final_status_values():
            self._d_dynawo_status_vars[status_name].set(status_name in selected_statuses_from_config)

        return resolved_execution_plan

    @staticmethod
    def resolve_optional_path_from_config(config_path: str, config_data: Dict[str, object], key: str) -> str:
        """
        Resolve an optional path value from GUI config data.

        :param config_path: Source configuration file path.
        :param config_data: Parsed configuration JSON object.
        :param key: Configuration key.
        :return: Resolved absolute path, or an empty string when unset.
        """
        raw_value = config_data.get(key)
        if isinstance(raw_value, str):
            value = raw_value.strip()
            if value == "":
                return ""
            else:
                pass
            if os.path.isabs(value):
                return value
            else:
                return os.path.abspath(os.path.join(os.path.dirname(config_path), value))
        else:
            return ""

    @staticmethod
    def read_bool_from_config(config_data: Dict[str, object], key: str, default: bool) -> bool:
        """
        Read a boolean-like field from configuration data.

        :param config_data: Parsed configuration JSON object.
        :param key: Configuration key.
        :param default: Default value.
        :return: Parsed boolean.
        """
        raw_value = config_data.get(key)
        if isinstance(raw_value, bool):
            return raw_value
        else:
            if isinstance(raw_value, str):
                return raw_value.lower() == "true"
            else:
                return default

    def read_statuses_from_config(self, config_data: Dict[str, object]) -> List[str]:
        """
        Read selected EEAC status values from configuration data.

        Rationale:
            This method keeps backward compatibility with the old
            ``dynawo-include-potentially-stable`` flag while supporting
            multi-status selection through ``dynawo-eeac-statuses``.

        :param config_data: Parsed configuration JSON object.
        :return: Selected status values.
        """
        selected_statuses: List[str] = list()
        raw_statuses = config_data.get("dynawo-eeac-statuses")
        if isinstance(raw_statuses, list):
            for item in raw_statuses:
                if isinstance(item, str):
                    if item in _all_eeac_final_status_values():
                        selected_statuses.append(item)
                    else:
                        pass
                else:
                    pass
        else:
            pass

        if len(selected_statuses) == 0:
            selected_statuses.append(OMIBStabilityState.ALWAYS_UNSTABLE.value)
        else:
            pass

        include_potentially_stable = self.read_bool_from_config(
            config_data,
            "dynawo-include-potentially-stable",
            False,
        )
        if include_potentially_stable:
            if OMIBStabilityState.POTENTIALLY_STABLE.value in selected_statuses:
                pass
            else:
                selected_statuses.append(OMIBStabilityState.POTENTIALLY_STABLE.value)
        else:
            pass

        return selected_statuses

    @staticmethod
    def read_plan_json(plan_path: str) -> Dict[str, object]:
        """

        :param plan_path:
        :return:
        """
        try:
            with open(plan_path, "r") as handle:
                data = json.load(handle)
        except Exception as exc:
            raise ValueError(f"Failed to parse JSON file {plan_path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("Execution plan file must be a JSON object.")
        return data

    def maybe_autoload_faults(self, workflow: str) -> None:
        """

        :param workflow:
        :return:
        """
        if self._autoload_lock:
            return
        if self._worker and self._worker.is_alive():
            return

        current_tab = self._workflow_tabs.index(self._workflow_tabs.select())
        if workflow == "eurostag" and current_tab != 0:
            return
        if workflow == "dynawo" and current_tab != 1:
            return

        if workflow == "eurostag":
            ready, signature = self.eurostag_autoload_signature()
        else:
            ready, signature = self.dynawo_autoload_signature()

        if not ready or signature is None:
            return
        if signature == self._last_load_signature:
            return

        self._autoload_lock = True
        try:
            self.load_faults()
        finally:
            self._autoload_lock = False

        if self._network is not None and self._execution_plan is not None:
            self._last_load_signature = signature

    def eurostag_autoload_signature(self) -> Tuple[bool, Optional[Tuple[str, ...]]]:
        """

        :return:
        """
        plan_path = self._e_plan.get().strip()
        if plan_path and os.path.isfile(plan_path):
            if self.is_eurostag_config(plan_path):
                signature = (
                    "eurostag",
                    plan_path,
                    "config",
                )
                return True, signature
        ech_file = self._e_ech.get().strip()
        dta_file = self._e_dta.get().strip()
        lf_file = self._e_lf.get().strip()
        if not (ech_file and dta_file and lf_file and plan_path):
            return False, None
        if not (os.path.isfile(ech_file) and os.path.isfile(dta_file) and os.path.isfile(lf_file)):
            return False, None
        if not os.path.isfile(plan_path):
            return False, None

        seq_file = self._e_seq.get().strip()
        seq_folder = self._e_seq_folder.get().strip()
        use_folder = self._e_use_folder.get()
        if use_folder:
            if not seq_folder or not os.path.isdir(seq_folder):
                return False, None
        else:
            if not seq_file or not os.path.isfile(seq_file):
                return False, None

        signature = (
            "eurostag",
            ech_file,
            dta_file,
            lf_file,
            plan_path,
            seq_file,
            seq_folder,
            str(use_folder),
            self._e_delay.get().strip(),
        )
        return True, signature

    def dynawo_autoload_signature(self) -> Tuple[bool, Optional[Tuple[str, ...]]]:
        """

        :return:
        """
        plan_path = self._d_plan.get().strip()
        if plan_path and os.path.isfile(plan_path):
            if self.is_dynawo_config(plan_path):
                signature = (
                    "dynawo",
                    plan_path,
                    "config",
                )
                return True, signature
        if not os.path.isfile(plan_path):
            return False, None

        if self.use_dynawo_jobs_mode():
            jobs_file = self._d_jobs.get().strip()
            if not jobs_file or not os.path.isfile(jobs_file):
                return False, None
            signature = (
                "dynawo",
                "jobs",
                jobs_file,
                plan_path,
            )
            return True, signature

        iidm_file = self._d_iidm.get().strip()
        dyd_file = self._d_dyd.get().strip()
        par_file = self._d_par.get().strip()
        if not (iidm_file and dyd_file and par_file):
            return False, None
        if not (os.path.isfile(iidm_file) and os.path.isfile(dyd_file) and os.path.isfile(par_file)):
            return False, None
        signature = (
            "dynawo",
            "manual",
            iidm_file,
            dyd_file,
            par_file,
            plan_path,
        )
        return True, signature

    def is_eurostag_config(self, plan_path: str) -> bool:
        """

        :param plan_path:
        :return:
        """
        try:
            data = self.read_plan_json(plan_path)
        except ValueError:
            return False
        return self.is_eurostag_config_data(data)

    def is_dynawo_config(self, plan_path: str) -> bool:
        """

        :param plan_path:
        :return:
        """
        try:
            data = self.read_plan_json(plan_path)
        except ValueError:
            return False
        return self.is_dynawo_config_data(data)

    @staticmethod
    def is_eurostag_config_data(data: Dict[str, object]) -> bool:
        """
        Tell whether a parsed JSON object looks like a Eurostag configuration.

        :param data: Parsed JSON object.
        :return: ``True`` for Eurostag-like configuration content.
        """
        return "ech-file" in data

    @staticmethod
    def is_dynawo_config_data(data: Dict[str, object]) -> bool:
        """
        Tell whether a parsed JSON object looks like a Dynawo configuration.

        :param data: Parsed JSON object.
        :return: ``True`` for Dynawo-like configuration content.
        """
        return "iidm-file" in data or "dynawo-jobs-file" in data or "jobs-file" in data

    def build_dynawo_run_configuration(self, execution_plan: ExecutionPlan) -> DynawoRunConfiguration:
        """
        Build a Dynawo run configuration from the current GUI state.

        :param execution_plan: Parsed execution plan selected in the GUI.
        :return: Dynawo run configuration matching the selected mode.
        """
        jobs_file: Optional[str]
        iidm_file: Optional[str]
        dyd_file: Optional[str]
        par_file: Optional[str]

        if self.use_dynawo_jobs_mode():
            jobs_file = self._d_jobs.get().strip() or None
            iidm_file = None
            dyd_file = None
            par_file = None
        else:
            jobs_file = None
            iidm_file = self._d_iidm.get().strip() or None
            dyd_file = self._d_dyd.get().strip() or None
            par_file = self._d_par.get().strip() or None

        output_dir = self._d_output.get().strip() or None

        return DynawoRunConfiguration(
            jobs_file=jobs_file,
            iidm_file=iidm_file,
            dynawo_dyd_file=dyd_file,
            dynawo_par_file=par_file,
            dynawo_dyn_file=None,
            execution_tree_file=self._d_plan.get().strip() or None,
            execution_tree=execution_plan,
            island_threshold=self.current_island_threshold(),
            cores=self.current_cores(),
            protection_delay=0.0,
            verbose=self._d_verbose.get(),
            output_dir=output_dir,
            json_path=None,
            rewrite=True,
            warn=self._d_warn.get(),
        )

    def populate_faults(self, faults: List[FaultEvents]) -> None:
        """

        :param faults:
        :return:
        """
        if not faults:
            messagebox.showwarning("No faults", "No faults were found in the input files.")
            return
        for index, fault in enumerate(faults, start=1):
            label = fault.name or f"fault_{index}"
            var = tk.BooleanVar(value=True)
            check = ttk.Checkbutton(self._fault_list.frame, text=label, variable=var)
            check.pack(anchor="w")
            self._faults.append(FaultSelection(fault=fault, var=var))

    def run_selected_faults(self) -> None:
        """

        :return:
        """
        if self._network is None or not self._faults or self._execution_plan is None:
            self.load_faults()
        if self._network is None or self._execution_plan is None:
            return
        selected = [item.fault for item in self._faults if item.var.get()]
        if not selected:
            messagebox.showwarning("No faults", "Select at least one fault to run.")
            return
        execution_plan = self._execution_plan

        output_dirs = self.build_output_dirs(self.current_output_dir(), selected)
        verbose = self.current_verbose()
        island_threshold = self.current_island_threshold()
        warn = self.current_warn()
        cores = self.current_cores()
        dynawo_post_options = self.build_dynawo_post_run_options(execution_plan)
        if dynawo_post_options is None:
            return

        self.set_running(True)
        self.clear_results()

        args = [
            (
                execution_plan,
                output_path,
                self._network.duplicate(),
                verbose,
                island_threshold,
                fault_event,
                warn,
            )
            for fault_event, output_path in zip(selected, output_dirs)
        ]

        self._worker = threading.Thread(
            target=self.run_worker,
            args=(args, cores, dynawo_post_options),
            daemon=True,
        )
        self._worker.start()
        self.after(100, self.poll_queue)

    def run_worker(
        self,
        jobs: List[Tuple],
        cores: int,
        dynawo_post_options: DynawoPostRunOptions,
    ) -> None:
        try:
            aggregated_results: List[Tuple[str, EEACResult, object]] = list()
            if cores <= 1 or len(jobs) == 1:
                for job in jobs:
                    result = run_fault(*job)
                    aggregated_results.append(result)
                    self._result_queue.put(("result", result))
            else:
                results = Parallel(n_jobs=cores, backend="loky")(
                    delayed(run_fault)(*job) for job in jobs
                )
                for result in results:
                    aggregated_results.append(result)
                    self._result_queue.put(("result", result))
            if dynawo_post_options.enabled:
                dynawo_report = self.run_dynawo_post_processing(
                    dynawo_post_options=dynawo_post_options,
                    results=aggregated_results,
                )
                extended_results = self.build_extended_results_from_dynawo_report(
                    run_results=aggregated_results,
                    dynawo_report=dynawo_report,
                )
                self._result_queue.put(("extended_results", extended_results))
                self._result_queue.put(("dynawo_report", dynawo_report))
            else:
                pass
            self._result_queue.put(("done", None))
        except Exception as exc:
            self._result_queue.put(("error", exc))

    def poll_queue(self) -> None:
        """
        Drain worker results and refresh the GUI incrementally.

        :return: Return value.
        """
        try:
            while True:
                kind, payload = self._result_queue.get_nowait()
                if kind == "result":
                    fault_name, fault_result, logger = payload
                    self.add_result(fault_name, fault_result, logger)
                elif kind == "error":
                    messagebox.showerror("Run error", str(payload))
                    self.set_running(False)
                elif kind == "dynawo_report":
                    self.add_dynawo_report(payload)
                elif kind == "extended_results":
                    self.refresh_tree_from_eeac_results(payload)
                elif kind == "done":
                    self.set_running(False)
        except queue.Empty:
            pass
        if self._worker and self._worker.is_alive():
            self.after(100, self.poll_queue)

    def build_extended_results_from_dynawo_report(
        self,
        run_results: List[Tuple[str, EEACResult, object]],
        dynawo_report: Dict[str, object],
    ) -> EEACResults:
        """
        Build a new EEACResults object with Dynawo-extended fields.

        :param run_results: Raw run results from the EEAC worker.
        :param dynawo_report: Dynawo post-run report payload.
        :return: Extended EEAC results.
        """
        extended_results = EEACResults()

        per_fault_raw = dynawo_report.get("per_fault", list())
        per_fault_map: Dict[str, Dict[str, object]] = dict()
        if isinstance(per_fault_raw, list):
            for entry in per_fault_raw:
                if isinstance(entry, dict):
                    fault_name_obj = entry.get("fault_name", "")
                    fault_name = str(fault_name_obj)
                    per_fault_map[fault_name] = entry
                else:
                    pass
        else:
            pass

        for fault_name, result, _logger in run_results:
            dynawo_entry = per_fault_map.get(fault_name, dict())
            extended_result = EEACResult(
                status=result.status,
                swing_state=result.swing_state,
                critical_cluster=result.critical_cluster,
                node_id=result.node_id,
                cct=result.cct,
                warning=result.warning,
                failure_report=result.failure_report,
                interval=result.interval,
                production_loss=result.production_loss,
                disconnected_production=result.disconnected_production,
                consumption_loss=result.consumption_loss,
                disconnected_consumption=result.disconnected_consumption,
                error_msg=result.error_msg,
                dynawo_generation_status=self.as_optional_str(dynawo_entry.get("generation_status")),
                dynawo_generation_reason=self.as_optional_str(dynawo_entry.get("generation_reason")),
                dynawo_run_status=self.as_optional_str(dynawo_entry.get("run_status")),
                dynawo_return_code=self.as_optional_int(dynawo_entry.get("return_code")),
                dynawo_case_output_dir=self.as_optional_str(dynawo_entry.get("case_output_dir")),
                dynawo_jobs_file=self.as_optional_str(dynawo_entry.get("jobs_file")),
                dynawo_dyd_file=self.as_optional_str(dynawo_entry.get("dyd_file")),
                dynawo_par_file=self.as_optional_str(dynawo_entry.get("par_file")),
                dynawo_stderr_head=self.as_optional_str(dynawo_entry.get("stderr_head")),
            )
            extended_results.add(fault_name, extended_result)
        return extended_results

    @staticmethod
    def as_optional_str(value: object) -> Optional[str]:
        """
        Convert a payload value to optional string.

        :param value: Input payload value.
        :return: String value or ``None``.
        """
        if value is None:
            return None
        else:
            return str(value)

    @staticmethod
    def as_optional_int(value: object) -> Optional[int]:
        """
        Convert a payload value to optional integer.

        :param value: Input payload value.
        :return: Integer value or ``None``.
        """
        if value is None:
            return None
        else:
            pass
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def refresh_tree_from_eeac_results(self, eeac_results: object) -> None:
        """
        Refresh the results tree from one EEACResults object.

        :param eeac_results: Result object payload.
        :return: Return value.
        """
        if isinstance(eeac_results, EEACResults):
            pass
        else:
            return
        for item in self._results_tree.get_children():
            self._results_tree.delete(item)
        for fault_entry in eeac_results.results:
            self.add_result(fault_entry.fault_name, fault_entry.result, logger=object())

    def build_dynawo_post_run_options(self, execution_plan: ExecutionPlan) -> Optional[DynawoPostRunOptions]:
        """
        Build optional Dynawo post-processing options from GUI state.

        :param execution_plan: Current execution plan.
        :return: Dynawo post-processing options, or ``None`` when validation fails.
        """
        workflow_name = self._selected_workflow_name()
        if workflow_name != "dynawo":
            return DynawoPostRunOptions(
                enabled=False,
                run_configuration=None,
                generation_root_dir=None,
                dynawo_install_dir=None,
                dynawo_binary_path=None,
                timeout_seconds=None,
                cct_min=None,
                cct_max=None,
                selected_statuses=list(),
            )
        else:
            pass

        if self._d_post_run_enabled.get():
            pass
        else:
            return DynawoPostRunOptions(
                enabled=False,
                run_configuration=None,
                generation_root_dir=None,
                dynawo_install_dir=None,
                dynawo_binary_path=None,
                timeout_seconds=None,
                cct_min=None,
                cct_max=None,
                selected_statuses=list(),
            )

        output_root = self._d_output.get().strip()
        if output_root == "":
            messagebox.showerror("Missing input", "Output dir is required when Dynawo post-run is enabled.")
            return None
        else:
            os.makedirs(output_root, exist_ok=True)

        run_configuration = self.build_dynawo_run_configuration(execution_plan)
        timeout_seconds = self.parse_optional_float(self._d_dynawo_timeout_seconds.get(), "Dynawo timeout")
        if timeout_seconds is None and self._d_dynawo_timeout_seconds.get().strip() != "":
            return None
        else:
            pass
        cct_min = self.parse_optional_float(self._d_dynawo_cct_min.get(), "Dynawo CCT min")
        if cct_min is None and self._d_dynawo_cct_min.get().strip() != "":
            return None
        else:
            pass
        cct_max = self.parse_optional_float(self._d_dynawo_cct_max.get(), "Dynawo CCT max")
        if cct_max is None and self._d_dynawo_cct_max.get().strip() != "":
            return None
        else:
            pass

        dynawo_install_dir = self._d_dynawo_install_dir.get().strip() or None
        dynawo_binary_path = self._d_dynawo_binary_path.get().strip() or None
        dynawo_runtime = self.validate_dynawo_runtime(
            dynawo_install_dir,
            dynawo_binary_path,
        )
        if dynawo_runtime.is_available:
            dynawo_install_dir = dynawo_runtime.dynawo_install_dir
            dynawo_binary_path = dynawo_runtime.dynawo_binary_path
        else:
            messagebox.showerror(
                "Dynawo unavailable",
                dynawo_runtime.error_text or "Dynawo executable could not be resolved.",
            )
            return None
        selected_statuses = self.selected_dynawo_statuses()
        if len(selected_statuses) > 0:
            pass
        else:
            messagebox.showerror("Missing input", "Select at least one EEAC status for Dynawo post-run.")
            return None
        generation_root_dir = os.path.join(output_root, "dynawo_cases")
        options = DynawoPostRunOptions(
            enabled=True,
            run_configuration=run_configuration,
            generation_root_dir=generation_root_dir,
            dynawo_install_dir=dynawo_install_dir,
            dynawo_binary_path=dynawo_binary_path,
            timeout_seconds=timeout_seconds,
            cct_min=cct_min,
            cct_max=cct_max,
            selected_statuses=selected_statuses,
        )
        return options

    @staticmethod
    def validate_dynawo_runtime(
        dynawo_install_dir: Optional[str],
        dynawo_binary_path: Optional[str],
    ) -> DynawoRuntimeValidationResult:
        """
        Resolve and validate the Dynawo runtime for post-run execution.

        :param dynawo_install_dir: Optional Dynawo installation directory.
        :param dynawo_binary_path: Optional explicit Dynawo executable path.
        :return: Dynawo runtime validation result.
        """
        if _DYNAWO_RUNNER_AVAILABLE:
            pass
        else:
            return DynawoRuntimeValidationResult(
                is_available=False,
                error_text="Dynawo runner is unavailable in this installation.",
                dynawo_install_dir=dynawo_install_dir,
                dynawo_binary_path=dynawo_binary_path,
            )

        try:
            dynawo_runner = DynawoRunner(
                dynawo_binary_path=dynawo_binary_path,
                dynawo_install_dir=dynawo_install_dir,
                dynawo_binary_options=None,
            )
        except ValueError as exc:
            return DynawoRuntimeValidationResult(
                is_available=False,
                error_text=str(exc),
                dynawo_install_dir=dynawo_install_dir,
                dynawo_binary_path=dynawo_binary_path,
            )

        validation_report = dynawo_runner.validate_installation()
        if validation_report.is_valid:
            return DynawoRuntimeValidationResult(
                is_available=True,
                error_text=None,
                dynawo_install_dir=dynawo_runner.dynawo_install_dir,
                dynawo_binary_path=dynawo_runner.dynawo_binary_path,
            )
        else:
            return DynawoRuntimeValidationResult(
                is_available=False,
                error_text=validation_report.to_error_text(),
                dynawo_install_dir=dynawo_runner.dynawo_install_dir,
                dynawo_binary_path=dynawo_runner.dynawo_binary_path,
            )

    def selected_dynawo_statuses(self) -> List[str]:
        """
        Return selected EEAC status values for Dynawo post-run coupling.

        :return: Selected status values.
        """
        selected_statuses: List[str] = list()
        for status_name in _all_eeac_final_status_values():
            if self._d_dynawo_status_vars[status_name].get():
                selected_statuses.append(status_name)
            else:
                pass
        return selected_statuses

    @staticmethod
    def parse_optional_float(raw_value: str, field_name: str) -> Optional[float]:
        """
        Parse an optional float from GUI text input.

        :param raw_value: Raw text value.
        :param field_name: User-facing field name.
        :return: Parsed float, or ``None`` for blank inputs.
        """
        value = raw_value.strip()
        if value == "":
            return None
        else:
            pass
        try:
            return float(value)
        except ValueError:
            messagebox.showerror("Invalid input", f"{field_name} must be a number.")
            return None

    def run_dynawo_post_processing(
        self,
        dynawo_post_options: DynawoPostRunOptions,
        results: List[Tuple[str, EEACResult, object]],
    ) -> Dict[str, object]:
        """
        Generate and optionally run Dynawo cases from EEAC results.

        :param dynawo_post_options: Dynawo post-processing options.
        :param results: EEAC run results.
        :return: Structured Dynawo post-processing summary.
        """
        if dynawo_post_options.run_configuration is None:
            return {"error": "Dynawo run configuration was not built."}
        else:
            pass
        if _DYNAWO_POST_PROCESS_AVAILABLE and _DYNAWO_PARSE_AVAILABLE:
            pass
        else:
            return {
                "error": (
                    "Dynawo post-process unavailable: missing Dynawo post-process modules "
                    "or Dynawo parser dependencies."
                )
            }
        if dynawo_post_options.generation_root_dir is None:
            return {"error": "Dynawo generation root directory is missing."}
        else:
            pass
        dynawo_runtime = self.validate_dynawo_runtime(
            dynawo_post_options.dynawo_install_dir,
            dynawo_post_options.dynawo_binary_path,
        )
        if dynawo_runtime.is_available:
            dynawo_post_options.dynawo_install_dir = dynawo_runtime.dynawo_install_dir
            dynawo_post_options.dynawo_binary_path = dynawo_runtime.dynawo_binary_path
        else:
            return {"error": dynawo_runtime.error_text or "Dynawo executable could not be resolved."}

        eeac_results = EEACResults()
        for fault_name, result, _logger in results:
            eeac_results.add(fault_name, result)

        selection_options = DynawoFaultSelectionOptions(
            statuses=[
                OMIBStabilityState.ALWAYS_UNSTABLE,
                OMIBStabilityState.POTENTIALLY_STABLE,
                OMIBStabilityState.ALWAYS_STABLE,
                OMIBStabilityState.UNKNOWN,
            ],
            status_names=dynawo_post_options.selected_statuses,
            cct_min=dynawo_post_options.cct_min,
            cct_max=dynawo_post_options.cct_max,
        )
        coupler = DynawoCaseCoupler(
            run_configuration=dynawo_post_options.run_configuration,
            eeac_results=eeac_results,
            selection_options=selection_options,
        )
        generation_report = coupler.generate_cases(dynawo_post_options.generation_root_dir, rewrite=True)
        run_report = coupler.run_generated_cases(
            generation_report=generation_report,
            dynawo_binary_path=dynawo_post_options.dynawo_binary_path,
            dynawo_install_dir=dynawo_post_options.dynawo_install_dir,
            dynawo_binary_options=None,
            timeout_seconds=dynawo_post_options.timeout_seconds,
        )

        generation_manifest = os.path.join(dynawo_post_options.generation_root_dir, "generation_manifest.json")
        run_manifest = os.path.join(dynawo_post_options.generation_root_dir, "run_manifest.json")
        coupler.write_generation_manifest(generation_report, generation_manifest)
        coupler.write_run_manifest(run_report, run_manifest)

        generation_by_fault: Dict[str, object] = dict()
        for generation_entry in generation_report.entries:
            generation_by_fault[generation_entry.fault_name] = generation_entry

        run_by_fault: Dict[str, object] = dict()
        for run_entry in run_report.entries:
            run_by_fault[run_entry.fault_name] = run_entry

        per_fault: List[Dict[str, object]] = list()
        for fault_name in sorted(generation_by_fault.keys()):
            generation_entry = generation_by_fault[fault_name]
            run_entry = run_by_fault.get(fault_name, None)
            fault_payload: Dict[str, object] = dict()
            fault_payload["fault_name"] = fault_name
            fault_payload["generation_status"] = generation_entry.generation_status.value
            fault_payload["generation_reason"] = generation_entry.reason
            fault_payload["case_output_dir"] = generation_entry.output_dir
            fault_payload["jobs_file"] = generation_entry.jobs_file
            fault_payload["dyd_file"] = generation_entry.dyd_file
            fault_payload["par_file"] = generation_entry.par_file
            if run_entry is None:
                fault_payload["run_status"] = "NOT_RUN"
                fault_payload["return_code"] = None
                fault_payload["stderr_head"] = ""
            else:
                fault_payload["run_status"] = run_entry.execution_status.value
                fault_payload["return_code"] = run_entry.return_code
                stderr_head = run_entry.stderr.strip()
                if len(stderr_head) > 240:
                    stderr_head = stderr_head[:240]
                else:
                    stderr_head = stderr_head
                fault_payload["stderr_head"] = stderr_head
            per_fault.append(fault_payload)

        generated_count = 0
        run_success_count = 0
        run_failed_count = 0
        for entry in generation_report.entries:
            if entry.generation_status.value == "GENERATED":
                generated_count += 1
            else:
                pass
        for entry in run_report.entries:
            if entry.execution_status.value == "SUCCESS":
                run_success_count += 1
            else:
                run_failed_count += 1
        return {
            "generation_root_dir": dynawo_post_options.generation_root_dir,
            "generation_manifest": generation_manifest,
            "run_manifest": run_manifest,
            "selected_faults": len(generation_report.entries),
            "generated_cases": generated_count,
            "run_success": run_success_count,
            "run_failed": run_failed_count,
            "per_fault": per_fault,
        }

    def add_dynawo_report(self, report: object) -> None:
        """
        Add Dynawo post-run summary to the results view.

        :param report: Dynawo report payload from the worker.
        :return: Return value.
        """
        if isinstance(report, dict):
            dynawo_root = self._results_tree.insert("", "end", text="Dynawo Post-Run", values=("",))
            for key in sorted(report.keys()):
                if key == "per_fault":
                    pass
                else:
                    self._results_tree.insert(dynawo_root, "end", text=key, values=(str(report[key]),))

            self._log_text.configure(state="normal")
            self._log_text.insert("end", "\n[Dynawo Post-Run]\n")
            for key in sorted(report.keys()):
                if key == "per_fault":
                    self._log_text.insert("end", "per_fault: see results tree fault nodes\n")
                else:
                    self._log_text.insert("end", f"{key}: {report[key]}\n")
            self._log_text.configure(state="disabled")
            self._log_text.see("end")
        else:
            pass

    def add_result(self, fault_name: str, result: EEACResult, logger: object) -> None:
        """

        :param fault_name:
        :param result:
        :param logger:
        :return:
        """
        fault_id = self._results_tree.insert("", "end", text=fault_name, values=("",))
        result_dict = result.to_dict()
        for key in sorted(result_dict.keys()):
            value = result_dict[key]
            self._results_tree.insert(fault_id, "end", text=key, values=(str(value),))
        self.append_logs(fault_name, logger)

    def append_logs(self, fault_name: str, logger: object) -> None:
        """

        :param fault_name:
        :param logger:
        :return:
        """
        if not isinstance(logger, Logger):
            return
        records = logger.records
        if not records:
            return
        self._log_text.configure(state="normal")
        self._log_text.insert("end", f"\n[{fault_name}]\n")
        for record in records:
            context = " ".join(f"{k}={v}" for k, v in record.context.items())
            suffix = f" {context}" if context else ""
            self._log_text.insert("end", f"{record.timestamp} {record.level.upper()} {record.message}{suffix}\n")
        self._log_text.configure(state="disabled")
        self._log_text.see("end")

    def clear_results(self) -> None:
        """
        Clear the results tree and the aggregated execution log pane.

        :return: Return value.
        """
        for item in self._results_tree.get_children():
            self._results_tree.delete(item)
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")

    def set_running(self, running: bool) -> None:
        """

        :param running:
        :return:
        """
        state = "disabled" if running else "normal"
        self._load_button.configure(state=state)
        self._run_button.configure(state=state)
        self._clear_button.configure(state=state)
        self._select_all_button.configure(state=state)
        self._select_none_button.configure(state=state)
        self._status_var.set("Running..." if running else "Ready")

    @staticmethod
    def build_output_dirs(
        output_dir: Optional[str],
        faults: List[FaultEvents],
    ) -> List[Optional[str]]:
        """
        Build one output directory per selected fault.

        :param output_dir: Root output directory configured in the GUI.
        :param faults: Faults selected for execution.
        :return: Per-fault output directories aligned with ``faults``.
        """
        if output_dir is None or output_dir == "":
            return [None] * len(faults)
        os.makedirs(output_dir, exist_ok=True)
        if len(faults) == 1:
            return [output_dir]
        output_dirs = [
            os.path.join(output_dir, fault.name or f"fault_{index + 1}")
            for index, fault in enumerate(faults)
        ]
        for path in output_dirs:
            os.makedirs(path, exist_ok=True)
        return output_dirs

    def _selected_workflow_name(self) -> str:
        """
        Return the workflow used for load/run operations.

        Rationale:
            The dedicated faults tab is not a configuration workflow. When that
            tab is selected, the GUI must keep using the last active input
            workflow (Eurostag or Dynawo).

        :return: Selected workflow name.
        """
        workflow = self._workflow_tabs.index(self._workflow_tabs.select())
        if workflow == 0:
            return "eurostag"
        else:
            if workflow == 1:
                return "dynawo"
            else:
                return self._active_workflow_name

    def current_plan_path(self) -> str:
        """

        :return:
        """
        workflow_name = self._selected_workflow_name()
        if workflow_name == "eurostag":
            return self._e_plan.get()
        else:
            return self._d_plan.get()

    def current_output_dir(self) -> Optional[str]:
        """

        :return:
        """
        workflow_name = self._selected_workflow_name()
        if workflow_name == "eurostag":
            if self._e_generate_output_files.get():
                return self._e_output.get()
            else:
                return None
        else:
            if self._d_generate_output_files.get():
                return self._d_output.get()
            else:
                return None

    def current_island_threshold(self) -> float:
        """

        :return:
        """
        workflow_name = self._selected_workflow_name()
        if workflow_name == "eurostag":
            value = self._e_island.get()
        else:
            value = self._d_island.get()
        try:
            return float(value)
        except ValueError:
            return 0.0

    def current_cores(self) -> int:
        """

        :return:
        """
        workflow_name = self._selected_workflow_name()
        if workflow_name == "eurostag":
            value = self._e_cores.get()
        else:
            value = self._d_cores.get()
        try:
            return max(int(value), 1)
        except ValueError:
            return 1

    def current_verbose(self) -> bool:
        """

        :return:
        """
        workflow_name = self._selected_workflow_name()
        if workflow_name == "eurostag":
            return self._e_verbose.get()
        else:
            return self._d_verbose.get()

    def current_warn(self) -> bool:
        """

        :return:
        """
        workflow_name = self._selected_workflow_name()
        if workflow_name == "eurostag":
            return self._e_warn.get()
        else:
            return self._d_warn.get()


def run_gui() -> None:
    app = DeeacGui()
    app.mainloop()
