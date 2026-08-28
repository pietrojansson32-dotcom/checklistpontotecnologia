from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List

app = FastAPI()

class ChecklistData(BaseModel):
    tecnico: str
    loja: str
    status: str
    itens: List[str]

@app.get("/")
def home():
    return FileResponse("index.html")

@app.post("/checklist")
def receber_checklist(dados: ChecklistData):
    print(f"Checklist recebido: {dados}")
    return {"status": "sucesso", "mensagem": "Relatório armazenado com sucesso!"}
