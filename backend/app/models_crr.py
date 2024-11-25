import uuid
from datetime import datetime
from typing import Optional, List, Dict

from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field, Relationship


# Models

class CRRMerton(SQLModel, table=True):
    __tablename__ = "crr_merton"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    entry_date: datetime = Field(nullable=False)
    cds_period: int = Field(nullable=False)
    cds_delta: Optional[float] = None
    ps: Optional[float] = None

    __table_args__ = (UniqueConstraint("entry_date", "cds_period"),)


class CRRSecurity(SQLModel, table=True):
    __tablename__ = "crr_securities"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ticker_bbg: str = Field(max_length=255, unique=True)


class CDSPrice(SQLModel, table=True):
    __tablename__ = "cds_prices"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    security_id: uuid.UUID = Field(foreign_key="crr_securities.id", nullable=False)
    entry_date: datetime = Field(nullable=False)
    price: Optional[float] = None


class CRRPrice(SQLModel, table=True):
    __tablename__ = "crr_prices"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    security_id: uuid.UUID = Field(foreign_key="crr_securities.id", nullable=False)
    entry_date: datetime = Field(nullable=False)
    price: Optional[float] = None


class CRRPortfolioConstituent(SQLModel, table=True):
    __tablename__ = "crr_portfolio_constituents"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(nullable=False, index=True)
    security_id: uuid.UUID = Field(foreign_key="crr_securities.id", nullable=False)
    sensitivity: float = Field(default=1.0)

    __table_args__ = (UniqueConstraint("user_id", "security_id"),)


# Requests

class AddSecurityRequest(SQLModel):
    sensitivity: float


# Responses

class SecurityResponseCRR(SQLModel):
    id: uuid.UUID
    name: str
    cds_price: Optional[float]
    crr_price: Optional[float]
    spread: Optional[float]
    sensitivity: Optional[float]


class SecurityDataResponse(SQLModel):
    crr: List[Dict[str, float]]
    cds: List[Dict[str, float]]


class SecurityResponseMerton(SQLModel):
    id: uuid.UUID
    ticker_bbg: str


class SpreadRegion(SQLModel):
    spread: str
    x1: datetime
    x2: datetime


class SpreadAnalysisResponse(SQLModel):
    regions: List[SpreadRegion]
    deviation: float


class MertonDataResponse(SQLModel):
    price: List[Dict[str, float]]
    cds_delta: List[Dict[str, float]]
    probability_of_survival: List[Dict[str, float]]
