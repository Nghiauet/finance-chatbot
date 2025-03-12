from fastapi import FastAPI
from backend.api.v1 import financial_reports

app = FastAPI()
app.include_router(financial_reports.router) 