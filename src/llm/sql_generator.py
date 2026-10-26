"""Multi-provider LLM interface for generating SQL queries from natural language."""

import json
import re
from typing import Any, Dict, Optional

from src.config import (
    DEFAULT_PROVIDER,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    TEMPERATURE,
)
from src.llm.guardrails import format_sql, validate_sql_query
from src.llm.prompts import FEW_SHOT_EXAMPLES, SYSTEM_PROMPT


class SQLGenerator:
    """Handles prompt construction and model calling across Groq, Gemini, and OpenAI."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = TEMPERATURE,
    ):
        self.provider = (provider or DEFAULT_PROVIDER).lower()
        self.temperature = temperature
        self.model = model

        # Set API key and model per provider
        if self.provider == "groq":
            self.api_key = api_key or GROQ_API_KEY
            self.model = self.model or GROQ_MODEL
        elif self.provider == "gemini":
            self.api_key = api_key or GEMINI_API_KEY
            self.model = self.model or GEMINI_MODEL
        elif self.provider == "openai":
            self.api_key = api_key or OPENAI_API_KEY
            self.model = self.model or OPENAI_MODEL
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _call_groq(self, user_content: str) -> str:
        """Invokes Groq API."""
        if not self.api_key:
            raise ValueError("Groq API key is missing. Please set GROQ_API_KEY in .env or settings.")
        from groq import Groq

        client = Groq(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=self.temperature,
            max_tokens=1500,
        )
        return response.choices[0].message.content or ""

    def _call_gemini(self, user_content: str) -> str:
        """Invokes Google Gemini API."""
        if not self.api_key:
            raise ValueError("Gemini API key is missing. Please set GEMINI_API_KEY in .env or settings.")
        from google import genai

        client = genai.Client(api_key=self.api_key)
        prompt = f"{SYSTEM_PROMPT}\n\nUser Request:\n{user_content}"
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return response.text or ""

    def _call_openai(self, user_content: str) -> str:
        """Invokes OpenAI API."""
        if not self.api_key:
            raise ValueError("OpenAI API key is missing. Please set OPENAI_API_KEY in .env or settings.")
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=self.temperature,
            max_tokens=1500,
        )
        return response.choices[0].message.content or ""

    def _parse_llm_response(self, raw_output: str) -> Dict[str, Any]:
        """Robustly parses LLM JSON output with fallback heuristics."""
        text = raw_output.strip()

        # Remove markdown code blocks if wrapped
        if text.startswith("```"):
            text = re.sub(r"^```(?:json|sql)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)

        # Attempt standard JSON decoding
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "sql" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

        # Regex fallback to extract JSON object
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                if isinstance(parsed, dict) and "sql" in parsed:
                    return parsed
            except json.JSONDecodeError:
                pass

        # Regex fallback for pure SQL block if JSON wasn't returned
        sql_match = re.search(r"(SELECT\s+[\s\S]+?;)", raw_output, re.IGNORECASE)
        if sql_match:
            return {
                "sql": sql_match.group(1).strip(),
                "explanation": "Generated from natural language query.",
                "assumptions": "",
            }

        return {
            "sql": text,
            "explanation": "Could not format query response automatically.",
            "assumptions": "",
        }

    def generate_sql(self, natural_language_query: str, schema_context: str) -> Dict[str, Any]:
        """Generates a SQL query, explanation, and metadata for a user question."""
        user_prompt = f"""### DATABASE SCHEMA:
{schema_context}

### REFERENCE EXAMPLES:
{FEW_SHOT_EXAMPLES}

### USER QUESTION:
"{natural_language_query}"

Generate the SQLite query and explanation as specified in the JSON schema.
"""
        if self.provider == "groq":
            raw_response = self._call_groq(user_prompt)
        elif self.provider == "gemini":
            raw_response = self._call_gemini(user_prompt)
        elif self.provider == "openai":
            raw_response = self._call_openai(user_prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        parsed = self._parse_llm_response(raw_response)
        raw_sql = parsed.get("sql", "").strip()
        formatted = format_sql(raw_sql)

        return {
            "sql": formatted or raw_sql,
            "raw_sql": raw_sql,
            "explanation": parsed.get("explanation", "No explanation provided."),
            "assumptions": parsed.get("assumptions", ""),
            "provider": self.provider,
            "model": self.model,
            "raw_response": raw_response,
        }
