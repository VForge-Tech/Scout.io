from fastapi.testclient import TestClient

from app.core.knowledge.connectors import ConnectorRegistry
from app.core.knowledge.connectors.api_connector import APIConnector
from app.core.knowledge.connectors.sql_connector import SQLConnector
from app.core.knowledge.connectors.git_connector import GitConnector


def test_connector_types_are_registered():
    assert ConnectorRegistry.get("api") is APIConnector
    assert ConnectorRegistry.get("sql") is SQLConnector
    assert ConnectorRegistry.get("git") is GitConnector


def test_create_knowledge_source_with_connector_type(client: TestClient, db):
    from tests.test_knowledge_sources import _auth_headers, _create_bot

    headers = _auth_headers(client, db)
    bot_id = _create_bot(client, headers)

    response = client.post(
        f"/api/v1/chatbots/{bot_id}/knowledge-sources",
        headers=headers,
        json={
            "source_type": "api",
            "uri": "https://api.example.com/data",
            "connector_type": "api",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["source_type"] == "api"
    assert data["config"].get("_connector_type") == "api"


def test_create_knowledge_source_without_connector_type_is_backward_compatible(
    client: TestClient, db,
):
    from tests.test_knowledge_sources import _auth_headers, _create_bot

    headers = _auth_headers(client, db)
    bot_id = _create_bot(client, headers)

    response = client.post(
        f"/api/v1/chatbots/{bot_id}/knowledge-sources",
        headers=headers,
        json={
            "source_type": "website",
            "uri": "https://example.com",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "_connector_type" not in data.get("config", {})
