"""choose_model prefers best benchmark quality among eligible profiles."""
import unittest

from company.routing import choose_model


class RoutingBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.registry = {
            "profiles": {
                "cheap": {"enabled": True, "capabilities": ["text"], "allowed_data": ["public"]},
                "strong": {"enabled": True, "capabilities": ["text"], "allowed_data": ["public"]},
                "restricted-only": {
                    "enabled": True, "capabilities": ["text"],
                    "allowed_data": ["restricted"],
                },
            },
            "departments": {"engineering": ["cheap", "strong"]},
            "positions": {},
            "company_default": ["cheap"],
        }

    def test_order_when_no_benchmarks(self):
        chosen = choose_model(self.registry, "engineering", "developer", "text", "public")
        self.assertEqual(chosen["profile_id"], "cheap")
        self.assertEqual(chosen["benchmark_source"], "order")

    def test_prefers_higher_quality(self):
        benches = [
            {"role": "creator", "profile_id": "cheap", "quality": 0.5},
            {"role": "creator", "profile_id": "strong", "quality": 0.9},
        ]
        chosen = choose_model(
            self.registry, "engineering", "developer", "text", "public",
            role="creator", benchmarks=benches,
        )
        self.assertEqual(chosen["profile_id"], "strong")
        self.assertEqual(chosen["benchmark_source"], "quality_max")
        self.assertEqual(chosen["benchmark_quality"], 0.9)

    def test_ignores_benchmarks_for_ineligible_profiles(self):
        benches = [
            {"role": "creator", "profile_id": "restricted-only", "quality": 0.99},
            {"role": "creator", "profile_id": "cheap", "quality": 0.4},
        ]
        chosen = choose_model(
            self.registry, "engineering", "developer", "text", "public",
            role="creator", benchmarks=benches,
        )
        self.assertEqual(chosen["profile_id"], "cheap")
        self.assertEqual(chosen["benchmark_source"], "quality_max")

    def test_falls_back_to_order_when_role_has_no_rows(self):
        benches = [{"role": "reviewer", "profile_id": "strong", "quality": 0.99}]
        chosen = choose_model(
            self.registry, "engineering", "developer", "text", "public",
            role="creator", benchmarks=benches,
        )
        self.assertEqual(chosen["profile_id"], "cheap")
        self.assertEqual(chosen["benchmark_source"], "order")


if __name__ == "__main__":
    unittest.main()
