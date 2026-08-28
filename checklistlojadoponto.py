from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List

app = FastAPI()

class ChecklistData(BaseModel):
    tecnico: str
    loja: str
    status: str
    itens: List[str]

# Serve a página HTML com o visual azul e branco direto na raiz
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PONTO TECNOLOGIA - Checklist de Assistência</title>
        <style>
            :root {
                --primary-dark: #002244;
                --accent-blue: #007bff;
                --bg-light: #f4f6f9;
                --white: #ffffff;
                --text-main: #333333;
                --border: #e1e8ed;
            }

            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; }
            body { background-color: var(--bg-light); color: var(--text-main); display: flex; flex-direction: column; min-height: 100vh; }

            header {
                background-color: var(--primary-dark);
                color: var(--white);
                padding: 15px 30px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            }

            .logo-area { font-size: 20px; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; }
            .tech-text { font-weight: normal; font-size: 16px; opacity: 0.8; }
            
            nav a {
                color: var(--white);
                text-decoration: none;
                margin-left: 20px;
                font-size: 14px;
                opacity: 0.9;
                transition: opacity 0.2s;
            }
            nav a:hover { opacity: 1; }

            main {
                flex: 1;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 40px 20px;
            }

            .container {
                background-color: var(--white);
                width: 100%;
                max-width: 550px;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0, 34, 68, 0.08);
                border-top: 5px solid var(--accent-blue);
            }

            h2 {
                color: var(--primary-dark);
                margin-bottom: 25px;
                text-align: center;
                font-size: 24px;
            }

            .form-group { margin-bottom: 18px; }
            label { display: block; margin-bottom: 7px; font-weight: 600; color: #003366; font-size: 14px;}
            
            input[type="text"], select {
                width: 100%;
                padding: 12px 15px;
                border: 1px solid var(--border);
                border-radius: 4px;
                font-size: 15px;
                outline: none;
                transition: border-color 0.2s;
            }
            input[type="text"]:focus, select:focus { border-color: var(--accent-blue); }

            .checkbox-group {
                display: flex;
                flex-direction: column;
                gap: 12px;
                margin-top: 10px;
                background-color: #f9fbff;
                padding: 15px;
                border-radius: 4px;
                border: 1px solid #edf2f7;
            }
            .checkbox-item {
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 14px;
                color: #4a5568;
                cursor: pointer;
            }
            
            button {
                width: 100%;
                background-color: var(--accent-blue);
                color: white;
                border: none;
                padding: 15px;
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                margin-top: 20px;
                transition: background-color 0.2s, transform 0.1s;
            }
            button:hover { background-color: #0069d9; }
            button:active { transform: translateY(1px); }

            #status { margin-top: 20px; padding: 12px; border-radius: 4px; text-align: center; font-weight: bold; display: none; font-size: 14px;}
            .sucesso { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .erro { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }

            footer {
                text-align: center;
                padding: 20px;
                font-size: 12px;
                color: #888;
                border-top: 1px solid var(--border);
                background-color: #f8f9fa;
            }
        </style>
    </head>
    <body>

    <header>
        <div class="logo-area">PONTO <span class="tech-text">TECNOLOGIA</span></div>
        <nav>
            <a href="/docs">Documentação API</a>
            <a href="#">Área Técnica</a>
        </nav>
    </header>

    <main>
        <div class="container">
            <h2>Checklist de Assistência Técnica</h2>
            <form id="checklistForm">
                <div class="form-group">
                    <label for="tecnico">Nome do Técnico:</label>
                    <input type="text" id="tecnico" placeholder="Digite seu nome (ex: Pietro)" required>
                </div>

                <div class="form-group">
                    <label for="loja">Loja ou Cliente:</label>
                    <input type="text" id="loja" placeholder="Digite a loja ou cliente (ex: Loja Centro)" required>
                </div>

                <div class="form-group">
                    <label>Itens Verificados no Local:</label>
                    <div class="checkbox-group">
                        <label class="checkbox-item"><input type="checkbox" name="item" value="Biometria OK"> Leitor Biométrico</label>
                        <label class="checkbox-item"><input type="checkbox" name="item" value="Fonte OK"> Fonte de Alimentação</label>
                        <label class="checkbox-item"><input type="checkbox" name="item" value="Rede OK"> Conexão de Rede / Comunicação</label>
                        <label class="checkbox-item"><input type="checkbox" name="item" value="Impressora OK"> Módulo de Impressão (Fiscal)</label>
                        <label class="checkbox-item"><input type="checkbox" name="item" value="Display OK"> Display / Monitor Touch</label>
                    </div>
                </div>

                <div class="form-group">
                    <label for="statusSelect">Status Geral do Serviço:</label>
                    <select id="statusSelect">
                        <option value="Aprovado">✅ Aprovado (Funcionando)</option>
                        <option value="Pendente">⚠️ Pendente de Peça / Retorno</option>
                        <option value="Reprovado">❌ Reprovado (Necessário Troca)</option>
                    </select>
                </div>

                <button type="submit" id="btnEnviar">Enviar Relatório Profissional</button>
            </form>

            <div id="status"></div>
        </div>
    </main>

    <footer>
        <p>&copy; 2026 PONTO TECNOLOGIA - Todos os direitos reservados.</p>
    </footer>

    <script>
        document.getElementById('checklistForm').addEventListener('submit', async function(e) {
            e.preventDefault();

            const btn = document.getElementById('btnEnviar');
            const statusDiv = document.getElementById('status');
            
            btn.disabled = true;
            btn.innerText = "Enviando Relatório...";
            statusDiv.style.display = "none";

            const itensSelecionados = Array.from(document.querySelectorAll('input[name="item"]:checked'))
                                          .map(cb => cb.value);

            const payload = {
                tecnico: document.getElementById('tecnico').value,
                loja: document.getElementById('loja').value,
                status: document.getElementById('statusSelect').value,
                itens: itensSelecionados
            };

            try {
                const response = await fetch('/checklist', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (response.ok) {
                    statusDiv.className = "sucesso";
                    statusDiv.innerText = "Relatório de Checklist enviado com sucesso!";
                    statusDiv.style.display = "block";
                    document.getElementById('checklistForm').reset();
                } else {
                    throw new Error("Erro na resposta do servidor.");
                }
            } catch (error) {
                statusDiv.className = "erro";
                statusDiv.innerText = "Falha ao conectar com a API.";
                statusDiv.style.display = "block";
            } finally {
                btn.disabled = false;
                btn.innerText = "Enviar Relatório Profissional";
            }
        });
    </script>

    </body>
    </html>
    """

@app.post("/checklist")
def receber_checklist(dados: ChecklistData):
    print(f"Checklist recebido: {dados}")
    return {"status": "sucesso", "mensagem": "Relatório armazenado com sucesso!"}
