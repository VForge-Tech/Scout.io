import re


class Sanitizer:
    def __init__(self):
        self.provider_patterns = [
            # Provider names with various separators
            (r'\b(openai|anthropic|google|together\.ai|meta-llama|mistral)\b', lambda m: "[AI provider]"),
            # Space/hyphen variations
            (r'\b(open\s*ai|anthropic|google|together\s*ai|meta\s*llama|mistral)\b', lambda m: "[AI provider]"),
            (r'\b(open-ai|anthropic|google|together-ai|meta-llama|mistral)\b', lambda m: "[AI provider]"),
            # Partial matches in compounds
            (r'(openai|anthropic|google|together\.ai|meta-llama|mistral)(?=-|_)', lambda m: "[AI provider]"),
            # Model names
            (r'\bgpt[-\s]?4[o]?\b', lambda m: "[AI model]"),
            (r'\bgpt[-\s]?3[.\s]?5\b', lambda m: "[AI model]"),
            (r'\bclaude[-\s]?(opus|sonnet|haiku)?\b', lambda m: "[AI model]"),
            (r'\bgemini[-\s]?(pro|ultra|flash)?\b', lambda m: "[AI model]"),
            (r'\bllama[-\s]?\d*\b', lambda m: "[AI model]"),
        ]
        self.internal_patterns = [
            # Key/secret patterns with various delimiters
            (r'\b(api[_-]?key|secret[_-]?key|token|password)\s*[:=]\s*\S+', lambda m: f"{m.group(1)}: [REDACTED]"),
            (r'(?<![a-zA-Z0-9_])sk[-_][a-zA-Z0-9]{8,}(?![a-zA-Z0-9_])', lambda m: "[REDACTED]"),
            (r'(?<![a-zA-Z0-9])sk[.:|][a-zA-Z0-9]{8,}(?![a-zA-Z0-9])', lambda m: "[REDACTED]"),
        ]

    def sanitize(self, text: str) -> str:
        result = text
        for pattern, replacer in self.provider_patterns:
            result = re.sub(pattern, replacer, result, flags=re.IGNORECASE)
        for pattern, replacer in self.internal_patterns:
            result = re.sub(pattern, replacer, result, flags=re.IGNORECASE)
        return result
