import uuid
from datetime import timedelta, datetime
from typing import List
from typing import Optional

import pandas as pd
from fastapi import APIRouter
from sqlmodel import Session
from sqlmodel import select

from app.api.deps import SessionDep, CurrentUser
from app.models_crr import SecurityResponseCRR, CRRPortfolioConstituent, SpreadRegion, \
    SpreadAnalysisResponse, SecurityDataResponse, CRRPrice, SecurityResponseMerton, MertonDataResponse, CRRMerton, \
    CDSPrice, CRRSecurity, AddSecurityRequest

router = APIRouter()


@router.get("/portfolio/", response_model=List[SecurityResponseCRR])
async def get_portfolio(
        session: SessionDep, current_user: CurrentUser
) -> List[SecurityResponseCRR]:
    def get_latest_price(sess: Session, model, model_id: uuid.UUID) -> Optional[float]:
        latest_entry = sess.exec(
            select(model)
            .where(model.id == model_id)
            .order_by(model.entry_date.desc())
        ).first()
        return latest_entry.price if latest_entry and latest_entry.price else None

    portfolio_constituents = session.exec(
        select(CRRPortfolioConstituent)
        .where(CRRPortfolioConstituent.user_id == current_user.id)
    ).all()

    portfolio = []
    for constituent in portfolio_constituents:
        security_name = session.get(CRRSecurity, constituent.security_id).ticker_bbg
        cds_price = get_latest_price(session, CDSPrice, constituent.security_id)
        crr_price = get_latest_price(session, CRRPrice, constituent.security_id)
        spread = round(cds_price - crr_price, 2) if crr_price and cds_price else None

        portfolio.append(
            SecurityResponseCRR(
                id=constituent.security_id,
                name=security_name,
                cds_price=cds_price,
                crr_price=crr_price,
                spread=spread,
                sensitivity=constituent.sensitivity
            )
        )

    return portfolio


@router.post("/portfolio/{id}/")
async def add_security_to_portfolio(
        id: uuid.UUID,
        request: AddSecurityRequest,
        session: SessionDep, current_user: CurrentUser
):
    portfolio_entry = CRRPortfolioConstituent(user_id=current_user.id, security_id=id, sensitivity=request.sensitivity)
    session.add(portfolio_entry)
    session.commit()
    return await get_portfolio(session, current_user)


@router.put("/portfolio/{id}/")
async def update_security_settings(
        id: uuid.UUID,
        request: AddSecurityRequest,
        session: SessionDep, current_user: CurrentUser
):
    portfolio_entry = session.exec(
        select(CRRPortfolioConstituent)
        .where(
            CRRPortfolioConstituent.user_id == current_user.id,
            CRRPortfolioConstituent.security_id == id
        )
    ).first()

    portfolio_entry.sensitivity = request.sensitivity
    session.add(portfolio_entry)
    session.commit()
    return await get_portfolio(session, current_user)


@router.delete("/portfolio/{id}/")
async def remove_security_from_portfolio(
        id: uuid.UUID,
        session: SessionDep, current_user: CurrentUser
):
    portfolio_entry = session.exec(
        select(CRRPortfolioConstituent)
        .where(CRRPortfolioConstituent.user_id == current_user.id, CRRPortfolioConstituent.id == id)
    ).first()

    session.delete(portfolio_entry)
    session.commit()
    return await get_portfolio(session, current_user)


@router.get("/spread/{id}/", response_model=SpreadAnalysisResponse)
async def calculate_spread_analysis(
        id: uuid.UUID,
        days: int,
        deviation: int,
        session: SessionDep, current_user: CurrentUser
):
    cds_data = pd.DataFrame(
        [cds.dict() for cds in session.exec(
            select(CDSPrice)
            .where(CDSPrice.security_id == id).order_by(CDSPrice.entry_date))
        .all()]
    )
    cds_data = cds_data.rename(columns={"price": "cds_price", "entry_date": "date"})

    crr_data = pd.DataFrame(
        [crr.dict() for crr in session.exec(
            select(CRRPrice)
            .where(CRRPrice.security_id == id).order_by(CRRPrice.entry_date))
        .all()]
    )
    crr_data = crr_data.rename(columns={"price": "crr_price", "entry_date": "date"})

    df = pd.merge(cds_data, crr_data, on="date", how="inner")
    df["spread"] = df["cds_price"] - df["crr_price"]
    df["rolling"] = df["spread"].rolling(window=days).mean()

    # Handle NaN values in 'rolling' explicitly
    df["rolling"].fillna(0, inplace=True)

    # Calculate standard deviation safely
    if not df["rolling"].isna().all():
        std_dev = df["rolling"].std() * deviation
    else:
        std_dev = 0  # Default value when std_dev can't be computed

    regions = []
    first_green, first_red = None, None
    for _, row in df.iterrows():
        if row["rolling"] > std_dev:
            if first_green is None:
                first_green = row["date"]
        elif first_green:
            regions.append(
                SpreadRegion(spread="positive", x1=first_green, x2=row["date"] - timedelta(days=1))
            )
            first_green = None

        if row["rolling"] < -std_dev:
            if first_red is None:
                first_red = row["date"]
        elif first_red:
            regions.append(
                SpreadRegion(spread="negative", x1=first_red, x2=row["date"] - timedelta(days=1))
            )
            first_red = None

    return SpreadAnalysisResponse(
        regions=regions,
        deviation=std_dev,
    )


@router.get("/security/{id}/", response_model=SecurityDataResponse)
async def get_security_data(
    id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> SecurityDataResponse:
    def to_timestamp(dt: datetime) -> int:
        return int(dt.timestamp())

    crr_data = session.exec(
        select(CRRPrice)
        .where(CRRPrice.security_id == id)
        .order_by(CRRPrice.entry_date)
    ).all()
    crr_prices = [{"date": to_timestamp(row.entry_date), "value": row.price} for row in crr_data]

    cds_data = session.exec(
        select(CDSPrice)
        .where(CDSPrice.security_id == id)
        .order_by(CDSPrice.entry_date)
    ).all()
    cds_prices = [{"date": to_timestamp(row.entry_date), "value": row.price} for row in cds_data]

    crr_dates = {entry["date"] for entry in crr_prices}
    cds_prices = [entry for entry in cds_prices if entry["date"] in crr_dates]

    return SecurityDataResponse(crr=crr_prices, cds=cds_prices)



@router.get("/search-securities/", response_model=List[SecurityResponseMerton])
async def search_securities(
        ticker: str,
        session: SessionDep, current_user: CurrentUser
) -> List[SecurityResponseMerton]:
    print('dodaj')
    securities = session.execute(
        select(CRRSecurity).where(CRRSecurity.ticker_bbg.ilike(f"%{ticker}%"))
    ).scalars().all()

    return [
        SecurityResponseMerton(id=sec.id, ticker_bbg=sec.ticker_bbg)
        for sec in securities
    ]


@router.get("/merton-data/", response_model=MertonDataResponse)
async def get_merton_data(
        id: uuid.UUID,
        period: int,
        session: SessionDep, current_user: CurrentUser
) -> MertonDataResponse:
    merton_data = session.exec(
        select(CRRMerton)
        .where(CRRMerton.id == id, CRRMerton.cds_period == period)
        .order_by(CRRMerton.entry_date)
    ).all()
    cds_deltas = [{"date": row.entry_date, "value": row.cds_delta} for row in merton_data]
    survival_probabilities = [{"date": row.entry_date, "value": row.ps} for row in merton_data]

    prices = session.exec(
        select(CDSPrice)
        .where(CDSPrice.security_id == id)
        .order_by(CDSPrice.entry_date)
    ).all()
    prices = [{"date": row.entry_date, "value": row.price} for row in prices]

    cds_deltas_dates = [cds_delta["date"] for cds_delta in cds_deltas]
    prices = [price for price in prices if price["date"] in cds_deltas_dates]

    return MertonDataResponse(
        price=prices,
        cds_delta=cds_deltas,
        probability_of_survival=survival_probabilities
    )
