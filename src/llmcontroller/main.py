from fastapi import FastAPI

from llmcontroller.api import admin, routes

app = FastAPI(title="LLMController", version="0.1.0")
app.include_router(admin.router)
app.include_router(routes.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}
