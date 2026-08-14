from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization, get_db_with_org
from app.models import Organization
from app.schemas.organization import OrganizationRead, OrganizationUpdate

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/me", response_model=OrganizationRead)
def get_my_organization(org: Organization = Depends(get_current_organization)):
    return org


@router.put("/me", response_model=OrganizationRead)
def update_my_organization(
    payload: OrganizationUpdate,
    org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db_with_org),
):
    if payload.name is not None:
        org.name = payload.name
    if payload.configuration is not None:
        org.configuration = payload.configuration
    db.commit()
    db.refresh(org)
    return org
