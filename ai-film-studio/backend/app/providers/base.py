from abc import ABC, abstractmethod
from typing import Any

class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_text(self, input: dict[str, Any]) -> str: ...
class BaseImageProvider(ABC):
    @abstractmethod
    def generate_image(self, prompt: str, references: list[str] | None = None) -> str: ...
class BaseVideoProvider(ABC):
    @abstractmethod
    def generate_video(self, prompt: str, first_frame: str | None, references: list[str], duration: int, aspect_ratio: str) -> str: ...
class BaseVisionProvider(ABC):
    @abstractmethod
    def analyze_frames(self, frames: list[str]) -> dict[str, Any]: ...
class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> list[float]: ...
    @abstractmethod
    def embed_image(self, image_path: str) -> list[float]: ...
