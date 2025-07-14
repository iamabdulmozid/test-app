from fastapi import FastAPI
from routers import shopify
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Order Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # or ["*"] for all origins (not recommended in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(shopify.router, prefix="/shopify", tags=["Shopify"])
# app.include_router(etsy.router, prefix="/etsy", tags=["Etsy"])
# app.include_router(google_drive.router, prefix="/drive", tags=["Drive"])
# app.include_router(gmail.router, prefix="/gmail", tags=["Gmail"])

@app.get("/")
def root():
    return {"message": "Welcome to the Order Manager API"}