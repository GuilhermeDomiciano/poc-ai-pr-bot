from fastapi import FastAPI


app = FastAPI(title="POC AI PR Bot API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
