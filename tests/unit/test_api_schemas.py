"""Validation tests for API request schemas."""

import pytest
from pydantic import ValidationError

from docintel.api.schemas import QueryRequest


def test_query_request_strips_surrounding_whitespace() -> None:
    assert QueryRequest(query="  find this  ", k=3).model_dump() == {
        "query": "find this",
        "k": 3,
    }


@pytest.mark.parametrize("query", ["", "   "])
def test_query_request_rejects_blank_query(query) -> None:
    with pytest.raises(ValidationError):
        QueryRequest(query=query)


@pytest.mark.parametrize("k", [0, -1, 101])
def test_query_request_bounds_k(k) -> None:
    with pytest.raises(ValidationError):
        QueryRequest(query="valid", k=k)
