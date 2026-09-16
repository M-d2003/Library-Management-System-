from pydantic import BaseModel
from datetime import date

class BookCreate(BaseModel):
    title: str
    author: str
    quantity: int

class Book(BaseModel):
    id: int
    title: str
    author: str
    quantity: int
    available: int

    class Config:
        orm_mode = True

class Transaction(BaseModel):
    id: int
    book_id: int
    user: str
    action: str
    date: date
