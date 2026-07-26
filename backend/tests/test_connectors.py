import uuid

import pytest

from app.core.knowledge.connectors import ConnectorRegistry, ConnectorConfig
from app.core.knowledge.connectors.api_connector import APIConnector
from app.core.knowledge.connectors.sql_connector import SQLConnector


def test_registry_register_and_get():
    assert ConnectorRegistry.get("api") is APIConnector
    assert ConnectorRegistry.get("sql") is SQLConnector
    assert ConnectorRegistry.get("nonexistent") is None


def test_registry_list_types():
    types = ConnectorRegistry.list_types()
    assert "api" in types
    assert "sql" in types
    assert "git" in types


def test_api_connector_validation():
    config = ConnectorConfig(
        source_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        chatbot_id=None,
        source_type="api",
        connector_type="api",
        uri="https://api.example.com/data",
        config={"method": "GET"},
    )
    connector = APIConnector()
    assert connector.validate(config) is True


def test_api_connector_validation_fails_no_uri():
    config = ConnectorConfig(
        source_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        chatbot_id=None,
        source_type="api",
        connector_type="api",
        uri="",
    )
    connector = APIConnector()
    assert connector.validate(config) is False


def test_sql_connector_validation():
    config = ConnectorConfig(
        source_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        chatbot_id=None,
        source_type="sql",
        connector_type="sql",
        uri="sqlite:///:memory:",
        config={"query": "SELECT 1"},
    )
    connector = SQLConnector()
    assert connector.validate(config) is True


def test_sql_connector_validation_fails():
    config = ConnectorConfig(
        source_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        chatbot_id=None,
        source_type="sql",
        connector_type="sql",
        uri="",
        config={},
    )
    connector = SQLConnector()
    assert connector.validate(config) is False


def test_connector_sync_graceful_failure():
    config = ConnectorConfig(
        source_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        chatbot_id=None,
        source_type="api",
        connector_type="api",
        uri="https://invalid.nonexistent.example/api",
    )
    connector = APIConnector()
    chunks = connector.sync(config)
    assert chunks == []


@pytest.mark.asyncio
async def test_connector_registry_default_fallback():
    assert ConnectorRegistry.get_or_default("sql") is SQLConnector
    assert ConnectorRegistry.get_or_default("unknown") is None
