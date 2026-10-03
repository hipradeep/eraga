from fastapi import FastAPI

app = FastAPI(
    title="ERAGA — Enterprise RAG Assistant",
    description="Production-grade Retrieval-Augmented Generation platform for enterprises.",
    version="0.1.0",
)
    

@app.get("/welcome")
def welcome():
    return {
        "message": "Welcome to ERAGA — Enterprise RAG Assistant 🧠",
        "version": "0.1.0",
        "status": "running",
    }
