from fastapi import FastAPI

# 이 줄이 반드시 있어야 합니다. 
# Uvicorn은 이 'app' 변수를 찾아 실행합니다.
app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}