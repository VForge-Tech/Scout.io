import re


class Sanitizer:
    def __init__(self):
        self.provider_patterns = [
            (r'\b(openai|anthropic|google|together\.ai|meta-llama|mistral)\b', lambda m: "[AI provider]"),
            (r'\bgpt[-\s]?4[o]?\b', lambda m: "[AI model]"),
            (r'\bgpt[-\s]?3[.\s]?5\b', lambda m: "[AI model]"),
            (r'\bclaude[-\s]?(opus|sonnet|haiku)?\b', lambda m: "[AI model]"),
            (r'\bgemini[-\s]?(pro|ultra|flash)?\b', lambda m: "[AI model]"),
            (r'\bllama[-\s]?\d*\b', lambda m: "[AI model]"),
        ]
        self.internal_patterns = [
            (r'\b(api[_-]?key|secret[_-]?key|token|password)\s*[:=]\s*\S+', lambda m: f"{m.group(1)}: [REDACTED]"),
            (r'\bsk[-][a-zA-Z0-9]{20,}\b', lambda m: "[REDACTED]"),
        ]

    def sanitize(self, text: str) -> str:
        result = text
        for pattern, replacer in self.provider_patterns:
            result = re.sub(pattern, replacer, result, flags=re.IGNORECASE)
        for pattern, replacer in self.internal_patterns:
            result = re.sub(pattern, replacer, result, flags=re.IGNORECASE)
        return result
