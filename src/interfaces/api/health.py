from fastapi import APIRouter

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("")
def health():
    return {"status": "ok", "message": "Backend running"}
