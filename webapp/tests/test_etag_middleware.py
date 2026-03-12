"""Tests for ETag middleware."""


def test_etag_header_present_on_get_api(client, auth_headers):
    resp = client.get("/api/stories/", headers=auth_headers)
    assert resp.status_code == 200
    assert "etag" in resp.headers


def test_304_on_matching_if_none_match(client, auth_headers):
    resp = client.get("/api/stories/", headers=auth_headers)
    etag = resp.headers["etag"]

    resp2 = client.get("/api/stories/", headers={**auth_headers, "if-none-match": etag})
    assert resp2.status_code == 304


def test_200_on_non_matching_if_none_match(client, auth_headers):
    resp = client.get("/api/stories/", headers={**auth_headers, "if-none-match": '"bogus"'})
    assert resp.status_code == 200
    assert "etag" in resp.headers


def test_post_not_affected(client, auth_headers):
    resp = client.post(
        "/api/stories/",
        headers=auth_headers,
        json={"title": "Test", "num_chapters": 1},
    )
    # POST responses don't get ETag
    assert "etag" not in resp.headers


def test_non_api_paths_get_etag(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "etag" in resp.headers


def test_non_api_path_304_on_matching_if_none_match(client):
    resp = client.get("/health")
    etag = resp.headers["etag"]

    resp2 = client.get("/health", headers={"if-none-match": etag})
    assert resp2.status_code == 304


def test_non_200_response_not_affected(client, auth_headers):
    resp = client.get("/api/stories/99999", headers=auth_headers)
    assert resp.status_code == 404
    assert "etag" not in resp.headers


def test_task_endpoint_skips_etag(client, auth_headers):
    from webapp.services.task_store import get_task_backend

    get_task_backend().update("etag_test_task", "running", 50, "In progress")

    resp = client.get("/api/stories/tasks/etag_test_task", headers=auth_headers)
    assert resp.status_code == 200
    assert "etag" not in resp.headers
