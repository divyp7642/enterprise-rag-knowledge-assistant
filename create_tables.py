
from sqlalchemy import text

from app.db.database import Base, engine
from app.models import Document, DocumentChunk


def create_tables():
    with engine.connect() as connection:
        database = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

        extension = connection.execute(
            text(
                "SELECT extname FROM pg_extension "
                "WHERE extname = 'vector'"
            )
        ).scalar_one_or_none()

    if database != "enterprise_rag_db":
        raise RuntimeError(
            f"Unexpected database: {database}"
        )

    if extension != "vector":
        raise RuntimeError(
            "pgvector extension is not enabled"
        )

    Base.metadata.create_all(bind=engine)

    print("Database:", database)
    print("Tables created successfully!")


if __name__ == "__main__":
    create_tables()
