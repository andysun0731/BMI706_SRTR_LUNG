from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import map, survival, utilization

app = FastAPI(
    title="BMI706 Lung Transplant API",
    description="API for lung transplant data visualization",
    version="1.0.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(map.router, prefix="/api/map", tags=["Map"])
app.include_router(survival.router, prefix="/api/survival", tags=["Survival"])
app.include_router(utilization.router, prefix="/api/utilization", tags=["Utilization"])

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "BMI706 Lung Transplant API is running"}
