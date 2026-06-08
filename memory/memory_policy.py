class MemoryPolicy:
    """Rules for memory writes."""

    def should_write_stable(self, confidence: float) -> bool:
        return confidence >= 0.8
