from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class ConnectorConfig:
    source_id: UUID
    organization_id: UUID
    chatbot_id: UUID | None
    source_type: str
    connector_type: str = "default"
    uri: str = ""
    config: dict = field(default_factory=dict)


class BaseKnowledgeConnector(ABC):
    connector_type: str = "default"

    @abstractmethod
    def validate(self, config: ConnectorConfig) -> bool:
        ...

    @abstractmethod
    def sync(self, config: ConnectorConfig) -> list[tuple[str, dict]]:
        ...
