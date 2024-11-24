import uuid
from datetime import datetime
from typing import Optional, List, Dict

from sqlmodel import SQLModel, Field, Relationship


# Models

class MRIPortfolio(SQLModel, table=True):
    __tablename__ = "mri_portfolios"  # Explicit table name
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True, max_length=255)
    user_id: uuid.UUID = Field(index=True, nullable=False)

    assets: list["MRIPortfolioConstituent"] = Relationship(back_populates="portfolio")


class MRIPortfolioConstituent(SQLModel, table=True):
    __tablename__ = "mri_portfolio_constituents"  # Explicit table name
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    portfolio_id: uuid.UUID = Field(foreign_key="mri_portfolios.id", nullable=False)
    asset_name: str = Field(max_length=255)
    asset_domain: str = Field(max_length=255)
    asset_class: str = Field(max_length=255)
    weight: float = Field(nullable=False, ge=0.0, le=1.0)

    portfolio: MRIPortfolio = Relationship(back_populates="assets")


class MRIAssetOutput(SQLModel, table=True):
    __tablename__ = "mri_asset_outputs"  # Explicit table name
    date: datetime = Field(primary_key=True)
    domain: str = Field(max_length=255, nullable=False)
    asset_class: str = Field(max_length=255, nullable=False)  # Renamed from `class_`
    rpr: float = Field(nullable=False)
    lookback: int = Field(nullable=False)


# Request and Response Models

# Responses

class PortfolioConstituentResponse(SQLModel):
    id: Optional[str]
    asset_name: str
    asset_domain: str
    asset_class: str
    weight: float


class PortfolioResponse(SQLModel):
    id: str
    name: str
    user_id: str
    assets: List[PortfolioConstituentResponse]
    time_series: Optional[List[Dict[str, float]]] = []


# Creates

class PortfolioConstituentCreate(SQLModel):
    asset_name: str
    asset_domain: str
    asset_class: str
    weight: float


class PortfolioCreate(SQLModel):
    name: str
    assets: List[PortfolioConstituentCreate]


# Updates

class PortfolioConstituentUpdate(SQLModel):
    id: Optional[str] = None
    asset_name: Optional[str] = None
    asset_domain: Optional[str] = None
    asset_class: Optional[str] = None
    weight: Optional[float] = None


class PortfolioUpdate(SQLModel):
    name: Optional[str] = None
    assets: Optional[List[PortfolioConstituentUpdate]] = None
