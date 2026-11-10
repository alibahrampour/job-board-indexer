"""Seed a few public Greenhouse boards. Idempotent.

    docker compose exec api python -m scripts.seed_sources

Board tokens come from public career-page URLs (boards.greenhouse.io/<token>).
If a token returns 404 the run is recorded as FAILED with a permanent error -
replace it with a board you have verified.
"""
from sqlalchemy import select

from app.connectors.greenhouse import GreenhouseConnector
from app.database import SessionLocal
from app.models import Source

BOARDS = ["airbnb", "stripe", "gitlab", "cloudflare", "datadog"]


def main() -> None:
    with SessionLocal() as db:
        for token in BOARDS:
            name = f"greenhouse:{token}"
            if db.scalar(select(Source).where(Source.name == name)):
                print(f"skip   {name}")
                continue
            config = {"board_token": token}
            db.add(Source(
                name=name, platform_type=GreenhouseConnector.platform_type,
                connector=GreenhouseConnector.key, connector_type=GreenhouseConnector.connector_type,
                base_url=GreenhouseConnector.build_base_url(config), config=config,
            ))
            print(f"added  {name}")
        db.commit()


if __name__ == "__main__":
    main()
