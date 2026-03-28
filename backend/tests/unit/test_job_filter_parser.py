from datetime import date
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.api.errors import ApiError
from job_discovery_backend.api.jobs.filters import JobFilterParams, parse_job_filters


class JobFilterParserTests(unittest.TestCase):
    def test_filter_parser_normalizes_supported_filters(self) -> None:
        params = parse_job_filters(
            title="  ML Engineer  ",
            location=" Toronto ",
            company_ids=[" company-1 ", "", "company-2"],
            work_modes=["Remote", "hybrid"],
            posted_after=date(2026, 1, 1),
            posted_before=date(2026, 1, 31),
        )

        self.assertEqual(
            params,
            JobFilterParams(
                title="ML Engineer",
                location="Toronto",
                company_ids=("company-1", "company-2"),
                work_modes=("remote", "hybrid"),
                posted_after=date(2026, 1, 1),
                posted_before=date(2026, 1, 31),
            ),
        )

    def test_filter_parser_rejects_invalid_work_modes(self) -> None:
        with self.assertRaises(ApiError) as error:
            parse_job_filters(work_modes=["remote", "space"])

        self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(error.exception.details[0]["field"], "work_modes")

    def test_filter_parser_rejects_invalid_date_ranges(self) -> None:
        with self.assertRaises(ApiError) as error:
            parse_job_filters(
                posted_after=date(2026, 2, 1),
                posted_before=date(2026, 1, 31),
            )

        self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(error.exception.details[0]["field"], "posted_after")


if __name__ == "__main__":
    unittest.main()
