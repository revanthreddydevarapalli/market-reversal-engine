from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from src.database.session import build_engine


def test_build_engine_sqlite_roundtrip():
    engine = build_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)

    with Session() as session:
        result = session.execute(text("SELECT 1")).scalar_one()

    assert result == 1
