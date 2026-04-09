from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infra.config.settings import get_settings
from src.infra.config.logging_config import setup_logging
from src.interfaces.api import all_routers

# ===========================
# SETUP
# ===========================
setup_logging()
settings = get_settings()

app = FastAPI(
    title="Events API",
    description="API de gestión de eventos - Teatro/Cine + Carreras",
    version="2.0.0",
)

# ===========================
# CORS
# ===========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================
# ROUTERS
# ===========================
for router in all_routers:
    app.include_router(router)
