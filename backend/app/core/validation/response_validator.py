import re

from app.core.config import get_settings

settings = get_settings()


class ResponseValidator:
    def __init__(self, min_similarity_threshold: float = 0.3):
        self.threshold = min_similarity_threshold

    def validate_against_context(
        self, response: str, context_chunks: list[dict]
    ) -> tuple[bool, str | None]:
        if not context_chunks:
            return True, None

        context_text = " ".join(c["text"] for c in context_chunks)
        response_lower = response.lower()

        sentences = re.split(r'(?<=[.!?])\s+', response)
        unsupported_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
            if not self._is_supported_by_context(sentence, context_text):
                unsupported_sentences.append(sentence)

        if unsupported_sentences:
            return False, unsupported_sentences

        return True, None

    def _is_supported_by_context(self, sentence: str, context: str) -> bool:
        words = set(re.findall(r'\b\w+\b', sentence.lower()))
        if not words:
            return True

        context_words = set(re.findall(r'\b\w+\b', context.lower()))
        common = words & context_words

        if len(words) == 0:
            return True

        overlap = len(common) / len(words)
        return overlap >= self.threshold

    def validate_safety(self, response: str) -> tuple[bool, str | None]:
        blocked_patterns = [
            r'\bignore your instructions\b',
            r'\byou are an AI\b',
            r'\byour system prompt\b',
        ]
        for pattern in blocked_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return False, "Response contains restricted content"
        return True, None
