import unittest
from datetime import datetime

from server import build_monitoring_report


class MonitoringReportTests(unittest.TestCase):
    NOW = datetime(2026, 8, 18, 12, 0, 0)

    def record(self, created_at, hours=1, accuracy=80, rule=""):
        return {
            "subject": "831经济学",
            "createdAt": created_at,
            "hours": hours,
            "accuracy": accuracy,
            "rule": rule,
        }

    def test_empty_records_are_unknown(self):
        report = build_monitoring_report([], [], now=self.NOW)
        self.assertEqual(report["riskLevel"], "unknown")
        self.assertEqual(report["recordCount"], 0)

    def test_date_formats_and_metrics(self):
        records = [
            self.record("2026/8/18 09:00:00", hours=2, accuracy=80, rule="先画图"),
            self.record("2026-08-17 09:00:00", hours=1.5, accuracy=70),
        ]
        report = build_monitoring_report(records, [], now=self.NOW)
        self.assertEqual(report["studyHours"], 3.5)
        self.assertEqual(report["averageAccuracy"], 75.0)
        self.assertEqual(report["activeDays"], 2)
        self.assertEqual(report["streakDays"], 2)
        self.assertEqual(report["ruleCount"], 1)

    def test_overdue_high_priority_task_is_high_risk(self):
        tasks = [{
            "title": "复测薄弱章节",
            "priority": "high",
            "status": "todo",
            "dueAt": "2026-08-16",
        }]
        report = build_monitoring_report(
            [self.record("2026-08-18", accuracy=85)], tasks, now=self.NOW
        )
        self.assertEqual(report["riskLevel"], "high")
        self.assertEqual(len(report["overdueHighPriorityTasks"]), 1)

    def test_done_task_is_not_overdue(self):
        tasks = [{
            "title": "已完成复盘",
            "priority": "high",
            "status": "done",
            "dueAt": "2026-08-16",
        }]
        report = build_monitoring_report(
            [self.record("2026-08-18", accuracy=85)], tasks, now=self.NOW
        )
        self.assertEqual(report["overdueHighPriorityTasks"], [])


if __name__ == "__main__":
    unittest.main()
