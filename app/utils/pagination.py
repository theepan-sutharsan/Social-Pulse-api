"""
Social Pulse API — Pagination helper + query utilities
"""
from flask import request
from typing import Tuple


def get_pagination_params() -> Tuple[int, int]:
    """Extract page and per_page from request args."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    return max(page, 1), max(per_page, 1)


def paginate_query(query, page: int, per_page: int) -> dict:
    """Paginate a SQLAlchemy query and return meta."""
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        "items": paginated.items,
        "total": paginated.total,
        "page": paginated.page,
        "per_page": paginated.per_page,
        "pages": paginated.pages,
        "has_next": paginated.has_next,
        "has_prev": paginated.has_prev,
    }
