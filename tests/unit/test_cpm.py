import pytest
from datetime import date
from bepi.services.scheduling import TaskData, compute_cpm, gantt_data


class TestCPM:
    @pytest.fixture
    def simple_network(self):
        """
        A(3) → C(4) → E(2)
        B(5) → D(3) → E

        Critical path: B → D → E = 10 days
        """
        return [
            TaskData("A", "Task A", 3),
            TaskData("B", "Task B", 5),
            TaskData("C", "Task C", 4, predecessors=["A"]),
            TaskData("D", "Task D", 3, predecessors=["B"]),
            TaskData("E", "Task E", 2, predecessors=["C", "D"]),
        ]

    def test_project_duration(self, simple_network):
        result = compute_cpm(simple_network)
        assert result.project_duration == 10

    def test_critical_path(self, simple_network):
        result = compute_cpm(simple_network)
        assert "B" in result.critical_path
        assert "D" in result.critical_path
        assert "E" in result.critical_path

    def test_slack(self, simple_network):
        result = compute_cpm(simple_network)
        assert result.tasks["A"]["slack"] == 1  # A can start 1 day late
        assert result.tasks["B"]["slack"] == 0  # B is critical

    def test_dates(self, simple_network):
        start = date(2026, 1, 1)
        result = compute_cpm(simple_network, project_start=start)
        assert result.project_end_date == date(2026, 1, 11)

    def test_gantt_output(self, simple_network):
        start = date(2026, 1, 1)
        result = compute_cpm(simple_network, project_start=start)
        gantt = gantt_data(simple_network, result, start)
        assert len(gantt) == 5
        assert any(g["Critical"] for g in gantt)

    def test_single_task(self):
        tasks = [TaskData("X", "Only task", 7)]
        result = compute_cpm(tasks)
        assert result.project_duration == 7
        assert result.critical_path == ["X"]

    def test_parallel_paths(self):
        """A(10), B(5), both independent, C depends on both.
        CP: A → C"""
        tasks = [
            TaskData("A", "Long", 10),
            TaskData("B", "Short", 5),
            TaskData("C", "End", 3, predecessors=["A", "B"]),
        ]
        result = compute_cpm(tasks)
        assert result.project_duration == 13
        assert "A" in result.critical_path
        assert "C" in result.critical_path
