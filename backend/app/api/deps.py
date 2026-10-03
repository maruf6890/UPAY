from __future__ import annotations

from dataclasses import dataclass

import asyncpg
from fastapi import Request

from app.services.anomaly_service import AnomalyService
from app.services.brief_service import BriefService
from app.services.liquidity_service import LiquidityService
from app.services.llm_service import LLMService
from app.services.store import AlertStore, DataStore


@dataclass
class Ctx:
    settings: object
    pool: asyncpg.Pool
    store: DataStore
    alerts: AlertStore
    liquidity: LiquidityService
    anomaly: AnomalyService
    llm: LLMService
    brief: BriefService


def get_ctx(request: Request) -> Ctx:
    return request.app.state.ctx
