from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services import shopify_service

router = APIRouter()

class DateRange(BaseModel):
    start_date: str  # Format: YYYY-MM-DD
    end_date: str    # Format: YYYY-MM-DD

@router.post("/sync-orders")
def sync_orders(date_range: DateRange):
    try:
        orders = shopify_service.fetch_orders(date_range.start_date, date_range.end_date)
        folder_path = shopify_service.process_orders(orders)
        return {
            "message": f"✅ Synced {len(orders)} orders.",
            "saved_to": folder_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
