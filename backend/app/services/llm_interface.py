from abc import ABC, abstractmethod


class LLMService(ABC):
    """Uniform interface so the agent can call any LLM provider interchangeably."""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        ...

    @abstractmethod
    def update_api_key(self, api_key: str) -> None:
        ...

    @property
    @abstractmethod
    def enabled(self) -> bool:
        ...
