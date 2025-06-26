from fastapi import FastAPI


print("Hello World")

api = FastAPI()

@api.get('/')
def index():
    return {"message": "Hello World"}