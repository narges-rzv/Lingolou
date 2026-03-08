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


def test_non_api_paths_not_affected(client):
    resp = client.get("/health")
    # /health is not under /api/ so no ETag
    assert "etag" not in resp.headers


def test_non_200_response_not_affected(client, auth_headers):
    resp = client.get("/api/stories/99999", headers=auth_headers)
    assert resp.status_code == 404
    assert "etag" not in resp.headers
