import datetime
from uuid import UUID

import pytest
from app.core.config import settings
from app.models_mri import MRIPortfolio, MRIPortfolioConstituent, MRIAssetOutput
from sqlmodel import Session
from starlette.testclient import TestClient


@pytest.fixture(autouse=True)
def clear_db(db: Session):
    db.query(MRIPortfolioConstituent).delete()
    db.query(MRIPortfolio).delete()
    db.commit()


def test_default_portfolio_time_series(
        client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # Create default portfolio
    default_portfolio_user_id = UUID("00000000-0000-0000-0000-000000000000")
    portfolio = MRIPortfolio(id=default_portfolio_user_id, name="Default Portfolio", user_id=default_portfolio_user_id)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)

    # Create portfolio constituents
    constituent1 = MRIPortfolioConstituent(
        portfolio_id=portfolio.id,
        asset_name="Asset 1",
        asset_domain="Domain 1",
        asset_class="Class 1",
        weight=0.5
    )
    constituent2 = MRIPortfolioConstituent(
        portfolio_id=portfolio.id,
        asset_name="Asset 2",
        asset_domain="Domain 2",
        asset_class="Class 2",
        weight=0.5
    )
    db.add_all([constituent1, constituent2])
    db.commit()

    # Create asset output data
    asset_output1 = MRIAssetOutput(
        date=datetime.datetime.utcnow(),
        domain="Domain 1",
        asset_class="Class 1",
        rpr=100.0,
        lookback=252
    )
    asset_output2 = MRIAssetOutput(
        date=datetime.datetime.utcnow(),
        domain="Domain 2",
        asset_class="Class 2",
        rpr=200.0,
        lookback=252
    )
    db.add_all([asset_output1, asset_output2])
    db.commit()

    # Test the default portfolio time series
    response = client.get(
        f"{settings.API_V1_STR}/mri/default-portfolio?lookback=252",
        headers=superuser_token_headers
    )
    assert response.status_code == 200, f"Unexpected response: {response.json()}"
    data = response.json()
    assert data["name"] == "Default Portfolio"
    assert data["id"] == str(portfolio.id)
    assert len(data["time_series"]) > 0


def test_get_portfolio(
        client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    user_id = UUID("00000000-6666-0000-0000-000000000000")
    portfolio = MRIPortfolio(name="Test Portfolio", user_id=user_id)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)

    response = client.get(
        f"{settings.API_V1_STR}/mri/{portfolio.id}?lookback=252",
        headers=superuser_token_headers
    )
    assert response.status_code == 200, f"Unexpected response: {response.json()}"
    data = response.json()
    assert data["name"] == "Test Portfolio"
    assert data["id"] == str(portfolio.id)


def test_get_user_portfolios(
        client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    user_id = UUID("00000000-6666-0000-0000-000000000000")
    portfolio1 = MRIPortfolio(name="Portfolio 1", user_id=user_id)
    portfolio2 = MRIPortfolio(name="Portfolio 2", user_id=user_id)
    db.add_all([portfolio1, portfolio2])
    db.commit()

    response = client.get(
        f"{settings.API_V1_STR}/mri/",
        headers=superuser_token_headers
    )
    assert response.status_code == 200, f"Unexpected response: {response.json()}"
    data = response.json()
    assert len(data) == 2
    assert any(portfolio["name"] == "Portfolio 1" for portfolio in data)
    assert any(portfolio["name"] == "Portfolio 2" for portfolio in data)


def test_get_default_portfolio(
        client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    default_portfolio_user_id = UUID("00000000-0000-0000-0000-000000000000")
    portfolio = MRIPortfolio(id="00000000-0000-0000-0000-000000000000", name="Default Portfolio",
                             user_id=default_portfolio_user_id)
    db.add(portfolio)
    db.commit()

    response = client.get(
        f"{settings.API_V1_STR}/mri/default-portfolio?lookback=252",
        headers=superuser_token_headers
    )
    assert response.status_code == 200, f"Unexpected response: {response.json()}"
    data = response.json()
    assert data["name"] == "Default Portfolio"
    assert data["id"] == str(portfolio.id)


def test_create_portfolio(
        client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    portfolio_data = {
        "name": "New Portfolio",
        "assets": [
            {
                "asset_name": "Asset 1",
                "asset_domain": "Domain 1",
                "asset_class": "Class 1",
                "weight": 0.5
            },
            {
                "asset_name": "Asset 2",
                "asset_domain": "Domain 2",
                "asset_class": "Class 2",
                "weight": 0.5
            }
        ]
    }

    response = client.post(
        f"{settings.API_V1_STR}/mri/",
        headers=superuser_token_headers,
        json=portfolio_data
    )
    assert response.status_code == 200, f"Unexpected response: {response.json()}"
    data = response.json()
    assert data["name"] == "New Portfolio"
    assert len(data["assets"]) == 2


def test_update_portfolio(
        client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    user_id = UUID("00000000-6666-0000-0000-000000000000")
    portfolio = MRIPortfolio(name="Old Portfolio", user_id=user_id)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)

    update_data = {
        "name": "Updated Portfolio",
        "assets": [
            {
                "asset_name": "Updated Asset 1",
                "asset_domain": "Updated Domain 1",
                "asset_class": "Updated Class 1",
                "weight": 0.7
            }
        ]
    }

    response = client.put(
        f"{settings.API_V1_STR}/mri/{portfolio.id}",
        headers=superuser_token_headers,
        json=update_data
    )
    assert response.status_code == 200, f"Unexpected response: {response.json()}"
    data = response.json()
    assert data["name"] == "Updated Portfolio"
    assert len(data["assets"]) == 1
    assert data["assets"][0]["weight"] == 0.7


def test_delete_portfolio(
        client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    user_id = UUID("00000000-6666-0000-0000-000000000000")
    portfolio = MRIPortfolio(name="Portfolio to Delete", user_id=user_id)
    db.add(portfolio)
    db.commit()

    response = client.delete(
        f"{settings.API_V1_STR}/mri/{portfolio.id}",
        headers=superuser_token_headers
    )
    assert response.status_code == 200

    response = client.get(
        f"{settings.API_V1_STR}/mri/{portfolio.id}?lookback=252",
        headers=superuser_token_headers
    )
    assert response.status_code == 404
