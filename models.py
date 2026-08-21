from datetime import date as Date
from typing import List

from pydantic import BaseModel


class Picture(BaseModel):
    price: float
    task: str
    picture_content: str


class Nest(BaseModel):
    date: Date
    pictures: List[Picture]
    total_price: float
