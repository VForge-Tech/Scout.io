from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_with_org
from app.models import Chatbot, Policy, User
from app.schemas.policy import PolicyCreate, PolicyRead, PolicyUpdate

router = APIRouter(tags=["policies"])


def _get_chatbot(db: Session, chatbot_id: UUID, user: User) -> Chatbot:
    chatbot = (
        db.query(Chatbot)
        .filter(
            Chatbot.id == chatbot_id,
            Chatbot.organization_id == user.organization_id,
        )
        .first()
    )
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found",
        )
    return chatbot


def _get_policy(db: Session, policy_id: UUID, org_id: UUID) -> Policy:
    policy = (
        db.query(Policy)
        .filter(Policy.id == policy_id, Policy.organization_id == org_id)
        .first()
    )
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )
    return policy


@router.get(
    "/chatbots/{chatbot_id}/policies",
    response_model=list[PolicyRead],
)
def list_policies(
    chatbot_id: UUID,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    _get_chatbot(db, chatbot_id, user)
    return (
        db.query(Policy)
        .filter(
            Policy.organization_id == user.organization_id,
            Policy.chatbot_id == chatbot_id,
        )
        .all()
    )


@router.post(
    "/chatbots/{chatbot_id}/policies",
    response_model=PolicyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_policy(
    chatbot_id: UUID,
    payload: PolicyCreate,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    _get_chatbot(db, chatbot_id, user)
    policy = Policy(
        organization_id=user.organization_id,
        chatbot_id=chatbot_id,
        name=payload.name,
        policy_type=payload.policy_type,
        rules=payload.rules,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get(
    "/chatbots/{chatbot_id}/policies/{policy_id}",
    response_model=PolicyRead,
)
def get_policy(
    chatbot_id: UUID,
    policy_id: UUID,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    _get_chatbot(db, chatbot_id, user)
    return _get_policy(db, policy_id, user.organization_id)


@router.put(
    "/chatbots/{chatbot_id}/policies/{policy_id}",
    response_model=PolicyRead,
)
def update_policy(
    chatbot_id: UUID,
    policy_id: UUID,
    payload: PolicyUpdate,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    _get_chatbot(db, chatbot_id, user)
    policy = _get_policy(db, policy_id, user.organization_id)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)
    db.commit()
    db.refresh(policy)
    return policy


@router.delete(
    "/chatbots/{chatbot_id}/policies/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_policy(
    chatbot_id: UUID,
    policy_id: UUID,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    _get_chatbot(db, chatbot_id, user)
    policy = _get_policy(db, policy_id, user.organization_id)
    db.delete(policy)
    db.commit()
    return None


@router.get(
    "/policies",
    response_model=list[PolicyRead],
)
def list_org_policies(
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    return (
        db.query(Policy)
        .filter(
            Policy.organization_id == user.organization_id,
            Policy.chatbot_id.is_(None),
        )
        .all()
    )


@router.post(
    "/policies",
    response_model=PolicyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_org_policy(
    payload: PolicyCreate,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    policy = Policy(
        organization_id=user.organization_id,
        name=payload.name,
        policy_type=payload.policy_type,
        rules=payload.rules,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy
