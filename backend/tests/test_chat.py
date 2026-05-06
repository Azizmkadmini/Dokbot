from unittest.mock import patch, MagicMock


def test_chat_empty_collection(client):
    with patch("app.api.chat.get_chroma_client") as mock_client, \
         patch("app.api.chat.get_collection") as mock_col:

        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client.return_value = MagicMock()
        mock_col.return_value = mock_collection

        response = client.post("/chat", json={"tenant_id": "empty", "question": "Hello?"})
        assert response.status_code == 404
        assert "No documents" in response.json()["detail"]


@patch("app.api.chat.chat")
@patch("app.api.chat.get_collection")
@patch("app.api.chat.get_chroma_client")
def test_chat_success(mock_client, mock_col, mock_chat, client):
    mock_collection = MagicMock()
    mock_collection.count.return_value = 10
    mock_client.return_value = MagicMock()
    mock_col.return_value = mock_collection
    mock_chat.return_value = {
        "answer": "RAG stands for Retrieval-Augmented Generation.",
        "sources": [{"source": "faq.pdf", "score": 0.91}],
        "latency_ms": 420,
        "cost_usd": 0.000023,
        "tokens": {"prompt": 200, "completion": 50},
    }

    response = client.post("/chat", json={
        "tenant_id": "tenant1",
        "question": "What is RAG?",
        "history": [],
    })

    assert response.status_code == 200
    data = response.json()
    assert "RAG" in data["answer"]
    assert data["latency_ms"] == 420
    assert len(data["sources"]) == 1


@patch("app.api.chat.chat")
@patch("app.api.chat.get_collection")
@patch("app.api.chat.get_chroma_client")
def test_chat_with_history(mock_client, mock_col, mock_chat, client):
    mock_collection = MagicMock()
    mock_collection.count.return_value = 5
    mock_client.return_value = MagicMock()
    mock_col.return_value = mock_collection
    mock_chat.return_value = {
        "answer": "Yes, it supports PDFs.",
        "sources": [],
        "latency_ms": 300,
        "cost_usd": 0.000010,
        "tokens": {"prompt": 150, "completion": 30},
    }

    response = client.post("/chat", json={
        "tenant_id": "tenant1",
        "question": "Does it support PDFs?",
        "history": [
            {"role": "user", "content": "What formats do you support?"},
            {"role": "assistant", "content": "We support PDF and text files."},
        ],
    })

    assert response.status_code == 200
    assert "PDF" in response.json()["answer"]
