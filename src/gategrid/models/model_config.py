from __future__ import annotations

from pydantic import BaseModel


class ModelConfig(BaseModel):
    provider: str
    model_name: str
    api_key_env: str
    base_url: str | None = None
