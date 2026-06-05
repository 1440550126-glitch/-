from .mock_provider import MockProvider

def get_llm_provider() -> MockProvider: return MockProvider()
def get_image_provider() -> MockProvider: return MockProvider()
def get_video_provider() -> MockProvider: return MockProvider()
def get_vision_provider() -> MockProvider: return MockProvider()
def get_embedding_provider() -> MockProvider: return MockProvider()

class OpenAIProvider: pass
class GeminiProvider: pass
class VeoProvider: pass
class RunwayProvider: pass
class KlingProvider: pass
class LumaProvider: pass
class PikaProvider: pass
class FluxProvider: pass
class StableDiffusionProvider: pass
class ElevenLabsProvider: pass
