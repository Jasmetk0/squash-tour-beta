"""The measurement helpers run on the reference Windows PC as well as Linux/macOS."""

import os
import sys

import pytest

from scripts import measure_saved_v2_growth as growth
from scripts import process_measurement as measurement


def test_memory_reports_current_and_peak_kib_of_this_process():
    values = measurement.memory_kib()
    assert values["VmHWM"] > 0
    if "VmRSS" in values:
        assert 0 < values["VmRSS"] <= values["VmHWM"]
    peak = measurement.peak_rss_kib()
    # The same process peak, from both helpers (it can only grow in between).
    assert values["VmHWM"] <= peak + 1024
    ballast = bytearray(64 * 2**20)
    ballast[::4096] = b"x" * len(ballast[::4096])
    assert measurement.peak_rss_kib() >= peak
    del ballast


def test_machine_describes_hardware_without_host_or_user_identifiers():
    described = measurement.machine()
    assert described["logical_cpus"] == os.cpu_count()
    assert described["total_memory_mib"] and described["total_memory_mib"] > 0
    assert described["python"] == sys.version.split()[0]
    assert set(described) == {"os", "system", "machine", "cpu_model", "logical_cpus", "total_memory_mib",
                              "python", "memory_metric"}
    # No host name, user name or path is part of the description.
    assert "node" not in described and not any(os.sep in str(value) for value in described.values())


def test_growth_report_records_machine_and_manual_hardware_note():
    env = growth.environment("saved_v2", "SSD, power plan Balanced")
    assert env["machine"] == measurement.machine()
    assert env["hardware_note"] == "SSD, power plan Balanced"
    assert env["storage"] == "saved_v2"
    assert set(growth.proc_status()) <= {"VmRSS", "VmHWM"} and growth.proc_status()["VmHWM"] > 0


@pytest.mark.skipif(sys.platform != "win32", reason="Windows peak working set reader")
def test_windows_working_set_is_read_through_a_real_process_handle():
    counters = measurement._windows_counters()
    assert counters.PeakWorkingSetSize >= counters.WorkingSetSize > 0
