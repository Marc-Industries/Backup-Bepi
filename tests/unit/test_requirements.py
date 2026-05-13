"""Test requirements management."""
import pytest
from bepi.services.requirements import (
    generate_req_id, trace_requirement, verification_matrix,
    coverage_report, import_from_csv_rows, RequirementData,
)


class TestGenerateReqId:
    def test_system_functional(self):
        assert generate_req_id("system", "functional", 1) == "SYS-FUN-001"

    def test_subsystem_performance(self):
        assert generate_req_id("subsystem", "performance", 42) == "SUB-PER-042"


class TestTraceRequirement:
    def test_full_trace(self):
        reqs = [
            RequirementData("1", "MIS-FUN-001", "mission", "functional", "Top", "text"),
            RequirementData("2", "SYS-FUN-001", "system", "functional", "Mid", "text", parent_id="1"),
            RequirementData("3", "SUB-FUN-001", "subsystem", "functional", "Bot", "text", parent_id="2"),
        ]
        result = trace_requirement("SYS-FUN-001", reqs)
        assert len(result["parents"]) == 1
        assert result["parents"][0].req_id == "MIS-FUN-001"
        assert len(result["children"]) == 1
        assert result["children"][0].req_id == "SUB-FUN-001"


class TestCoverageReport:
    def test_coverage_calculation(self):
        reqs = [
            RequirementData("1", "R1", "system", "functional", "A", "t", verification_status="passed"),
            RequirementData("2", "R2", "system", "functional", "B", "t", verification_status="passed"),
            RequirementData("3", "R3", "system", "functional", "C", "t", verification_status="not_started"),
            RequirementData("4", "R4", "subsystem", "performance", "D", "t", verification_status="failed"),
        ]
        report = coverage_report(reqs)
        assert report["total"] == 4
        assert report["by_status"]["passed"] == 2
        assert report["overall_pct"] == pytest.approx(50.0)


class TestImportCsv:
    def test_basic_import(self):
        rows = [
            {"Level": "system", "Category": "functional", "Title": "Power", "Text": "The system shall provide power"},
            {"Level": "system", "Category": "performance", "Title": "Mass", "Text": "Total mass < 500 kg"},
        ]
        result = import_from_csv_rows(rows)
        assert len(result) == 2
        assert result[0].req_id == "SYS-FUN-001"
        assert result[1].req_id == "SYS-PER-002"
