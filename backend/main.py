from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from db_migrations import init_schema
from routers import students, courses, surveys, evaluation, admin, dashboard
from routers import graph, admin_upload_grouped
from services.graph_service import Neo4jConnection


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: 운영은 Alembic upgrade, 개발/테스트는 create_all (db_migrations.init_schema)
    init_schema()
    yield
    # shutdown
    Neo4jConnection.close()


app = FastAPI(
    title="Lions Student Dashboard API",
    description="한양대학교 LIONS 학생 대시보드 백엔드 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
# CORS_ORIGINS: 쉼표로 구분된 허용 오리진 목록 (예: https://lions-frontend.onrender.com,http://localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
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