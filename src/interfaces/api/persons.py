from fastapi import APIRouter, Depends, HTTPException, Query

from src.interfaces.dependencies import verify_support_key
from src.app.use_cases.person_use_cases import PersonUseCases

router = APIRouter(prefix="/api/persons", tags=["Persons"])


@router.get("/by-document")
def get_person(
    nit: str = Query(...),
    _: bool = Depends(verify_support_key),
):
    if not nit:
        raise HTTPException(status_code=400, detail="Documento requerido")

    uc = PersonUseCases()
    result = uc.find_by_document(nit)
    return result
