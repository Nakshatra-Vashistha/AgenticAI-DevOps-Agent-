"""
LLM factory for the DevOps multi-agent system.
Dynamically handles model declarations from environment variables with strict SecretStr typing.
"""

import os
from pydantic import SecretStr  # <-- IMPORT THIS
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI


class LLMBrainFactory:
    """
    Unified factory to instantiate the LLM brain.
    Allows seamless switching between Gemini and Grok via environment configurations.
    """

    @staticmethod
    def get_llm() -> BaseChatModel:
        """
        Create and return a chat model based on the LLM_PROVIDER environment variable.
        """
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()

        if provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            
            if not api_key:
                raise ValueError(
                    "GEMINI_API_KEY environment variable is required when LLM_PROVIDER=gemini"
                )
            
            # Wrap the string api_key in a SecretStr object to satisfy Pydantic and Pylance
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=SecretStr(api_key),  # <-- PATCH APPLIED HERE
                temperature=0.2,
            )

        if provider == "grok":
            api_key = os.getenv("GROK_API_KEY")
            if not api_key:
                raise ValueError(
                    "GROK_API_KEY environment variable is required when LLM_PROVIDER=grok"
                )
                
            # Wrap the string api_key in a SecretStr object to satisfy Pydantic and Pylance
            return ChatOpenAI(
                model="grok-beta",
                api_key=SecretStr(api_key),         # <-- PATCH APPLIED HERE
                base_url="https://api.x.ai/v1",
            )

        raise ValueError(f"Unsupported LLM provider: {provider}. Choose 'gemini' or 'grok'.")