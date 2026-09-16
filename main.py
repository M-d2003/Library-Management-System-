from fastapi import FastAPI, HTTPException
from datetime import date
from sqlalchemy import select, insert, update
from database import engine, books, transactions
import schema
 
 # Allow CORS for Streamlit
from fastapi.middleware.cors import CORSMiddleware
 
app = FastAPI(title="Library Management System (SQLAlchemy Core)")
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# ================================================================
#   CREATE BOOK
# ================================================================
@app.post("/books/", response_model=schema.Book)
def create_book(book: schema.BookCreate):
    query = insert(books).values(
        title=book.title,
        author=book.author,
        quantity=book.quantity,
        available=book.quantity
    )
 
    with engine.connect() as conn:
        result = conn.execute(query)
        conn.commit()
        book_id = result.inserted_primary_key[0]
 
        row = conn.execute(select(books).where(books.c.id == book_id)).mappings().fetchone()
 
    return schema.Book(**row)
 
# ================================================================
#   LIST ALL BOOKS
# ================================================================
@app.get("/books/", response_model=list[schema.Book])
def list_books():
    with engine.connect() as conn:
        rows = conn.execute(select(books)).mappings().all()
    return [schema.Book(**row) for row in rows]
 
# ================================================================
#   GET BOOK BY ID
# ================================================================
@app.get("/books/{book_id}", response_model=schema.Book)
def get_book(book_id: int):
    with engine.connect() as conn:
        row = conn.execute(select(books).where(books.c.id == book_id)).mappings().fetchone()
 
    if not row:
        raise HTTPException(status_code=404, detail="Book not found")
 
    return schema.Book(**row)
 
# ================================================================
#   ISSUE BOOK
# ================================================================
@app.post("/issue/")
def issue_book(book_id: int, user: str):
    with engine.connect() as conn:
        row = conn.execute(select(books).where(books.c.id == book_id)).mappings().fetchone()
 
        if not row:
            raise HTTPException(status_code=404, detail="Book not found")
 
        if row["available"] <= 0:
            raise HTTPException(status_code=400, detail="Book not available")
 
        conn.execute(
            update(books)
            .where(books.c.id == book_id)
            .values(available=row["available"] - 1)
        )
 
        conn.execute(
            insert(transactions).values(
                book_id=book_id,
                user=user,
                action="ISSUE",
                date=date.today()
            )
        )
 
        conn.commit()
 
    return {"message": "Book issued successfully"}
 
# ================================================================
#   RETURN BOOK
# ================================================================
@app.post("/return/")
def return_book(book_id: int, user: str, return_date: str = None):
 
    with engine.connect() as conn:
        # Check if book exists
        row = conn.execute(select(books).where(books.c.id == book_id)).mappings().fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Book not found")
 
        # Fetch issue and return transactions
        issued_tx = conn.execute(
            select(transactions)
            .where(transactions.c.book_id == book_id)
            .where(transactions.c.user == user)
            .where(transactions.c.action == "ISSUE")
        ).mappings().all()
 
        returned_tx = conn.execute(
            select(transactions)
            .where(transactions.c.book_id == book_id)
            .where(transactions.c.user == user)
            .where(transactions.c.action == "RETURN")
        ).mappings().all()
 
        # Identify active issue
        active_issues = []
        for issue in issued_tx:
            matched_return = [r for r in returned_tx if r["date"] >= issue["date"]]
            if not matched_return:
                active_issues.append(issue)
 
        if not active_issues:
            raise HTTPException(status_code=400, detail="No active issue for this book/user")
 
        issue_date = min(issue["date"] for issue in active_issues)
 
        # Determine actual return date
        if return_date:
            actual_return_date = date.fromisoformat(return_date)
        else:
            actual_return_date = date.today()
 
        if actual_return_date < issue_date:
            raise HTTPException(status_code=400, detail="Return date cannot be before issue date")
 
        # Update book availability
        conn.execute(
            update(books)
            .where(books.c.id == book_id)
            .values(available=row["available"] + 1)
        )
 
        # Log return
        conn.execute(
            insert(transactions).values(
                book_id=book_id,
                user=user,
                action="RETURN",
                date=actual_return_date
            )
        )
        conn.commit()
 
    return {"message": f"Book returned successfully on {actual_return_date}"}
 
# ================================================================
#   GET TRANSACTIONS
# ================================================================
@app.get("/transactions/", response_model=list[schema.Transaction])
def get_transactions():
    with engine.connect() as conn:
        rows = conn.execute(select(transactions)).mappings().all()
    return [schema.Transaction(**row) for row in rows]
 
# ================================================================
#   GET VALID RETURN DATES
# ================================================================
@app.get("/return_dates/")
def get_return_dates(book_id: int, user: str):
 
    with engine.connect() as conn:
        issued_tx = conn.execute(
            select(transactions)
            .where(transactions.c.book_id == book_id)
            .where(transactions.c.user == user)
            .where(transactions.c.action == "ISSUE")
        ).mappings().all()
 
        returned_tx = conn.execute(
            select(transactions)
            .where(transactions.c.book_id == book_id)
            .where(transactions.c.user == user)
            .where(transactions.c.action == "RETURN")
        ).mappings().all()
 
    active_issues = []
    for issue in issued_tx:
        matched_return = [r for r in returned_tx if r["date"] >= issue["date"]]
        if not matched_return:
            active_issues.append(issue)
 
    if not active_issues:
        return {"message": "No active issues for this user/book", "earliest_issue_date": None}
 
    earliest_issue_date = min(issue["date"] for issue in active_issues)
    return {"earliest_issue_date": earliest_issue_date}