
import os
import streamlit as st
from dataclasses import dataclass
from dotenv import load_dotenv

# Load the .env file from the frontend project root
load_dotenv(override=False)


@dataclass
class Config:
    supabase_url: str
    supabase_key: str
    api_base_url: str
    request_timeout: int = 30


def getv(name, default=""):
    try:
        value = st.secrets.get(name, None)
        if value is not None:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, default)


def get_config():
    return Config(
        supabase_url=getv("SUPABASE_URL").rstrip("/"),
        supabase_key=(
            getv("SUPABASE_PUBLISHABLE_KEY")
            or getv("SUPABASE_KEY")
        ),
        api_base_url=getv(
            "JURISMIND_API_URL",
            "http://127.0.0.1:8000"
        ).rstrip("/"),
        request_timeout=int(
            getv("JURISMIND_REQUEST_TIMEOUT", "30")
        ),
    )
