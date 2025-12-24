import os
import random
import dspy
import re

PREFILL = "Alright, let me make sure I remember the rules. First, I'm supposed to fill in the `reasoning` field in my output object. Let's see if there's any custom instructions for how to structure my reasoning in `[[ ## reasoning_rules ## ]]`..."

llm_log = open("../llm.log", "w")

class DarkLLM(dspy.LM):
    def __init__(self, *args, **kwargs):
        self.nosys = kwargs.get('nosys', False)
        self.noprefill = kwargs.get('noprefill', False)
        self.model_name = kwargs.get('model_name', None)
        if 'nosys' in kwargs:
            del kwargs['nosys']
        if 'noprefill' in kwargs:
            del kwargs['noprefill']
        super().__init__(*args, **kwargs)
        
    def forward(self, prompt=None, messages=None, **kwargs):
        if self.nosys:
            for message in messages:
                if message["role"] == "system":
                    message["role"] = "user"
        if not self.noprefill:
            messages = messages + [{"role": "assistant", "content": PREFILL}] 
        
        for message in messages:
            llm_log.write(f" ## {self.model} ##\n\n")
            llm_log.write(f" ## {message['role']} ##\n\n {message['content']}\n\n")

        return super().forward(prompt, messages, **kwargs)
    
    def aforward(self, prompt=None, messages=None, **kwargs):
        if self.nosys:
            for message in messages:
                if message["role"] == "system":
                    message["role"] = "user"
        if not self.noprefill:
            messages = messages + [{"role": "assistant", "content": PREFILL}] 
        return super().afoward(prompt, messages, **kwargs)

gemini_safety_settings = {
    "safety_settings": [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_UNSPECIFIED",
            "threshold": "BLOCK_NONE",
        }
    ]
}

def get_lm(model):
    def _get_provider(providers: list[str], stealth_mode: bool = False) -> dict:
        if stealth_mode:
            return {
                "provider": {
                    "order": ["stealth"],
                }
            }
        return {
            "provider": {
                "order": providers,
                "allow_fallbacks": False,
                "data_collection": 'deny'
            }
        }
    if model == "gpt5-chat":
        lm = DarkLLM(model='openai/gpt-5-chat-latest', temperature=1.0, max_tokens=16000, api_key=os.getenv('OPENAI_API_KEY'))
    elif model == "gpt5":
        lm = DarkLLM(model='openai/gpt-5-2025-08-07', temperature=1.0, max_tokens=16000, api_key=os.getenv('OPENAI_API_KEY'))
    elif model == "or-gpt5-chat":
        lm = DarkLLM(model='openrouter/openai/gpt-5-chat', temperature=1.0, max_tokens=32000, api_key=os.getenv('OPENROUTER_API_KEY'), base_url='https://openrouter.ai/api/v1', extra_body=_get_provider(["openai"]))
    elif model == "glm-47":
        lm = DarkLLM(model='openrouter/z-ai/glm-4.7', temperature=0.6, max_tokens=8192, api_key=os.getenv('OPENROUTER_API_KEY'), base_url='https://openrouter.ai/api/v1', extra_body=_get_provider(["z-ai", "parasail"]))
    elif model == "qwen-think":
        lm = DarkLLM(model='openrouter/qwen/qwen3-235b-a22b-thinking-2507', noprefill=True, temperature=0.7, max_tokens=16000, api_key=os.getenv('OPENROUTER_API_KEY'), base_url='https://openrouter.ai/api/v1', extra_body=_get_provider(["cerebras", "novita"]))
    elif model == "qwen-instruct":
        lm = DarkLLM(model='openrouter/qwen/qwen3-235b-a22b-2507', temperature=0.7, top_p=0.8, top_k=20, max_tokens=16000, api_key=os.getenv('OPENROUTER_API_KEY'), base_url='https://openrouter.ai/api/v1', extra_body=_get_provider(["cerebras", "novita"]))
    elif model == "opus":
        lm = DarkLLM(model='openrouter/anthropic/claude-opus-4.5', thinking_budget=0, temperature=0.9, max_tokens=8192, api_key=os.getenv('OPENROUTER_API_KEY'), base_url='https://openrouter.ai/api/v1', extra_body=_get_provider(["anthropic"]))
    elif model == "sonnet":
        lm = DarkLLM(model='openrouter/anthropic/claude-sonnet-4.5', thinking_budget=0, temperature=0.8, max_tokens=8192, api_key=os.getenv('OPENROUTER_API_KEY'), base_url='https://openrouter.ai/api/v1', extra_body=_get_provider(["anthropic"]))
    elif model == "grok-4":
        lm = DarkLLM(model='openrouter/x-ai/grok-4', temperature=1.1, max_tokens=8192, api_key=os.getenv('OPENROUTER_API_KEY'), base_url='https://openrouter.ai/api/v1', extra_body=_get_provider(["xai"]))
    elif model == "grok-4.1-fast":
        lm = DarkLLM(model='openrouter/x-ai/grok-4.1-fast', noprefill=True, temperature=0.3, max_tokens=8192, api_key=os.getenv('OPENROUTER_API_KEY'), base_url='https://openrouter.ai/api/v1', extra_body=_get_provider(["xai"]))
    elif model == "deepseek":
        lm = DarkLLM(model='openrouter/deepseek/deepseek-chat-v3-0324', temperature=0.4,  max_tokens=8192, api_key=os.getenv('OPENROUTER_API_KEY'), base_url='https://openrouter.ai/api/v1', extra_body=_get_provider(["baseten", "gmicloud", "fireworks"]))
    elif model == "gemini-pro":
        lm = DarkLLM(model='openrouter/google/gemini-3-pro-preview', temperature=1.0, thinking_budget=0, max_tokens=8192, api_key=os.getenv('OPENROUTER_API_KEY'), base_url='https://openrouter.ai/api/v1', extra_body=_get_provider(["google", "google-vertex/global", "google-vertex/us"]), nosys=True, stream=False, **gemini_safety_settings)
    elif model == "kimi-k2":
        lm = DarkLLM(model='openrouter/moonshotai/kimi-k2-0905', temperature=0.65, max_tokens=8192, api_key=os.getenv('OPENROUTER_API_KEY'), base_url='https://openrouter.ai/api/v1', extra_body=_get_provider(["groq", "fireworks", "novita"]))
    elif model == "qwen3-max":
        lm = DarkLLM(model='openrouter/qwen/qwen3-max', temperature=0.65, max_tokens=8192, api_key=os.getenv('OPENROUTER_API_KEY'), base_url='https://openrouter.ai/api/v1', extra_body=_get_provider(["alibaba"]))
    elif model == "qwen3-vl":
        lm = DarkLLM(model='openrouter/qwen/qwen3-vl-30b-a3b-instruct', noprefill=True, temperature=0.3, max_tokens=16000, api_key=os.getenv('OPENROUTER_API_KEY'), base_url='https://openrouter.ai/api/v1', extra_body=_get_provider(["novita"]))
    elif model == "qwen3-vl-think":
        lm = DarkLLM(model='openrouter/qwen/qwen3-vl-235b-a22b-thinking', noprefill=True, temperature=0.3, max_tokens=16000, api_key=os.getenv('OPENROUTER_API_KEY'), base_url='https://openrouter.ai/api/v1', extra_body=_get_provider(["novita"]))
    else:
        raise ValueError(f"Invalid model: {model}")
    return lm
