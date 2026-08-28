from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# Permite que o Netlify acesse a API sem bloqueios de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AutomacaoPayload(BaseModel):
    ips: List[str]
    executar_passo1: bool = True
    executar_passo2: bool = True
    executar_passo3: bool = True

@app.get("/")
def home():
    return {"status": "API Checklist Loja do Ponto Ativa!"}

@app.get("/ping")
def ping(ip: str):
    # Simulação de resposta de conectividade
    return {"online": True, "tempo_ms": 15, "ip": ip}

@app.post("/api/automacao")
def iniciar_automacao(payload: AutomacaoPayload):
    resultados = []
    for ip in payload.ips:
        resultados.append({
            "ip": ip,
            "status": "sucesso",
            "equipamento": "Control iD",
            "detalhes": [
                "Conexão estabelecida com sucesso.",
                "Dispositivo identificado como Control iD.",
                "Rotinas operacionais concluídas."
            ]
        })
    return {"resultados": resultados}

@app.post("/checklist")
def salvar_checklist(dados: dict):
    return {"status": "sucesso", "mensagem": "Checklist salvo com sucesso!"}