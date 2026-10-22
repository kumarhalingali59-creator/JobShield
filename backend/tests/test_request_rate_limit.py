
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.request_rate_limit import RequestRateLimitMiddleware
import app.core.request_rate_limit as rate_limit_module


def create_test_app(limit: int = 2) -> FastAPI:
    app = FastAPI()

    app.add_middleware(
        RequestRateLimitMiddleware,
        path_limits={"/api/auth/login": limit},
    )

    @app.post("/api/auth/login")
    def login():
        return {"message": "Request accepted"}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


def test_requests_succeed_below_rate_limit():
    client = TestClient(create_test_app(limit=2))

    first = client.post("/api/auth/login")
    second = client.post("/api/auth/login")

    assert first.status_code == 200
    assert second.status_code == 200


def test_requests_over_limit_return_429_and_retry_after():
    client = TestClient(create_test_app(limit=2))

    client.post("/api/auth/login")
    client.post("/api/auth/login")

    response = client.post("/api/auth/login")

    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) >= 1


def test_rate_limit_is_separate_for_different_ips():
    app = create_test_app(limit=2)

    with TestClient(app, client=("192.0.2.1", 12345)) as client_one:
        responses = [
            client_one.post("/api/auth/login")
            for _ in range(3)
        ]

    with TestClient(app, client=("192.0.2.2", 12345)) as client_two:
        other_ip = client_two.post("/api/auth/login")

    assert [response.status_code for response in responses] == [
        200, 200, 429
    ]
    assert other_ip.status_code == 200


def test_get_requests_bypass_post_rate_limit():
    client = TestClient(create_test_app(limit=2))

    responses = [
        client.get("/health")
        for _ in range(15)
    ]

    assert all(response.status_code == 200 for response in responses)


def test_rate_limit_resets_after_window_expires(monkeypatch):
    current_time = [1000.0]

    monkeypatch.setattr(
        rate_limit_module,
        "monotonic",
        lambda: current_time[0],
    )

    client = TestClient(create_test_app(limit=2))

    first = client.post("/api/auth/login")
    second = client.post("/api/auth/login")
    blocked = client.post("/api/auth/login")

    assert first.status_code == 200
    assert second.status_code == 200
    assert blocked.status_code == 429

    # Move time forward beyond the 60-second window.
    current_time[0] += 61

    after_expiry = client.post("/api/auth/login")
    assert after_expiry.status_code == 200
