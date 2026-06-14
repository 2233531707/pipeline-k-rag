import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("OPENAI_API_KEY", "dummy-test-key")

from server.routers.knowledge_router import _parse_bbox_param


def test_parse_bbox_param_returns_tuple() -> None:
    assert _parse_bbox_param("1,2,3,4") == (1.0, 2.0, 3.0, 4.0)


@pytest.mark.parametrize("value", ["1,2,3", "a,2,3,4", "3,2,1,4", "1,4,3,2"])
def test_parse_bbox_param_rejects_invalid_value(value: str) -> None:
    with pytest.raises(HTTPException) as exc:
        _parse_bbox_param(value)

    assert exc.value.status_code == 400
