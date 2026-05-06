from unittest.mock import patch, MagicMock


def test_ingest_file_no_auth(client):
    response = client.post("/ingest/file", data={"tenant_id": "t1", "source_name": "doc"})
    assert response.status_code == 422  # missing file + missing header


def test_ingest_file_wrong_key(client):
    response = client.post(
        "/ingest/file",
        headers={"X-API-Key": "wrong-key"},
        data={"tenant_id": "t1", "source_name": "doc"},
        files={"file": ("test.txt", b"Hello world", "text/plain")},
    )
    assert response.status_code == 403


@patch("app.api.ingest.ingest_chunks", return_value=3)
@patch("app.api.ingest.get_collection")
@patch("app.api.ingest.get_chroma_client")
def test_ingest_text_file_success(mock_client, mock_col, mock_ingest, client):
    mock_client.return_value = MagicMock()
    mock_col.return_value = MagicMock()

    response = client.post(
        "/ingest/file",
        headers={"X-API-Key": "test-admin-key"},
        data={"tenant_id": "tenant1", "source_name": "FAQ"},
        files={"file": ("faq.txt", b"Q: What is RAG?\nA: Retrieval-Augmented Generation.", "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["chunks_ingested"] == 3
    assert data["source_name"] == "FAQ"


def test_list_sources_no_auth(client):
    response = client.get("/ingest/sources/tenant1")
    assert response.status_code == 422  # missing header
