from api.server import app  # re-use your FastAPI instance

# Expose for Hugging Face
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
