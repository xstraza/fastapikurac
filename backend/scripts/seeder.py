import os
from datetime import datetime
import pandas as pd
from app.models_mri import MRIAssetOutput
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database configuration
DATABASE_URL = "postgresql://postgres:changethis@localhost:5432/app"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Directory containing the CSV files
DATA_DIR = "/Users/xstraza/Development/RPC-Analytics/fastapikurac/backend/data/long_term"

# Function to parse the filename and extract `class` and `domain`
def parse_filename(filename):
    parts = filename.replace("_long.csv", "").split("_")
    asset_class = parts[0]
    domain = "_".join(parts[1:])
    return asset_class, domain


import uuid
from app.models_mri import MRIPortfolio, MRIPortfolioConstituent


def seed_data():
    session = SessionLocal()
    try:
        # Insert default portfolio
        default_portfolio = MRIPortfolio(
            id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            name="default portfolio",
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000000")
        )
        session.add(default_portfolio)
        session.commit()

        # Insert default portfolio constituents
        constituents = [
            {"asset_name": "commodity global", "asset_class": "commodity", "domain": "global", "weight": 0.2},
            {"asset_name": "global credit", "asset_class": "credit", "domain": "global", "weight": 0.2},
            {"asset_name": "global equities", "asset_class": "equities", "domain": "global", "weight": 0.2},
            {"asset_name": "us interest rate", "asset_class": "us-interest-rate", "domain": "global", "weight": 0.2},
            {"asset_name": "global fx", "asset_class": "fx", "domain": "global", "weight": 0.2},
        ]

        for constituent in constituents:
            portfolio_constituent = MRIPortfolioConstituent(
                portfolio_id=default_portfolio.id,
                asset_name=constituent["asset_name"],
                asset_domain=constituent["domain"],
                asset_class=constituent["asset_class"],
                weight=constituent["weight"]
            )
            session.add(portfolio_constituent)

        # Commit all changes to the database
        session.commit()

        # Existing data seeding logic
        for filename in os.listdir(DATA_DIR):
            if filename.endswith("_long.csv"):
                file_path = os.path.join(DATA_DIR, filename)
                asset_class, domain = parse_filename(filename)

                # Read the CSV file
                df = pd.read_csv(file_path)

                # Iterate over the rows and insert into the database
                for _, row in df.iterrows():
                    asset_output = MRIAssetOutput(
                        date=datetime.strptime(row["Date"], "%Y-%m-%d"),
                        domain=domain,
                        asset_class=asset_class,
                        rpr=row.iloc[1],  # Updated for safe positional access
                        lookback=row["lookback"],
                    )
                    session.add(asset_output)

        session.commit()
        print("Data seeding completed successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error during seeding: {e}")
    finally:
        session.close()

# Run the seeding function
if __name__ == "__main__":
    seed_data()
