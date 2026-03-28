from __future__ import annotations

from dataclasses import dataclass

from job_discovery_backend.api.errors import ApiError

DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100
SORT_DIRECTIONS = {"asc", "desc"}


@dataclass(frozen=True)
class PaginationParams:
    page: int
    per_page: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


@dataclass(frozen=True)
class SortParams:
    field: str
    direction: str


def parse_pagination_params(
    *,
    page: int = DEFAULT_PAGE,
    per_page: int = DEFAULT_PER_PAGE,
    max_per_page: int = MAX_PER_PAGE,
) -> PaginationParams:
    errors: list[dict[str, str]] = []
    if page < 1:
        errors.append(
            {
                "field": "page",
                "message": "Must be greater than or equal to 1",
                "code": "out_of_range",
            }
        )
    if per_page < 1 or per_page > max_per_page:
        errors.append(
            {
                "field": "per_page",
                "message": f"Must be between 1 and {max_per_page}",
                "code": "out_of_range",
            }
        )

    if errors:
        raise ApiError(
            422,
            "invalid_query",
            "Invalid pagination parameters",
            details=errors,
        )

    return PaginationParams(page=page, per_page=per_page)


def parse_sort_params(
    *,
    sort: str | None,
    order: str | None,
    allowed_fields: set[str],
    default_field: str,
    default_order: str = "desc",
) -> SortParams:
    resolved_field = sort or default_field
    resolved_order = (order or default_order).lower()

    errors: list[dict[str, str]] = []
    if resolved_field not in allowed_fields:
        errors.append(
            {
                "field": "sort",
                "message": f"Must be one of: {', '.join(sorted(allowed_fields))}",
                "code": "invalid_choice",
            }
        )

    if resolved_order not in SORT_DIRECTIONS:
        errors.append(
            {
                "field": "order",
                "message": "Must be one of: asc, desc",
                "code": "invalid_choice",
            }
        )

    if errors:
        raise ApiError(
            422,
            "invalid_query",
            "Invalid sort parameters",
            details=errors,
        )

    return SortParams(field=resolved_field, direction=resolved_order)
