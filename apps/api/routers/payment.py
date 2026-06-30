from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import prisma
from routers.auth import get_current_user

router = APIRouter()

class CheckoutRequest(BaseModel):
    plan: str
    currency: str = "EUR"

@router.post("/checkout")
async def create_checkout_session(request: CheckoutRequest, user=Depends(get_current_user)):
    # Verify plan type
    plan_limits = {
        "starter": (100000, 29.0),
        "pro": (500000, 99.0),
        "enterprise": (5000000, 499.0),
        "free": (10000, 0.0)
    }
    
    if request.plan not in plan_limits:
        raise HTTPException(status_code=400, detail="Plan inconnu.")
        
    limit, cost = plan_limits[request.plan]
    
    # Get active organization
    membership = await prisma.membership.find_first(where={"userId": user.id})
    if not membership:
        raise HTTPException(status_code=404, detail="Organisation non trouvée.")
        
    # Upgrade Organization Plan
    await prisma.organization.update(
        where={"id": membership.orgId},
        data={
            "plan": request.plan,
            "tokenLimit": limit,
            "tokenUsed": 0 # Reset tokens on new plan checkout
        }
    )
    
    # Create simulated invoice
    await prisma.invoice.create(
        data={
            "amount": cost,
            "currency": request.currency,
            "status": "paid",
            "period": f"{new_period()}",
            "orgId": membership.orgId
        }
    )
    
    # Audit log
    await prisma.auditlog.create(
        data={
            "action": "payment.checkout",
            "details": f"Organisation mise à niveau vers le plan {request.plan} ({cost} {request.currency})",
            "userId": user.id,
            "orgId": membership.orgId
        }
    )
    
    return {
        "url": f"https://checkout.stripe.com/pay/cs_test_fake123?plan={request.plan}",
        "status": "success",
        "message": f"Votre espace de travail a été mis à niveau vers le plan {request.plan}."
    }

@router.get("/invoices")
async def get_invoices(user=Depends(get_current_user)):
    membership = await prisma.membership.find_first(where={"userId": user.id})
    if not membership:
        return []
        
    invoices = await prisma.invoice.find_many(
        where={"orgId": membership.orgId},
        order={"createdAt": "desc"}
    )
    return [
        {
            "id": inv.id,
            "amount": inv.amount,
            "currency": inv.currency,
            "status": inv.status,
            "period": inv.period,
            "createdAt": inv.createdAt.isoformat()
        }
        for inv in invoices
    ]

def new_period():
    import datetime
    now = datetime.datetime.now()
    return now.strftime("%Y-%m")
