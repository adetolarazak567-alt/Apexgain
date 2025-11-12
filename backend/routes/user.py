from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from passlib.hash import bcrypt
from auth import create_token, decode_token
from models import UserModel, TaskModel, WithdrawalModel
from datetime import datetime
from main import manager

router = APIRouter()

# --- In-memory storage ---
users = {}
tasks = []
withdrawals = []
withdrawal_counter = 1
task_counter = 1

# --- User signup/login ---
class SignupSchema(BaseModel):
    name: str
    email: str
    password: str

@router.post("/signup")
async def signup(data: SignupSchema):
    if data.email in users:
        raise HTTPException(status_code=400, detail="User exists")
    hashed = bcrypt.hash(data.password)
    users[data.email] = {"name": data.name, "email": data.email, "password": hashed, "is_admin": False, "balance":0, "gb_processed":0}
    token = create_token({"email": data.email, "is_admin": False})
    return {"token": token}

class LoginSchema(BaseModel):
    email: str
    password: str

@router.post("/login")
async def login(data: LoginSchema):
    user = users.get(data.email)
    if not user or not bcrypt.verify(data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_token({"email": user["email"], "is_admin": user["is_admin"]})
    return {"token": token}

# --- Dashboard ---
@router.get("/dashboard")
async def dashboard(token: str):
    payload = decode_token(token)
    user = users.get(payload["email"])
    return {"balance": user["balance"], "gb_processed": user["gb_processed"]}

# --- Tasks ---
class TaskRequestSchema(BaseModel):
    title: str
    gb_size: float
    reward_per_gb: float = 1.0

@router.post("/task/create")
async def create_task(token: str, data: TaskRequestSchema):
    global task_counter
    payload = decode_token(token)
    if not payload.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    task = {"id": task_counter, "title": data.title, "gb_size": data.gb_size, "assigned_to": None, "status":"pending", "reward_per_gb": data.reward_per_gb}
    tasks.append(task)
    task_counter +=1
    return task

@router.get("/task")
async def get_task(token: str):
    payload = decode_token(token)
    for task in tasks:
        if task["assigned_to"] is None:
            task["assigned_to"] = payload["email"]
            return task
    return {"message":"No tasks available"}

@router.post("/task/complete")
async def complete_task(token: str, task_id: int = Body(...)):
    payload = decode_token(token)
    user = users.get(payload["email"])
    for task in tasks:
        if task["id"] == task_id and task["assigned_to"] == payload["email"]:
            task["status"] = "completed"
            reward = task["gb_size"] * task["reward_per_gb"]
            user["balance"] += reward
            user["gb_processed"] += task["gb_size"]
            await manager.broadcast({
                "type": "task_completed",
                "task": task,
                "user_email": user["email"],
                "balance": user["balance"],
                "gb_processed": user["gb_processed"]
            })
            return {"message": f"Task completed, earned ${reward}"}
    raise HTTPException(status_code=400, detail="Task not found or not assigned")

# --- Withdrawals ---
class WithdrawalRequestSchema(BaseModel):
    amount: float
    method: str
    details: str

@router.post("/withdraw")
async def request_withdrawal(token: str, data: WithdrawalRequestSchema):
    global withdrawal_counter
    payload = decode_token(token)
    user = users.get(payload["email"])
    if data.amount < 10:
        raise HTTPException(status_code=400, detail="Minimum withdrawal is $10")
    if data.amount > user["balance"]:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    withdrawal = {"id": withdrawal_counter, "user_email": user["email"], "amount": data.amount,
                  "method": data.method, "details": data.details, "status":"pending", "requested_at": datetime.utcnow()}
    withdrawals.append(withdrawal)
    withdrawal_counter += 1
    user["balance"] -= data.amount
    await manager.broadcast({
        "type": "withdrawal_requested",
        "withdrawal": withdrawal
    })
    return {"message": f"Withdrawal request for ${data.amount} submitted"}
