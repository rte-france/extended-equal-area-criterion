"""
Module for logger.

:module: logger
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd


class LoggerRecord:
    """
    Logger record.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :ivar level: level.
    :ivar message: message.
    :ivar context: context.
    """
    __slots__ = ("timestamp", "level", "message", "context")

    def __init__(self, level: str, message: str, context: Optional[Dict[str, str]] = None):
        """
        Initialize the object.
        
        :param level: level.
        :param message: message.
        :param context: context.
        """
        self.timestamp = datetime.now().isoformat(timespec="seconds")
        self.level = level
        self.message = message
        self.context = context or dict()


class Logger:
    """
    Logger.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :ivar _verbose: verbose.
    """
    __slots__ = ("_verbose", "_records")

    def __init__(self, verbose: bool = False):
        """
        Initialize the object.
        
        :param verbose: verbose.
        """
        self._verbose = verbose
        self._records: List[LoggerRecord] = []

    @property
    def records(self) -> List[LoggerRecord]:
        """
        Return the collected log records.
        
        :return: Ordered log records produced during the run.
        """
        return self._records

    def info(self, message: str, context: Optional[Dict[str, str]] = None) -> None:
        """
        Info.
        
        :param message: message.
        :param context: context.
        """
        if not message and not context:
            return
        self._records.append(LoggerRecord("info", message, context))

    def warning(self, message: str, context: Optional[Dict[str, str]] = None) -> None:
        """
        Warning.
        
        :param message: message.
        :param context: context.
        """
        if not message and not context:
            return
        self._records.append(LoggerRecord("warning", message, context))

    def error(self, message: str, context: Optional[Dict[str, str]] = None) -> None:
        """
        Error.
        
        :param message: message.
        :param context: context.
        """
        if not message and not context:
            return
        self._records.append(LoggerRecord("error", message, context))

    def to_dataframe(self) -> "pd.DataFrame":
        """
        To dataframe.
        
        :return: Return value.
        """

        rows: List[Dict[str, str]] = list()
        for record in self._records:
            row: Dict[str, str] = {
                "timestamp": record.timestamp,
                "level": record.level,
                "message": record.message,
            }
            for key, value in record.context.items():
                row[f"context.{key}"] = value
            rows.append(row)
        return pd.DataFrame(rows)

    def print_if_verbose(self) -> None:
        """
        Print if verbose.
        
        :return: Return value.
        :rtype: None
        """
        if not self._verbose:
            return
        df = self.to_dataframe()
        if df.empty:
            return
        print(df.to_string(index=False))

    def write_csv(self, path: str) -> None:
        """
        Write csv.
        
        :param path: path.
        """
        df = self.to_dataframe()
        df.to_csv(path, index=False)

    def write_excel(self, path: str) -> None:
        """
        Write excel.
        
        :param path: path.
        """
        df = self.to_dataframe()
        df.to_excel(path, index=False)
