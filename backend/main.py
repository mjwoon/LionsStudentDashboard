import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routers import students, courses, surveys, evaluation, admin, dashboard
from routers import graph, admin_upload_grouped
from services.graph_service import Neo4jConnection

app = FastAPI(
    title="Lions Student Dashboard API",
    description="한양대학교 LIONS 학생 대시보드 백엔드 API",
    version="1.0.0"
)

# CORS middleware
# CORS_ORIGINS: 쉼표로 구분된 허용 오리진 목록 (예: https://lions-frontend.onrender.com,http://localhost:5173)
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
cors_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(students.router)
app.include_router(courses.router)
app.include_router(surveys.router)
app.include_router(evaluation.router)
app.include_router(admin.router)
app.include_router(admin_upload_grouped.router)
app.include_router(dashboard.router)
app.include_router(graph.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    Neo4jConnection.close()


@app.get("/")
def read_root():
    return {
        "message": "Lions Student Dashboard API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}