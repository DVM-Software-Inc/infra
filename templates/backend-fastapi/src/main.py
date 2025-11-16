from fastapi import FastAPI

app = FastAPI(title="FastAPI Template")

@app.get("/health/")
async def health():
    return {"status": "ok"}
