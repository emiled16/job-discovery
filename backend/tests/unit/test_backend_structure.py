from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BackendStructureTests(unittest.TestCase):
    def test_backend_contains_python_runtime_modules(self) -> None:
        required = [
            ROOT / "src" / "job_discovery_backend" / "api",
            ROOT / "src" / "job_discovery_backend" / "worker",
            ROOT / "src" / "job_discovery_backend" / "scheduler",
            ROOT / "tests" / "unit",
            ROOT / "tests" / "smoke",
        ]

        missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]

        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()

