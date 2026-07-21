from sqlalchemy import Delete, Select, Update, event
from sqlalchemy.orm import Session, declarative_base

from app.core.security import current_org_id_var

Base = declarative_base()


@event.listens_for(Session, "do_orm_execute")
def receive_do_orm_execute(orm_execute_state):
    """Intercepts ORM statement executions to append org_id filtering on multi-tenant models."""
    org_id = current_org_id_var.get()
    if org_id is not None and not orm_execute_state.is_column_load:
        statement = orm_execute_state.statement

        # Handle ORM SELECT statements
        if isinstance(statement, Select):
            # Check if any targeted entity has an org_id column
            if hasattr(statement, "column_descriptions"):
                for desc in statement.column_descriptions:
                    entity = desc.get("entity")
                    if entity and hasattr(entity, "org_id"):
                        orm_execute_state.statement = statement.filter(
                            entity.org_id == org_id
                        )

        # Handle ORM UPDATE / DELETE statements
        elif isinstance(statement, (Update, Delete)):
            mapper = orm_execute_state.bind_mapper
            if mapper and hasattr(mapper, "class_"):
                entity = mapper.class_
                if entity and hasattr(entity, "org_id"):
                    orm_execute_state.statement = statement.filter(
                        entity.org_id == org_id
                    )
