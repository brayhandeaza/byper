from fastapi import FastAPI
from byper import States

app = FastAPI()


@States.watch("count")
def increment():
    try:
        print(f"Count:")
    except Exception as e:
        print(e)


@app.get("/")
async def root():
    try:
        States.set("count", 100)
        return {"message": "Hello World"}

    except Exception as e:
        print(e)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
