from collections.abc import Generator
from datetime import datetime, timedelta
from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, SQLModel

from app.api.deps import CurrentUser
from app.core import security
from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import Item, User
from app.tests.utils.user import authentication_token_from_email


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    SQLModel.metadata.create_all(engine)  # Create all tables
    with Session(engine) as session:
        init_db(session)
        yield session
        statement = delete(Item)
        session.execute(statement)
        statement = delete(User)
        session.execute(statement)
        session.commit()
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def current_user():
    return CurrentUser(id=1, is_superuser=True)  # Mock a user with id=1


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def superuser_token_headers(db: Session) -> dict[str, str]:
    user_id = UUID("00000000-6666-0000-0000-000000000000")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(
            id=user_id,
            email="superuser@example.com",
            hashed_password="fakehashedpassword",
            is_superuser=True,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "sub": str(user.id),
        "exp": datetime.utcnow() + token_expires
    }
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=security.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
