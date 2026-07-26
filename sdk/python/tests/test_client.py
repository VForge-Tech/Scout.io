from unittest.mock import patch

from scout_sdk import ScoutClient, ScoutConfig


def test_client_initialization():
    config = ScoutConfig(api_key="sk-test")
    client = ScoutClient(config)
    assert client.config.api_key == "sk-test"
    assert client.config.base_url == "https://api.scout.io"


@patch("scout_sdk.client.httpx.request")
def test_send_message(mock_request):
    mock_request.return_value.status_code = 200
    mock_request.return_value.json.return_value = {"reply": "Hello!", "session_id": "s1"}

    client = ScoutClient(ScoutConfig(api_key="sk-test"))
    resp = client.send_message("bot-1", "Hi")

    assert resp["reply"] == "Hello!"
    mock_request.assert_called_once()


@patch("scout_sdk.client.httpx.request")
def test_search_knowledge(mock_request):
    mock_request.return_value.status_code = 200
    mock_request.return_value.json.return_value = [{"id": "1", "score": 0.95}]

    client = ScoutClient(ScoutConfig(api_key="sk-test"))
    results = client.search_knowledge("org-1", "test query")

    assert len(results) == 1
    assert results[0]["id"] == "1"
