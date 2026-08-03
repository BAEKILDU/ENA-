"""환경 변수 로드 (.env / Streamlit secrets)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


def _secret(name: str) -> str:
    """Streamlit Cloud secrets 우선, 없으면 환경변수."""
    try:
        import streamlit as st

        if hasattr(st, "secrets") and name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:  # noqa: BLE001
        pass
    return (os.getenv(name) or "").strip()


def get_openai_api_key() -> str:
    return _secret("OPENAI_API_KEY")


def get_supabase_url() -> str:
    return _secret("SUPABASE_URL")


def get_supabase_anon_key() -> str:
    return _secret("SUPABASE_ANON_KEY")


def get_supabase_service_role_key() -> str:
    return _secret("SUPABASE_SERVICE_ROLE_KEY")


def env_status() -> dict[str, bool]:
    """키가 설정되어 있는지 여부만 반환 (값은 노출하지 않음)."""
    return {
        "OPENAI_API_KEY": bool(get_openai_api_key()),
        "SUPABASE_URL": bool(get_supabase_url()),
        "SUPABASE_ANON_KEY": bool(get_supabase_anon_key()),
    }
