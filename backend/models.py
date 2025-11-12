from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserModel(BaseModel):
    name: str
    email: EmailStr
    password: str
    is_admin: bool = False
    balance: float = 0
    gb_processed: float = 0

class TaskModel(BaseModel):
    id: int
    title: str
    gb_size: float
    assigned_to: Optional[str] = None
    status: str = "pending"
    reward_per_gb: float = 1.0

class WithdrawalModel(BaseModel):
    id: int
    user_email: str
    amount: float
    method: str
    details: str
    status: str = "pending"
    requested_at: datetime = datetime.utcnow()
