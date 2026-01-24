from fastapi import FastAPI

app = FastAPI()


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/recommend")
def recommend(user_id: int, k: int = 20) -> dict:
    return {"user_id": user_id, "k": k, "items": []}
