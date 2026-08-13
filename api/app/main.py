"""Applicatie-samenvoeger — blijft dun (stack-profiel.md §Dunne verzamelaars).
Elke feature draagt zijn eigen router(s); hier komt geen feature-specifieke logica bij."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .features.berichten.router import admin_router as berichten_admin_router
from .features.berichten.router import router as berichten_router
from .features.feedback.router import admin_router as feedback_admin_router
from .features.feedback.router import router as feedback_router

app = FastAPI(title="wetsanalyse-api (referentie-implementatie)")

# CORS: `frontend` (ADR-0017) roept deze API rechtstreeks vanuit de browser aan (geen
# same-origin BFF-proxyroute), dus zonder dit blokkeert de browser elke fetch vanaf een ander
# poortnummer. Alle origins toegestaan — passend bij de vereenvoudigde auth-stand-in
# (shared/auth.py); een echte origin-allowlist hoort bij het latere, echte auth-domein.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Versieprefix zoals werkwijze-ADR-0010: elk contract van deze service onder /v1.
app.include_router(feedback_router, prefix="/v1")
app.include_router(feedback_admin_router, prefix="/v1")
app.include_router(berichten_router, prefix="/v1")
app.include_router(berichten_admin_router, prefix="/v1")
