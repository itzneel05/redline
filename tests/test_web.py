from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest
from conftest import FakeModel

from redline.web import serve


@pytest.fixture
def base_url():
    httpd = serve(port=0, model_factory=lambda: FakeModel())
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address
    try:
        yield f"http://{host}:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _get(url: str) -> tuple[int, bytes]:
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.status, response.read()


def _post(url: str, payload: object) -> tuple[int, dict]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_index_and_static_are_served(base_url: str) -> None:
    status, body = _get(base_url + "/")
    assert status == 200
    assert b"Redline" in body
    assert b'id="document"' in body  # the report is rendered as a marked-up document

    status, body = _get(base_url + "/static/app.js")
    assert status == 200
    assert b"analyseContract" in body

    status, body = _get(base_url + "/static/styles.css")
    assert status == 200
    assert b"--red" in body


def test_analyze_endpoint_returns_report(base_url: str) -> None:
    status, data = _post(
        base_url + "/api/analyze",
        {"text": "Payment is net 90 days. Client may request unlimited revisions."},
    )
    assert status == 200
    assert data["overall_risk"] == "high"
    assert data["model"] == "fake-model"
    assert data["findings"]


def test_analyze_endpoint_can_draft_email(base_url: str) -> None:
    status, data = _post(base_url + "/api/analyze", {"text": "net 90 days", "email": True})
    assert status == 200
    assert "email" in data


def test_analyze_endpoint_rejects_empty_text(base_url: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        _post(base_url + "/api/analyze", {"text": "   "})
    assert excinfo.value.code == 400


def test_analyze_endpoint_rejects_bad_json(base_url: str) -> None:
    request = urllib.request.Request(
        base_url + "/api/analyze",
        data=b"{not json}",
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        urllib.request.urlopen(request, timeout=10)
    assert excinfo.value.code == 400


def test_unknown_path_is_404(base_url: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        _get(base_url + "/nope")
    assert excinfo.value.code == 404
