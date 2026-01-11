from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime, date
from uuid import uuid4


class Participant(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Nazwa uczestnika nie może być pusta')
        return v.strip()


class Expense(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    amount_minor: int
    date: date
    payer_id: str
    beneficiary_ids: List[str]
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Tytuł wydatku nie może być pusty')
        return v.strip()
    
    @field_validator('amount_minor')
    @classmethod
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError('Kwota musi być większa od 0')
        return v
    
    @field_validator('beneficiary_ids')
    @classmethod
    def at_least_one_beneficiary(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Co najmniej jeden beneficjent jest wymagany')
        return v


class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    created_at: datetime = Field(default_factory=datetime.now)
    read_only: bool = False
    participants: List[Participant] = Field(default_factory=list)
    expenses: List[Expense] = Field(default_factory=list)
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Nazwa sesji nie może być pusta')
        return v.strip()


class Balance(BaseModel):
    participant_id: str
    participant_name: str
    balance_minor: int


class Payment(BaseModel):
    from_participant_id: str
    from_participant_name: str
    to_participant_id: str
    to_participant_name: str
    amount_minor: int


class Settlement(BaseModel):
    balances: List[Balance]
    payments: List[Payment]
