"""
Module for results.

:module: results
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.


from typing import Dict, List, Optional


class EEACResult:
    """
    Eeacresult.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar status: status.
    :ivar swing_state: swing state.
    :ivar critical_cluster: critical cluster.
    :ivar node_id: node id.
    :ivar cct: cct.
    :ivar warning: warning.
    :ivar failure_report: failure report.
    :ivar interval: interval.
    :ivar production_loss: production loss.
    :ivar disconnected_production: disconnected production.
    :ivar consumption_loss: consumption loss.
    :ivar disconnected_consumption: disconnected consumption.
    :ivar error_msg: error msg.
    :ivar dynawo_generation_status: Dynawo generation status.
    :ivar dynawo_generation_reason: Dynawo generation reason.
    :ivar dynawo_run_status: Dynawo run status.
    :ivar dynawo_return_code: Dynawo return code.
    :ivar dynawo_case_output_dir: Dynawo case output directory.
    :ivar dynawo_jobs_file: Dynawo generated jobs file.
    :ivar dynawo_dyd_file: Dynawo generated dyd file.
    :ivar dynawo_par_file: Dynawo generated par file.
    :ivar dynawo_stderr_head: Dynawo stderr summary.
    """
    __slots__ = (
        "status",
        "swing_state",
        "critical_cluster",
        "node_id",
        "cct",
        "warning",
        "failure_report",
        "interval",
        "production_loss",
        "disconnected_production",
        "consumption_loss",
        "disconnected_consumption",
        "error_msg",
        "dynawo_generation_status",
        "dynawo_generation_reason",
        "dynawo_run_status",
        "dynawo_return_code",
        "dynawo_case_output_dir",
        "dynawo_jobs_file",
        "dynawo_dyd_file",
        "dynawo_par_file",
        "dynawo_stderr_head",
    )

    def __init__(
        self,
        status: str,
        swing_state: Optional[str] = None,
        critical_cluster: Optional[str] = None,
        node_id: Optional[int] = None,
        cct: Optional[float] = None,
        warning: Optional[str] = None,
        failure_report: Optional[str] = None,
        interval: Optional[str] = None,
        production_loss: Optional[str] = None,
        disconnected_production: Optional[str] = None,
        consumption_loss: Optional[str] = None,
        disconnected_consumption: Optional[str] = None,
        error_msg: Optional[str] = None,
        dynawo_generation_status: Optional[str] = None,
        dynawo_generation_reason: Optional[str] = None,
        dynawo_run_status: Optional[str] = None,
        dynawo_return_code: Optional[int] = None,
        dynawo_case_output_dir: Optional[str] = None,
        dynawo_jobs_file: Optional[str] = None,
        dynawo_dyd_file: Optional[str] = None,
        dynawo_par_file: Optional[str] = None,
        dynawo_stderr_head: Optional[str] = None,
    ):
        """
        Initialize the object.
        
        :param status: status.
        :param swing_state: swing state.
        :param critical_cluster: critical cluster.
        :param node_id: node id.
        :param cct: cct.
        :param warning: warning.
        :param failure_report: failure report.
        :param interval: interval.
        :param production_loss: production loss.
        :param disconnected_production: disconnected production.
        :param consumption_loss: consumption loss.
        :param disconnected_consumption: disconnected consumption.
        :param error_msg: error msg.
        :param dynawo_generation_status: Dynawo generation status.
        :param dynawo_generation_reason: Dynawo generation reason.
        :param dynawo_run_status: Dynawo run status.
        :param dynawo_return_code: Dynawo return code.
        :param dynawo_case_output_dir: Dynawo case output directory.
        :param dynawo_jobs_file: Dynawo generated jobs file.
        :param dynawo_dyd_file: Dynawo generated dyd file.
        :param dynawo_par_file: Dynawo generated par file.
        :param dynawo_stderr_head: Dynawo stderr summary.
        """
        self.status = status
        self.swing_state = swing_state
        self.critical_cluster = critical_cluster
        self.node_id = node_id
        self.cct = cct
        self.warning = warning
        self.failure_report = failure_report
        self.interval = interval
        self.production_loss = production_loss
        self.disconnected_production = disconnected_production
        self.consumption_loss = consumption_loss
        self.disconnected_consumption = disconnected_consumption
        self.error_msg = error_msg
        self.dynawo_generation_status = dynawo_generation_status
        self.dynawo_generation_reason = dynawo_generation_reason
        self.dynawo_run_status = dynawo_run_status
        self.dynawo_return_code = dynawo_return_code
        self.dynawo_case_output_dir = dynawo_case_output_dir
        self.dynawo_jobs_file = dynawo_jobs_file
        self.dynawo_dyd_file = dynawo_dyd_file
        self.dynawo_par_file = dynawo_par_file
        self.dynawo_stderr_head = dynawo_stderr_head

    def to_dict(self) -> Dict[str, object]:
        """
        To dict.
        
        :return: Return value.
        :rtype: Dict[str, object]
        """
        data = {
            "status": self.status,
            "swing_state": self.swing_state,
            "critical_cluster": self.critical_cluster,
            "node_id": self.node_id,
            "CCT": self.cct,
            "warning": self.warning,
            "failure_report": self.failure_report,
            "interval": self.interval,
            "production_loss": self.production_loss,
            "disconnected_production": self.disconnected_production,
            "consumption_loss": self.consumption_loss,
            "disconnected_consumption": self.disconnected_consumption,
            "error_msg": self.error_msg,
            "dynawo_generation_status": self.dynawo_generation_status,
            "dynawo_generation_reason": self.dynawo_generation_reason,
            "dynawo_run_status": self.dynawo_run_status,
            "dynawo_return_code": self.dynawo_return_code,
            "dynawo_case_output_dir": self.dynawo_case_output_dir,
            "dynawo_jobs_file": self.dynawo_jobs_file,
            "dynawo_dyd_file": self.dynawo_dyd_file,
            "dynawo_par_file": self.dynawo_par_file,
            "dynawo_stderr_head": self.dynawo_stderr_head,
        }
        return {key: value for key, value in data.items() if value is not None}

    def __getitem__(self, key: str) -> object:
        """
        getitem  .
        
        :param key: key.
        """
        mapping = {
            "status": self.status,
            "swing_state": self.swing_state,
            "critical_cluster": self.critical_cluster,
            "node_id": self.node_id,
            "CCT": self.cct,
            "warning": self.warning,
            "failure_report": self.failure_report,
            "interval": self.interval,
            "production_loss": self.production_loss,
            "disconnected_production": self.disconnected_production,
            "consumption_loss": self.consumption_loss,
            "disconnected_consumption": self.disconnected_consumption,
            "error_msg": self.error_msg,
            "dynawo_generation_status": self.dynawo_generation_status,
            "dynawo_generation_reason": self.dynawo_generation_reason,
            "dynawo_run_status": self.dynawo_run_status,
            "dynawo_return_code": self.dynawo_return_code,
            "dynawo_case_output_dir": self.dynawo_case_output_dir,
            "dynawo_jobs_file": self.dynawo_jobs_file,
            "dynawo_dyd_file": self.dynawo_dyd_file,
            "dynawo_par_file": self.dynawo_par_file,
            "dynawo_stderr_head": self.dynawo_stderr_head,
        }
        return mapping[key]

    def __repr__(self):
        """
        repr  .
        
        :return: Return value.
        """
        return f"EEACResult({self.to_dict()})"


class EEACFaultResult:
    """
    Eeacfaultresult.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar fault_name: fault name.
    :ivar result: eeac result.
    """

    def __init__(self, fault_name: str, result: EEACResult):
        """
        Initialize the object.
        
        :param fault_name: fault name.
        :param result: eeac result.
        :return: Return value.
        """
        self.fault_name = fault_name
        self.result = result

    def to_dict(self) -> Dict[str, Dict[str, object]]:
        """
        To dict.
        
        :return: Return value.
        :rtype: Dict[str, Dict[str, object]]
        """
        return {self.fault_name: self.result.to_dict()}

    def __repr__(self):
        """
        repr  .
        
        :return: Return value.
        """
        return f"EEACFaultResult({self.fault_name!r}, {self.result!r})"


class EEACResults:
    """
    Eeacresults.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :summary: Class metadata.
    """
    def __init__(self):
        """
        Initialize the object.
        
        :return: Return value.
        """
        self._results: List[EEACFaultResult] = []

    def add(self, fault_name: str, result: EEACResult) -> None:
        """
        Add.
        
        :param fault_name: fault name.
        :param result: result.
        """
        self._results.append(EEACFaultResult(fault_name, result))

    @property
    def results(self) -> List[EEACFaultResult]:
        """
        Results list.
        
        :return: Result value.
        :rtype: List[EEACFaultResult]
        """
        return self._results

    def to_dict(self) -> Dict[str, Dict[str, object]]:
        """
        To dict.
        
        :return: Return value.
        :rtype: Dict[str, Dict[str, object]]
        """
        return {entry.fault_name: entry.result.to_dict() for entry in self._results}

    def get(self, fault_name: str) -> Optional[EEACResult]:
        """
        Get a result by fault name.
        
        :param fault_name: fault name.
        :return: Result value.
        :rtype: Optional[EEACResult]
        """
        for entry in self._results:
            if entry.fault_name == fault_name:
                return entry.result
        return None

    def __repr__(self):
        """
        repr  .
        
        :return: Return value.
        """
        return f"EEACResults({self.to_dict()})"
