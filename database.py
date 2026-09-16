from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Date

DATABASE_URL = "sqlite:///./library.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
metadata = MetaData()

books = Table(
    "books",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String, nullable=False),
    Column("author", String, nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("available", Integer, nullable=False),
)

transactions = Table(
    "transactions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("book_id", Integer, nullable=False),
    Column("user", String, nullable=False),
    Column("action", String, nullable=False),  # ISSUE / RETURN
    Column("date", Date, nullable=False),
)

# Create all tables
metadata.create_all(engine)
