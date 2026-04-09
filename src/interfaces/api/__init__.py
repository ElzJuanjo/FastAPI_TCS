from .health import router as health_router
from .events import router as events_router
from .orders import router as orders_router
from .payments import router as payments_router
from .persons import router as persons_router
from .webhooks import router as webhooks_router

all_routers = [
    health_router,
    events_router,
    orders_router,
    payments_router,
    persons_router,
    webhooks_router,
]
