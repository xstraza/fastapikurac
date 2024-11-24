from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete
from sqlalchemy.sql import func
from sqlmodel import select

from app.api.deps import SessionDep, CurrentUser
from app.models_mri import (
    MRIPortfolio,
    MRIPortfolioConstituent,
    MRIAssetOutput,
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioResponse,
    PortfolioConstituentResponse,
)

router = APIRouter()


@router.get("/default-portfolio", response_model=PortfolioResponse, tags=["mri"])
def get_default_portfolio(
        *, session: SessionDep, current_user: CurrentUser
) -> PortfolioResponse:
    return get_portfolio(session=session, current_user=current_user, id="00000000-0000-0000-0000-000000000000",
                         lookback=252)


@router.get("/", response_model=List[PortfolioResponse])
def get_user_portfolios(
        *, session: SessionDep, current_user: CurrentUser
) -> List[PortfolioResponse]:
    portfolios = session.exec(
        select(MRIPortfolio).where(MRIPortfolio.user_id == current_user.id)
    ).all()

    admin_portfolios = session.exec(
        select(MRIPortfolio).where(MRIPortfolio.user_id == UUID("00000000-0000-0000-0000-000000000000"))
    ).all()
    portfolios.extend(admin_portfolios)

    response = [
        PortfolioResponse(
            id=str(portfolio.id),
            name=portfolio.name,
            user_id=str(portfolio.user_id),
            assets=[
                PortfolioConstituentResponse(
                    id=str(asset.id),
                    asset_name=asset.asset_name,
                    asset_domain=asset.asset_domain,
                    asset_class=asset.asset_class,
                    weight=asset.weight
                )
                for asset in session.exec(
                    select(MRIPortfolioConstituent).where(
                        MRIPortfolioConstituent.portfolio_id == portfolio.id
                    )
                ).all()
            ]
        )
        for portfolio in portfolios
    ]

    return response


@router.get("/{id}", response_model=PortfolioResponse)
def get_portfolio(
        *, session: SessionDep, current_user: CurrentUser, id: str, lookback: int
) -> PortfolioResponse:
    portfolio = session.get(MRIPortfolio, id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if id is not "00000000-0000-0000-0000-000000000000" and portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    constituents = session.exec(
        select(MRIPortfolioConstituent).where(
            MRIPortfolioConstituent.portfolio_id == id
        )
    ).all()

    assets = []
    aggregated_data = session.exec(
        select(
            MRIAssetOutput.date,
            func.sum(MRIAssetOutput.rpr * MRIPortfolioConstituent.weight).label("Value")
        )
        .join(MRIPortfolioConstituent,
              (MRIAssetOutput.asset_class == MRIPortfolioConstituent.asset_class) &
              (MRIAssetOutput.domain == MRIPortfolioConstituent.asset_domain))
        .where(
            MRIPortfolioConstituent.portfolio_id == id,
            MRIAssetOutput.lookback == lookback
        )
        .group_by(MRIAssetOutput.date)
        .order_by(MRIAssetOutput.date)
    ).all()

    for constituent in constituents:
        assets.append(
            PortfolioConstituentResponse(
                id=str(constituent.id),
                asset_name=constituent.asset_name,
                asset_domain=constituent.asset_domain,
                asset_class=constituent.asset_class,
                weight=constituent.weight,
            )
        )

    return PortfolioResponse(
        id=str(portfolio.id),
        name=portfolio.name,
        user_id=str(portfolio.user_id),
        assets=assets,
        time_series=[{"Date": date, "Value": value} for date, value in aggregated_data]
    )


@router.post("/", response_model=PortfolioResponse)
def create_portfolio(
        *, session: SessionDep, current_user: CurrentUser, portfolio_in: PortfolioCreate
) -> PortfolioResponse:
    portfolio = MRIPortfolio(
        name=portfolio_in.name,
        user_id=str(current_user.id)
    )
    session.add(portfolio)
    session.commit()
    session.refresh(portfolio)

    assets = []
    for asset in portfolio_in.assets:
        constituent = MRIPortfolioConstituent(
            portfolio_id=str(portfolio.id),
            asset_name=asset.asset_name,
            asset_domain=asset.asset_domain,
            asset_class=asset.asset_class,
            weight=asset.weight,
        )
        session.add(constituent)
        session.commit()
        session.refresh(constituent)
        assets.append(
            PortfolioConstituentResponse(
                id=str(constituent.id),
                asset_name=constituent.asset_name,
                asset_domain=constituent.asset_domain,
                asset_class=constituent.asset_class,
                weight=constituent.weight
            )
        )

    return PortfolioResponse(
        id=str(portfolio.id),
        name=portfolio.name,
        user_id=str(portfolio.user_id),
        assets=assets
    )


@router.put("/{id}", response_model=PortfolioResponse)
def update_portfolio(
        *,
        session: SessionDep,
        current_user: CurrentUser,
        id: str,
        portfolio_in: PortfolioUpdate
) -> PortfolioResponse:
    portfolio = session.get(MRIPortfolio, id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    portfolio.name = portfolio_in.name
    session.add(portfolio)

    session.exec(
        delete(MRIPortfolioConstituent).where(
            MRIPortfolioConstituent.portfolio_id == id
        )
    )

    for asset in portfolio_in.assets:
        constituent = MRIPortfolioConstituent(
            portfolio_id=str(id),
            asset_name=asset.asset_name,
            asset_domain=asset.asset_domain,
            asset_class=asset.asset_class,
            weight=asset.weight,
        )
        session.add(constituent)
    session.commit()
    session.refresh(portfolio)

    db_assets = session.exec(select(MRIPortfolioConstituent).where(MRIPortfolioConstituent.portfolio_id == id))
    assets = [
        PortfolioConstituentResponse(id=str(asset.id), asset_name=asset.asset_name, asset_domain=asset.asset_domain,
                                     asset_class=asset.asset_class, weight=asset.weight, ) for asset in
        db_assets.all()]
    return PortfolioResponse(
        id=str(portfolio.id),
        name=portfolio.name,
        user_id=str(portfolio.user_id),
        assets=assets
    )


@router.delete("/{id}")
def delete_portfolio(
        *, session: SessionDep, current_user: CurrentUser, id: str
) -> None:
    portfolio = session.get(MRIPortfolio, id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    session.exec(
        delete(MRIPortfolioConstituent).where(
            MRIPortfolioConstituent.portfolio_id == id
        )
    )

    session.delete(portfolio)
    session.commit()
    return None
