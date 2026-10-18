
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.request_rate_limit import RequestRateLimitMiddleware


def create_test_app(limit: int = 2) -> FastAPI:
    app = FastAPI()

    # Use an isolated test endpoint and limiter configuration.
    app.add_middleware(RequestRateLimitMiddleware)

    @app.post("/api/auth/login")
    def login():
        return {"message": "Request accepted"}

    return app


def test_requests_succeed_below_rate_limit():
    client = TestClient(create_test_app())

    first = client.post("/api/auth/login")
    second = client.post("/api/auth/login")

    assert first.status_code == 200
    assert second.status_code == 200


def test_requests_over_limit_return_429_and_retry_after():
    client = TestClient(create_test_app())

    for _ in range(10):
        response = client.post("/api/auth/register")

    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) >= 1



def test_rate_limit_is_separate_for_different_ips():
    app = create_test_app()

    with TestClient(app, client=("192.0.2.1", 12345)) as client_one:
        responses = [
            client_one.post("/api/auth/login")
            for _ in range(11)
        ]

    with TestClient(app, client=("192.0.2.2", 12345)) as client_two:
        other_ip = client_two.post("/api/auth/login")

    assert all(response.status_code == 200 for response in responses[:10])
    assert responses[10].status_code == 429
    assert other_ip.status_code == 200



def create_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestRateLimitMiddleware)

    @app.post("/api/auth/login")
    def login():
        return {"message": "Request accepted"}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


def test_get_requests_bypass_post_rate_limit():
    client = TestClient(create_test_app())

    responses = [
        client.get("/health")
        for _ in range(15)
    ]

    assert all(response.status_code == 200 for response in responses)
