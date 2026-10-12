from fastapi import FastAPI

app = FastAPI(
    title="JobShield API",
    description="Recruitment Trust Intelligence Platform",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "JobShield API",
    }