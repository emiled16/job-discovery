from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.api.errors import ApiError
from job_discovery_backend.api.query import (
    PaginationParams,
    SortParams,
    parse_pagination_params,
    parse_sort_params,
)


class ApiQueryParamTests(unittest.TestCase):
    def test_pagination_defaults_are_applied(self) -> None:
        params = parse_pagination_params()

        self.assertEqual(params, PaginationParams(page=1, per_page=20))
        self.assertEqual(params.offset, 0)

    def test_pagination_rejects_out_of_bounds_values(self) -> None:
        with self.assertRaises(ApiError) as page_error:
            parse_pagination_params(page=0)

        self.assertEqual(page_error.exception.status_code, 422)
        self.assertEqual(page_error.exception.details[0]["field"], "page")

        with self.assertRaises(ApiError) as per_page_error:
            parse_pagination_params(per_page=101)

        self.assertEqual(per_page_error.exception.status_code, 422)
        self.assertEqual(per_page_error.exception.details[0]["field"], "per_page")

    def test_sort_defaults_are_applied(self) -> None:
        params = parse_sort_params(
            sort=None,
            order=None,
            allowed_fields={"posted_at", "title"},
            default_field="posted_at",
        )

        self.assertEqual(params, SortParams(field="posted_at", direction="desc"))

    def test_sort_rejects_unknown_fields_and_orders(self) -> None:
        with self.assertRaises(ApiError) as sort_error:
            parse_sort_params(
                sort="salary",
                order="sideways",
                allowed_fields={"posted_at", "title"},
                default_field="posted_at",
            )

        self.assertEqual(sort_error.exception.status_code, 422)
        self.assertEqual(sort_error.exception.details[0]["field"], "sort")
        self.assertEqual(sort_error.exception.details[1]["field"], "order")


if __name__ == "__main__":
    unittest.main()
