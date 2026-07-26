import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.ai.router import AIRouter
from app.core.config import get_settings
from app.core.knowledge.engine import KnowledgeEngine
from app.core.memory.knowledge_memory import KnowledgeMemory
from app.core.memory.optimization_memory import OptimizationMemory
from app.core.memory.org_memory import OrganizationalMemory
from app.core.memory.session_memory import SessionMemory
from app.core.optimization.token_optimizer import TokenOptimizer
from app.core.validation.response_validator import ResponseValidator
from app.core.validation.sanitizer import Sanitizer
from app.models import Policy

logger = logging.getLogger(__name__)
settings = get_settings()


class ResponsePipeline:
    def __init__(
        self,
        knowledge_engine: KnowledgeEngine | None = None,
        ai_router: AIRouter | None = None,
        session_memory: SessionMemory | None = None,
        knowledge_memory: KnowledgeMemory | None = None,
        org_memory: OrganizationalMemory | None = None,
        opt_memory: OptimizationMemory | None = None,
        token_optimizer: TokenOptimizer | None = None,
        validator: ResponseValidator | None = None,
        sanitizer: Sanitizer | None = None,
    ):
        self.knowledge = knowledge_engine or KnowledgeEngine()
        self.ai = ai_router or AIRouter()
        self.session_memory = session_memory or SessionMemory()
        self.knowledge_memory = knowledge_memory or KnowledgeMemory()
        self.org_memory = org_memory or OrganizationalMemory()
        self.opt_memory = opt_memory or OptimizationMemory()
        self.token_optimizer = token_optimizer or TokenOptimizer()
        self.validator = validator or ResponseValidator()
        self.sanitizer = sanitizer or Sanitizer()

    def run(
        self,
        query: str,
        session_id: str,
        organization_id: str | UUID,
        chatbot_id: str | UUID | None = None,
        behaviour: str = "balanced",
        db: Session | None = None,
        policies: list[Policy] | None = None,
    ) -> dict:
        org_id_str = str(organization_id)
        chatbot_id_str = str(chatbot_id) if chatbot_id else None

        cached = self.opt_memory.get_cached_response(query, org_id_str)
        if cached:
            return {"reply": cached, "cached": True, "session_id": session_id}

        retrieved_chunks = self.knowledge_memory.get_cached_chunks(
            query, org_id_str, chatbot_id_str
        )

        if retrieved_chunks is None:
            retrieved_chunks = self.knowledge.retrieve(
                query=query,
                organization_id=org_id_str,
                chatbot_id=chatbot_id_str,
                policies=policies,
            )
            self.knowledge_memory.cache_chunks(
                query, org_id_str, retrieved_chunks, chatbot_id_str
            )

        context = "\n\n".join(
            f"[Source {i+1}] (relevance: {r['score']:.3f})\n{r['text']}"
            for i, r in enumerate(retrieved_chunks)
        )

        context = self.token_optimizer.compress_context(context, query)

        messages = self.session_memory.build_context(session_id, context)

        self.session_memory.add_message(session_id, "user", query)

        reply = self.ai.generate(messages)

        is_valid, issues = self.validator.validate_against_context(
            reply, retrieved_chunks
        )

        if not is_valid:
            logger.warning("Response validation failed: %s", issues)
            messages_no_context = [
                {"role": "system", "content": "You are Scout, an AI assistant."},
                {"role": "user", "content": query},
            ]
            reply = self.ai.generate(messages_no_context)

        is_safe, safety_issue = self.validator.validate_safety(reply)
        if not is_safe:
            reply = "I apologize, but I cannot provide that response."

        reply = self.sanitizer.sanitize(reply)

        self.session_memory.add_message(session_id, "assistant", reply)

        self.opt_memory.cache_response(query, org_id_str, reply)

        return {"reply": reply, "cached": False, "session_id": session_id}
