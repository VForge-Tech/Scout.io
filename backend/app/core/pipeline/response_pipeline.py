import logging
import re
import time
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.ai.router import AIRouter
from app.core.billing.pricing import estimate_cost_paise
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


def sse_wrap(events):
    """Encode pipeline event dicts into Server-Sent-Events ``data:`` frames."""
    import json

    for event in events:
        yield f"data: {json.dumps(event)}\n\n"


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

        # Post-generation safety patterns
        self._cross_org_pattern = re.compile(
            r'\b(organization|org)\s+(?:id|identifier)?\s*[:=]?\s*[a-f0-9-]{36}\b',
            re.IGNORECASE
        )
        self._system_prompt_leak_patterns = [
            re.compile(r'\b(system\s+)?prompt\b', re.IGNORECASE),
            re.compile(r'\binternal\s+(instructions?|workings?)\b', re.IGNORECASE),
            re.compile(r'\byour\s+instructions?\b', re.IGNORECASE),
        ]
        self._instruction_override_patterns = [
            re.compile(r'\bignore\s+(?:your\s+)?(?:instructions?|filters?|safety)\b', re.IGNORECASE),
            re.compile(r'\bdisable\s+(?:filters?|safety|guards?)\b', re.IGNORECASE),
            re.compile(r'\b(admin\s+mode|developer\s+mode|debug\s+mode)\b', re.IGNORECASE),
            re.compile(r'\boverride\s+(?:filters?|safety|instructions?)\b', re.IGNORECASE),
            re.compile(r'\bpretend\s+(?:to\s+be|you\s+are)\b', re.IGNORECASE),
        ]

    def _check_post_generation_safety(self, reply: str, org_id: str) -> tuple[bool, str | None]:
        """
        Post-generation safety check for issues that validator/sanitizer might miss.
        
        Returns:
            (is_safe, issue_description) - if not safe, issue describes the problem
        """
        # Check for cross-org references (other org UUIDs)
        uuid_matches = re.findall(r'\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b', reply, re.IGNORECASE)
        for match in uuid_matches:
            if match.lower() != org_id.lower():
                logger.warning("Cross-org UUID detected in response: %s", match)
                return False, f"Response references another organization's ID: {match}"

        # Check for system prompt leakage
        for pattern in self._system_prompt_leak_patterns:
            if pattern.search(reply):
                logger.warning("Potential system prompt leak detected: %s", pattern.pattern)
                return False, "Response may contain system prompt references"

        # Check for instruction override attempts
        for pattern in self._instruction_override_patterns:
            if pattern.search(reply):
                logger.warning("Instruction override attempt detected: %s", pattern.pattern)
                return False, "Response contains instruction override language"

        return True, None

    def _record_usage(
        self, db: Session | None, org_id: str, chatbot_id: str | None
    ) -> None:
        """Persist an LLMUsage row for the most recent generation.

        Uses the token counts and model captured by AIRouter (provider-reported
        when available, estimated otherwise). This is the only place LLMUsage is
        written; the billing beat task aggregates it for usage-based billing.
        """
        usage = getattr(self.ai, "last_usage", None)
        if not db or not usage:
            return
        from uuid import UUID

        from app.models import LLMUsage

        model = usage.get("model") or self.ai.primary_model
        prompt_tokens = usage.get("prompt_tokens") or 0
        completion_tokens = usage.get("completion_tokens") or 0
        try:
            org_uuid = UUID(str(org_id))
            chatbot_uuid = UUID(str(chatbot_id)) if chatbot_id else None
        except ValueError:
            return
        db.add(
            LLMUsage(
                organization_id=org_uuid,
                chatbot_id=chatbot_uuid,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost=estimate_cost_paise(model, prompt_tokens, completion_tokens),
                time_to_first_token_ms=usage.get("time_to_first_token_ms"),
                total_latency_ms=usage.get("total_latency_ms"),
            )
        )

    def _prepare_context(
        self,
        query: str,
        session_id: str,
        org_id_str: str,
        chatbot_id_str: str | None,
        policies: list[Policy] | None,
        reranker_enabled: bool | None,
    ) -> dict:
        """Run the pre-generation stages shared by run() and run_stream().

        Handles response caching, retrieval, context building and session
        memory. Returns a dict with either a cached reply or the prepared
        generation inputs (messages, retrieved_chunks) plus per-stage timings
        in milliseconds.
        """
        timings: dict[str, float] = {}

        _t0 = time.perf_counter()
        cached = self.opt_memory.get_cached_response(query, org_id_str)
        timings["cache_lookup"] = (time.perf_counter() - _t0) * 1000
        if cached:
            return {"cached": True, "reply": cached, "timings": timings}

        _t0 = time.perf_counter()
        retrieved_chunks = self.knowledge_memory.get_cached_chunks(
            query, org_id_str, chatbot_id_str
        )
        timings["knowledge_cache_lookup"] = (time.perf_counter() - _t0) * 1000

        if retrieved_chunks is None:
            _t0 = time.perf_counter()
            retrieved_chunks = self.knowledge.retrieve(
                query=query,
                organization_id=org_id_str,
                chatbot_id=chatbot_id_str,
                policies=policies,
                reranker_enabled=reranker_enabled,
            )
            timings["retrieval"] = (time.perf_counter() - _t0) * 1000
            _t0 = time.perf_counter()
            self.knowledge_memory.cache_chunks(
                query, org_id_str, retrieved_chunks, chatbot_id_str
            )
            timings["knowledge_cache_write"] = (time.perf_counter() - _t0) * 1000
        else:
            timings["retrieval"] = 0.0
            timings["knowledge_cache_write"] = 0.0

        _t0 = time.perf_counter()
        context = "\n\n".join(
            f"[Source {i+1}] (relevance: {r['score']:.3f})\n{r['text']}"
            for i, r in enumerate(retrieved_chunks)
        )

        context = self.token_optimizer.compress_context(context, query)
        timings["context_build"] = (time.perf_counter() - _t0) * 1000

        _t0 = time.perf_counter()
        messages = self.session_memory.build_context(session_id, context)

        self.session_memory.add_message(session_id, "user", query)
        timings["session_memory"] = (time.perf_counter() - _t0) * 1000

        return {
            "cached": False,
            "messages": messages,
            "retrieved_chunks": retrieved_chunks,
            "timings": timings,
        }

    def run(
        self,
        query: str,
        session_id: str,
        organization_id: str | UUID,
        chatbot_id: str | UUID | None = None,
        behaviour: str = "balanced",
        db: Session | None = None,
        policies: list[Policy] | None = None,
        reranker_enabled: bool | None = None,
    ) -> dict:
        org_id_str = str(organization_id)
        chatbot_id_str = str(chatbot_id) if chatbot_id else None

        timings: dict[str, float] = {}

        prep = self._prepare_context(
            query, session_id, org_id_str, chatbot_id_str, policies, reranker_enabled
        )
        timings.update(prep["timings"])
        if prep["cached"]:
            return {"reply": prep["reply"], "cached": True, "session_id": session_id, "timings": timings}

        messages = prep["messages"]
        retrieved_chunks = prep["retrieved_chunks"]

        _t0 = time.perf_counter()
        reply = self.ai.generate(messages)
        timings["llm_generate"] = (time.perf_counter() - _t0) * 1000
        self._record_usage(db, org_id_str, chatbot_id_str)

        _t0 = time.perf_counter()
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
            self._record_usage(db, org_id_str, chatbot_id_str)
        timings["validation"] = (time.perf_counter() - _t0) * 1000

        _t0 = time.perf_counter()
        is_safe, safety_issue = self.validator.validate_safety(reply)
        if not is_safe:
            reply = "I apologize, but I cannot provide that response."

        # Post-generation safety check
        post_safe, post_issue = self._check_post_generation_safety(reply, org_id_str)
        if not post_safe:
            logger.warning("Post-generation safety check failed: %s", post_issue)
            reply = "I apologize, but I cannot provide that response."
        timings["safety"] = (time.perf_counter() - _t0) * 1000

        _t0 = time.perf_counter()
        reply = self.sanitizer.sanitize(reply)

        self.session_memory.add_message(session_id, "assistant", reply)

        self.opt_memory.cache_response(query, org_id_str, reply)
        timings["postprocess"] = (time.perf_counter() - _t0) * 1000

        timings["total"] = sum(v for v in timings.values())
        return {"reply": reply, "cached": False, "session_id": session_id, "timings": timings}

    def run_stream(
        self,
        query: str,
        session_id: str,
        organization_id: str | UUID,
        chatbot_id: str | UUID | None = None,
        behaviour: str = "balanced",
        db: Session | None = None,
        policies: list[Policy] | None = None,
        reranker_enabled: bool | None = None,
    ):
        """Streaming variant of run().

        Runs the pre-generation stages (cache, retrieval, context, memory)
        synchronously, then yields SSE-style event dicts as the LLM tokens
        arrive:

        - {"type": "meta", "session_id": ...}
        - {"type": "token", "content": <delta>}
        - {"type": "notice", "message": ...}   # post-hoc safety filter applied
        - {"type": "error", "message": ...}    # stream broke mid-response
        - {"type": "done", "reply": ..., "time_to_first_token_ms": ...,
           "total_latency_ms": ..., "usage": ..., "timings": ...}

        Degradation semantics: if the provider stream breaks mid-response the
        caller keeps whatever tokens already arrived (surfaced via an ``error``
        event and ``stream_error`` on ``done``); the response is never frozen
        silently. Because tokens are already visible to the client, post-hoc
        validation/safety failures are logged and surfaced as a ``notice``
        rather than silently swapped for a refusal.
        """
        org_id_str = str(organization_id)
        chatbot_id_str = str(chatbot_id) if chatbot_id else None

        prep = self._prepare_context(
            query, session_id, org_id_str, chatbot_id_str, policies, reranker_enabled
        )
        timings = prep["timings"]
        yield {"type": "meta", "session_id": session_id}

        if prep["cached"]:
            yield {
                "type": "done",
                "reply": prep["reply"],
                "cached": True,
                "usage": None,
                "timings": timings,
            }
            return

        messages = prep["messages"]
        retrieved_chunks = prep["retrieved_chunks"]

        llm_start = time.perf_counter()
        ttft: float | None = None
        chunks: list[str] = []
        for delta in self.ai.generate_stream(messages):
            if ttft is None:
                ttft = (time.perf_counter() - llm_start) * 1000
            if delta:
                chunks.append(delta)
                yield {"type": "token", "content": delta}
        total_latency_ms = (time.perf_counter() - llm_start) * 1000
        stream_error = bool(getattr(self.ai, "last_stream_error", False))
        reply = "".join(chunks)

        # Post-generation checks against the final text (best-effort for
        # streamed content; see docstring for the degradation rationale).
        notice: str | None = None
        is_valid, issues = self.validator.validate_against_context(
            reply, retrieved_chunks
        )
        if not is_valid:
            logger.warning("Streamed response validation failed: %s", issues)
        is_safe, _ = self.validator.validate_safety(reply)
        post_safe, post_issue = self._check_post_generation_safety(reply, org_id_str)
        if not (is_safe and post_safe):
            logger.warning(
                "Streamed response failed safety checks%s", f": {post_issue}" if post_issue else ""
            )
            notice = "Response did not pass safety filters."
        reply = self.sanitizer.sanitize(reply)

        usage = getattr(self.ai, "last_usage", None) or {}
        usage["time_to_first_token_ms"] = round(ttft or 0, 2)
        usage["total_latency_ms"] = round(total_latency_ms, 2)
        self.ai.last_usage = usage
        self._record_usage(db, org_id_str, chatbot_id_str)

        self.session_memory.add_message(session_id, "assistant", reply)
        self.opt_memory.cache_response(query, org_id_str, reply)

        from app.core.metrics import LLM_TIME_TO_FIRST_TOKEN, LLM_TOTAL_LATENCY

        if ttft is not None:
            LLM_TIME_TO_FIRST_TOKEN.observe(ttft / 1000)
        LLM_TOTAL_LATENCY.observe(total_latency_ms / 1000)

        if notice:
            yield {"type": "notice", "message": notice}
        if stream_error:
            yield {
                "type": "error",
                "message": "The stream ended unexpectedly; showing the partial response.",
            }
        yield {
            "type": "done",
            "reply": reply,
            "cached": False,
            "stream_error": stream_error,
            "time_to_first_token_ms": round(ttft or 0, 2),
            "total_latency_ms": round(total_latency_ms, 2),
            "usage": usage,
            "timings": timings,
        }
