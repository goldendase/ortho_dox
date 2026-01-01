"""
LM configuration with native tool calling support.

Uses DSPy's ChatAdapter with native function calling enabled,
routing through OpenRouter for model flexibility.
"""

import os
from dataclasses import dataclass, field

import dspy


# Gemini safety settings - disable all content filtering for theological content
# (matches settings in scannerd/model.py)
GEMINI_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_UNSPECIFIED", "threshold": "BLOCK_NONE"},
]


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    litellm_id: str
    providers: list[str]
    temperature: float = 0.7
    max_tokens: int = 8192
    is_vision: bool = False
    is_gemini: bool = False  # Flag to apply Gemini-specific settings
    extra_kwargs: dict = field(default_factory=dict)


# Model registry
MODELS: dict[str, ModelConfig] = {
    # Default / King
    "glm": ModelConfig(
        litellm_id="openrouter/z-ai/glm-4.7",
        providers=["parasail", "novita", "z-ai"],
        temperature=0.6,
        max_tokens=16000,
    ),

    # Fast models
    "grok": ModelConfig(
        litellm_id="openrouter/x-ai/grok-4.1-fast",
        providers=["xai"],
        temperature=0.3,
        max_tokens=8192,
    ),
    "gemini-flash": ModelConfig(
        litellm_id="openrouter/google/gemini-3-flash-preview",
        providers=["google-vertex", "google-ai-studio"],
        temperature=0.7,
        max_tokens=8192,
        is_gemini=True,
    ),

    # Thinking models
    "kimi": ModelConfig(
        litellm_id="openrouter/moonshotai/kimi-k2-thinking",
        providers=["google-vertex", "parasail"],
        temperature=0.6,
        max_tokens=16000,
    ),

    # Other smart models
    "gemini-pro": ModelConfig(
        litellm_id="openrouter/google/gemini-3-pro-preview",
        providers=["google-vertex", "google-ai-studio"],
        temperature=0.7,
        max_tokens=8192,
        is_gemini=True,
    ),
    "qwen": ModelConfig(
        litellm_id="openrouter/qwen/qwen3-235b-a22b-2507",
        providers=["cerebras", "google-vertex"],
        temperature=0.7,
        max_tokens=16000,
    ),

    # Vision models
    "qwen-vl": ModelConfig(
        litellm_id="openrouter/qwen/qwen3-vl-235b-a22b-instruct",
        providers=["novita"],
        temperature=0.3,
        max_tokens=16000,
        is_vision=True,
    ),
    "qwen-vl-think": ModelConfig(
        litellm_id="openrouter/qwen/qwen3-vl-235b-a22b-thinking",
        providers=["novita", "parasail"],
        temperature=0.3,
        max_tokens=16000,
        is_vision=True,
    ),
}


def _get_provider_config(providers: list[str]) -> dict:
    """Build OpenRouter provider routing config."""
    if not providers:
        return {}
    return {
        "extra_body": {
            "provider": {
                "order": providers,
                "allow_fallbacks": False,
                "data_collection": "deny",
            }
        }
    }


def get_lm(
    model: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dspy.LM:
    """
    Get a configured LM instance.

    Args:
        model: Model name from MODELS registry, or a raw litellm model ID
        temperature: Override default temperature
        max_tokens: Override default max_tokens

    Returns:
        Configured dspy.LM instance
    """
    is_gemini = False
    if model in MODELS:
        config = MODELS[model]
        model_id = config.litellm_id
        temp = temperature if temperature is not None else config.temperature
        tokens = max_tokens if max_tokens is not None else config.max_tokens
        provider_config = _get_provider_config(config.providers)
        extra = config.extra_kwargs
        is_gemini = config.is_gemini
    else:
        # Allow raw litellm model IDs for flexibility
        model_id = model
        temp = temperature if temperature is not None else 0.7
        tokens = max_tokens if max_tokens is not None else 8192
        provider_config = {}
        extra = {}
        # Check if raw model ID is Gemini
        is_gemini = "gemini" in model.lower()

    kwargs = {
        "model": model_id,
        "temperature": temp,
        "max_tokens": tokens,
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "base_url": "https://openrouter.ai/api/v1",
        **provider_config,
        **extra,
    }

    # Apply Gemini safety settings to disable content filtering
    if is_gemini:
        kwargs["safety_settings"] = GEMINI_SAFETY_SETTINGS

    return dspy.LM(**kwargs)


def configure_dspy(
    model: str = "glm",
    use_native_tools: bool = True,
    **lm_kwargs,
) -> dspy.LM:
    """
    Configure DSPy globally with native tool calling.

    Args:
        model: Model name or litellm ID
        use_native_tools: Enable native function calling (recommended)
        **lm_kwargs: Additional kwargs passed to get_lm

    Returns:
        The configured LM (also set globally via dspy.configure)
    """
    lm = get_lm(model, **lm_kwargs)
    adapter = dspy.ChatAdapter(use_native_function_calling=use_native_tools)
    dspy.configure(lm=lm, adapter=adapter)
    return lm


def get_fast_lm() -> dspy.LM:
    """Get a fast LM for lightweight tasks."""
    return get_lm("gemini-flash")


def get_smart_lm() -> dspy.LM:
    """Get the primary capable LM for complex reasoning."""
    return get_lm("glm")


def get_vision_lm() -> dspy.LM:
    """Get a vision-capable LM."""
    return get_lm("qwen-vl-think")


def configure_chat_lm(model: str = "glm") -> dspy.LM:
    """Configure DSPy for chat with text-based tool calling.

    DEPRECATED: Use get_chat_context() with dspy.context() for async-safe configuration.

    Sets up both the LM and the ChatAdapter. Native function calling is disabled
    because GLM doesn't support it and DSPy ReAct uses text-based tool calling anyway.

    Args:
        model: Model name from MODELS registry, or raw litellm model ID

    Returns:
        The configured LM (also set globally via dspy.configure)
    """
    lm = get_lm(model)
    adapter = dspy.ChatAdapter(use_native_function_calling=False)
    dspy.configure(lm=lm, adapter=adapter)
    return lm


def get_chat_context(model: str = "glm") -> dict:
    """Get DSPy context kwargs for chat with text-based tool calling.

    Use this with dspy.context() for async-safe per-request configuration.
    Example:
        with dspy.context(**get_chat_context(model)):
            # DSPy operations here

    Args:
        model: Model name from MODELS registry, or raw litellm model ID

    Returns:
        Dict with lm and adapter for dspy.context()
    """
    lm = get_lm(model)
    adapter = dspy.ChatAdapter(use_native_function_calling=False)
    return {"lm": lm, "adapter": adapter}
