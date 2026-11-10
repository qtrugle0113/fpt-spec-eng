"""Fixture-only import seam; production binding and supervision remain unchanged."""
import os
from unittest.mock import patch
from aat_etl.resources import run_supervised
from aat_etl.runtime_task import execute_task as actual_execute


def execute_task(*,expected_revision,mode):
    def injected(command):
        command=list(command);command[2]='tests.airflow.runtime_authorization_fault_child'
        command.append(mode)
        return run_supervised(command)
    with patch('aat_etl.runtime_task.run_supervised',side_effect=injected):
        return actual_execute(expected_revision=expected_revision)
