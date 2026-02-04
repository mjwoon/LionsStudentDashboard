from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routers import students, courses, surveys, evaluation, admin, dashboard
from routers import graph
from services.graph_service import Neo4jConnection

app = FastAPI(
    title="Lions Student Dashboard API",
    description="한양대학교 LIONS 학생 대시보드 백엔드 API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서 모든 오리진 허용
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