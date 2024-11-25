import uuid
import datetime
import pytest
from sqlmodel import Session
from starlette.testclient import TestClient
from app.models_crr import CRRPortfolioConstituent, CRRSecurity, CDSPrice, CRRPrice, CRRMerton
from app.core.config import settings


@pytest.fixture(autouse=True)
def clear_db(db: Session):
    try:
        db.rollback()  # Ensure no lingering transactions
        db.query(CDSPrice).delete()
        db.query(CRRPrice).delete()
        db.query(CRRPortfolioConstituent).delete()
        db.query(CRRMerton).delete()
        db.query(CRRSecurity).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        raise e



def test_get_portfolio(client: TestClient, superuser_token_headers: dict[str, str], db: Session) -> None:
    user_id = "00000000-6666-0000-0000-000000000000"
    security_id = uuid.uuid4()
    security = CRRSecurity(id=security_id, ticker_bbg="TEST")
    db.add(security)
    db.commit()

    constituent = CRRPortfolioConstituent(user_id=user_id, security_id=security.id, sensitivity=0.5)
    db.add(constituent)
    db.commit()

    response = client.get(f"{settings.API_V1_STR}/crr/portfolio/", headers=superuser_token_headers)
    assert response.status_code == 200, f"Unexpected response: {response.json()}"
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "TEST"


def test_add_security_to_portfolio(client: TestClient, superuser_token_headers: dict[str, str], db: Session) -> None:
    security_id = uuid.uuid4()
    security = CRRSecurity(id=security_id, ticker_bbg="TEST")
    db.add(security)
    db.commit()

    request_data = {"sensitivity": 0.5}
    response = client.post(f"{settings.API_V1_STR}/crr/portfolio/{security_id}/", headers=superuser_token_headers, json=request_data)
    assert response.status_code == 200, f"Unexpected response: {response.json()}"
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "TEST"


def test_update_security_settings(client: TestClient, superuser_token_headers: dict[str, str], db: Session) -> None:
    user_id = "00000000-6666-0000-0000-000000000000"
    security_id = uuid.uuid4()
    security = CRRSecurity(id=security_id, ticker_bbg="TEST")
    db.add(security)
    db.commit()

    constituent = CRRPortfolioConstituent(user_id=user_id, security_id=security.id, sensitivity=0.5)
    db.add(constituent)
    db.commit()

    request_data = {"sensitivity": 0.7}
    response = client.put(
        f"{settings.API_V1_STR}/crr/portfolio/{security_id}/",
        headers=superuser_token_headers,
        json=request_data
    )
    assert response.status_code == 200, f"Unexpected response: {response.json()}"
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "TEST"
    assert data[0]["sensitivity"] == 0.7


def test_remove_security_from_portfolio(client: TestClient, superuser_token_headers: dict[str, str], db: Session) -> None:
    user_id = "00000000-6666-0000-0000-000000000000"
    security_id = uuid.uuid4()
    security = CRRSecurity(id=security_id, ticker_bbg="TEST")
    db.add(security)
    db.commit()

    constituent = CRRPortfolioConstituent(user_id=user_id, security_id=security_id, sensitivity=0.5)
    db.add(constituent)
    db.commit()

    response = client.delete(
        f"{settings.API_V1_STR}/crr/portfolio/{constituent.id}/",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200, f"Unexpected response: {response.json()}"
    data = response.json()
    assert all(entry["id"] != str(constituent.id) for entry in data)


def test_calculate_spread_analysis(client: TestClient, superuser_token_headers: dict[str, str], db: Session) -> None:
    security_id = str(uuid.uuid4())  # Ensure UUID is formatted as a string
    security = CRRSecurity(id=security_id, ticker_bbg="TEST")
    db.add(security)
    db.commit()

    # Add enough historical data points for the rolling window calculation
    for i in range(30):  # Ensure at least `days` worth of data
        cds_price = CDSPrice(
            id=uuid.uuid4(),
            security_id=security_id,
            entry_date=datetime.datetime.utcnow() - datetime.timedelta(days=i),
            price=100.0 + i
        )
        crr_price = CRRPrice(
            id=uuid.uuid4(),
            security_id=security_id,
            entry_date=datetime.datetime.utcnow() - datetime.timedelta(days=i),
            price=90.0 + i
        )
        db.add_all([cds_price, crr_price])
    db.commit()

    # Include required query parameters
    response = client.get(
        f"{settings.API_V1_STR}/crr/spread/{security_id}/",
        headers=superuser_token_headers,
        params={"days": 5, "deviation": 2},
    )
    assert response.status_code == 200, f"Unexpected response: {response.json()}"
    data = response.json()
    assert "regions" in data
    assert "deviation" in data


def test_get_security_data(client: TestClient, superuser_token_headers: dict[str, str], db: Session) -> None:
    security_id = uuid.uuid4()
    security = CRRSecurity(id=security_id, ticker_bbg="TEST")
    db.add(security)
    db.commit()
    # Add test data for CRRPrice and CDSPrice
    for i in range(5):
        crr_price = CRRPrice(
            id=uuid.uuid4(),  # Unique IDs for rows
            security_id=security_id,
            entry_date=datetime.datetime.utcnow() - datetime.timedelta(days=i),  # Use entry_date
            price=90.0 + i,
        )
        cds_price = CDSPrice(
            id=uuid.uuid4(),  # Unique IDs for rows
            security_id=security_id,
            entry_date=datetime.datetime.utcnow() - datetime.timedelta(days=i),  # Use entry_date
            price=100.0 + i,
        )
        db.add_all([crr_price, cds_price])
    db.commit()

    response = client.get(
        f"{settings.API_V1_STR}/crr/security/{security_id}/",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "crr" in data
    assert "cds" in data
    assert len(data["crr"]) == len(data["cds"])


def test_search_securities(client: TestClient, superuser_token_headers: dict[str, str], db: Session) -> None:
    # Create and add a test security to the database
    security_id = uuid.uuid4()
    security = CRRSecurity(id=security_id, ticker_bbg="TEST123")
    db.add(security)
    db.commit()

    # Perform the GET request to search for the security
    response = client.get(
        f"{settings.API_V1_STR}/crr/search-securities/",
        headers=superuser_token_headers,
        params={"ticker": "TEST"},
    )

    # Validate the response
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["ticker_bbg"] == "TEST123"



def test_get_merton_data(client: TestClient, superuser_token_headers: dict[str, str], db: Session) -> None:
    security_id = uuid.uuid4()

    # Ensure the security is created before adding related data
    security = CRRSecurity(id=security_id, ticker_bbg="TEST")
    db.add(security)
    db.commit()  # Commit to ensure the security exists in the database

    # Add test data for CRRMerton
    for i in range(5):
        merton_entry = CRRMerton(
            id=uuid.uuid4(),  # Use a unique ID for each entry
            security_id=security_id,  # Link to the created security
            cds_period=1,
            entry_date=datetime.datetime.utcnow() - datetime.timedelta(days=i),
            cds_delta=0.1 * i,
            ps=0.95 - 0.01 * i,
        )
        db.add(merton_entry)

    # Add test data for CDSPrice
    for i in range(5):
        price_entry = CDSPrice(
            id=uuid.uuid4(),
            security_id=security_id,  # Link to the created security
            entry_date=datetime.datetime.utcnow() - datetime.timedelta(days=i),
            price=100.0 + i,
        )
        db.add(price_entry)

    db.commit()  # Commit to save all data

    # Send the request to the endpoint
    response = client.get(
        f"{settings.API_V1_STR}/crr/merton-data/",
        headers=superuser_token_headers,
        params={"id": str(security_id), "period": 1},  # Ensure ID is a string for the request
    )

    # Verify the response
    assert response.status_code == 200
    data = response.json()
    assert "price" in data
    assert "cds_delta" in data
    assert "probability_of_survival" in data
    assert len(data["price"]) == len(data["cds_delta"])

