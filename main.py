from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import routers

app = FastAPI(
    title="GK Package APIs",
    description="APIs for General Knowledge package questions and assessments",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routers.questions_router)
app.include_router(routers.assessments_router)
app.include_router(routers.categories_router)
app.include_router(routers.profiles_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the GK Package APIs"}

#------------------------------uvicorn app.main:app --reload --port 8000---------------------#