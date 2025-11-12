from fastapi import APIRouter, HTTPException
from auth import decode_token
from routes.user import users, tasks, withdrawals

router = APIRouter()

# --- Admin auth helper ---
def admin_required(token: str):
    payload = decode_token(token)
    if not payload.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access only")
    return payload

# --- Get all users ---
@router.get("/users")
async def get_users(token: str):
    admin_required(token)
    return list(users.values())

# --- Get all tasks ---
@router.get("/tasks")
async def get_tasks(token: str):
    admin_required(token)
    return tasks

# --- Get all withdrawals ---
@router.get("/withdrawals")
async def get_withdrawals(token: str):
    admin_required(token)
    return withdrawals

# --- Approve withdrawal ---
@router.post("/withdrawals/approve")
async def approve_withdrawal(token: str, withdrawal_id: int):
    admin_required(token)
    for w in withdrawals:
        if w["id"] == withdrawal_id:
            w["status"] = "approved"
            return {"message": f"Withdrawal {withdrawal_id} approved"}
    raise HTTPException(status_code=404, detail="Withdrawal not found")
