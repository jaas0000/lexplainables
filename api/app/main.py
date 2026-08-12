"""Applicatie-samenvoeger — blijft dun (stack-profiel.md §Dunne verzamelaars).
Elke feature draagt zijn eigen router(s); hier komt geen feature-specifieke logica bij."""

from __future__ import annotations

from fastapi import FastAPI

from .features.feedback.router import admin_router as feedback_admin_router
from .features.feedback.router import router as feedback_router

app = FastAPI(title="wetsanalyse-api (referentie-implementatie)")

# Versieprefix zoals werkwijze-ADR-0010: elk contract van deze service onder /v1.
app.include_router(feedback_router, prefix="/v1")
app.include_router(feedback_admin_router, prefix="/v1")
