from datetime import date as Date
from typing import List
from pydantic import BaseModel


class PictureGC(BaseModel):
    price: float
    task: str
    picture_content: str
    twin_content: str


class Nest(BaseModel):
    email : str
    pictures: List[PictureGC]
    total_price: float
