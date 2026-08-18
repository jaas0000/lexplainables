"""Applicatie-samenvoeger — blijft dun (stack-profiel.md §Dunne verzamelaars).
Elke feature draagt zijn eigen router(s); hier komt geen feature-specifieke logica bij."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .features.berichten.router import admin_router as berichten_admin_router
from .features.berichten.router import router as berichten_router
from .features.feedback.router import admin_router as feedback_admin_router
from .features.feedback.router import router as feedback_router
from .features.identiteit_toegang.router import admin_router as gebruikers_admin_router
from .features.identiteit_toegang.router import router as auth_router
from .features.llm_profielen.router import admin_router as llm_profielen_admin_router
from .features.projecten.router import router as projecten_router
from .features.runtime_config.router import admin_router as runtime_config_admin_router
from .features.wetcatalogus.router import admin_router as wetcatalogus_admin_router
from .features.wetcatalogus.router import router as wetcatalogus_router

app = FastAPI(title="wetsanalyse-api (referentie-implementatie)")

# CORS: publieke routes zijn toegankelijk vanuit de browser. Admin-routes gaan via de BFF
# (ADR-0003). Origins komen uit een env-var; default "*" voor lokale ontwikkeling.
# Stel CORS_ALLOW_ORIGINS in op de frontend-origin in productie (bijv. "https://app.example.com").
_cors_origins = os.environ.get("CORS_ALLOW_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", include_in_schema=False)
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


# Versieprefix zoals werkwijze-ADR-0010: elk contract van deze service onder /v1.
app.include_router(feedback_router, prefix="/v1")
app.include_router(feedback_admin_router, prefix="/v1")
app.include_router(berichten_router, prefix="/v1")
app.include_router(berichten_admin_router, prefix="/v1")
app.include_router(auth_router, prefix="/v1")
app.include_router(gebruikers_admin_router, prefix="/v1")
app.include_router(wetcatalogus_router, prefix="/v1")
app.include_router(wetcatalogus_admin_router, prefix="/v1")
app.include_router(llm_profielen_admin_router, prefix="/v1")
app.include_router(runtime_config_admin_router, prefix="/v1")
app.include_router(projecten_router, prefix="/v1")
