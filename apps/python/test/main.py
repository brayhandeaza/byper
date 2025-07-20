from fastapi import FastAPI
from byper import States

app = FastAPI()


@States.watch("count")
def increment(value):
    try:
        print(f"Count: {value}")
    except Exception as e:
        print(e)


@app.get("/")
async def root():
    try:
        States.set("count", 100)
        return {"message": "Hello World"}

    except Exception as e:
        print(e)

