from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    decision: Literal["confirmed", "dismissed"] = Field(description="Analyst decision")
    reviewer: str = Field(default="analyst", max_length=64)
    note: str | None = Field(default=None, max_length=500)
