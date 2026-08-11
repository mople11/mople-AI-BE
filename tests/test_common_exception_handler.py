import logging

import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from common.exception_handler import custom_exception_handler


def _context():
    request = APIRequestFactory().get("/api/v1/boom")
    return {"request": Request(request), "view": None, "args": (), "kwargs": {}}


def test_unhandled_exception_is_logged(caplog):
    with caplog.at_level(logging.ERROR, logger="common.exception_handler"):
        response = custom_exception_handler(RuntimeError("boom"), _context())

    assert response.status_code == 500
    assert response.data["error"]["code"] == "COMMON_500"
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert "Unhandled exception on GET /api/v1/boom" in record.message
    assert record.exc_info is not None


def test_client_error_is_not_logged(caplog):
    from rest_framework.exceptions import ValidationError

    with caplog.at_level(logging.ERROR, logger="common.exception_handler"):
        response = custom_exception_handler(ValidationError("bad input"), _context())

    assert response.status_code == 422
    assert caplog.records == []
