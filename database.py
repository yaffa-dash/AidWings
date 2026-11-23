
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Text,
    inspect,
    text
)
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine(
    "sqlite:///aidwings.db",
    connect_args={"check_same_thread": False}
)

Base = declarative_base()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String, primary_key=True)
    location = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String, default="Other")
    image_path = Column(String)
    timestamp = Column(String)
    review_status = Column(String)


# Create the table if it does not exist
Base.metadata.create_all(bind=engine)


# Add missing columns to an existing database
inspector = inspect(engine)

columns = [
    column["name"]
    for column in inspector.get_columns("assessments")
]

if "category" not in columns:
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE assessments "
                "ADD COLUMN category VARCHAR DEFAULT 'Other'"
            )
        )

    print("AidWings database updated: category column added.")
