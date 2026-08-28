import io
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURAÇÃO DE LOGS ---
log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "automacao.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8", mode="a"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# --- INSTÂNCIA FASTAPI ---
app = FastAPI(
    title="Ponto Tecnologia - Painel de Automação",
    description="API para automação de equipamentos com detecção automática do modelo.",
    version="3.1.0",
)

executor = ThreadPoolExecutor(max_workers=10)


class AutomationRequest(BaseModel):
    ips: List[str]
    image_name: Optional[str] = "WIN_20260811_14_48_02_Pro.jpg"


# --- CONFIGURAÇÃO DO CHROME PARA SERVIDORES (HEADLESS) ---
def get_chrome_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver


# --- FUNÇÃO DE AUTODETECÇÃO DO EQUIPAMENTO ---
def identificar_equipamento(driver, url: str) -> str:
    try:
        driver.get(url)
        time.sleep(2)
        page_source = driver.page_source.lower()
        title = driver.title.lower()

        if "control id" in page_source or "controlid" in page_source or "idsecure" in page_source:
            logger.info(f"🔍 [{url}] Equipamento identificado: Control iD")
            return "control_id"

        if "elite" in page_source or "elite 40" in page_source or "elite40" in title:
            logger.info(f"🔍 [{url}] Equipamento identificado: Elite 40")
            return "elite40"

        if "definir novas credenciais" in page_source or "configurações faciais" in page_source or "modo ponto" in page_source:
            logger.info(f"🔍 [{url}] Equipamento identificado: Facial / Modo Ponto")
            return "foto_modo_ponto"

        logger.warning(f"⚠️ [{url}] Não foi possível identificar com precisão. Assumindo fluxo Control iD.")
        return "control_id"

    except Exception as e:
        logger.error(f"❌ Erro ao identificar equipamento em {url}: {e}")
        return "desconhecido"


# --- AUXILIARES ---
def preencher_campo_mascarado(driver, elemento, valor):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
        time.sleep(0.2)
        driver.execute_script("""
            var elem = arguments[0];
            var val = arguments[1];
            elem.focus();
            elem.value = val;
            if (typeof $ !== 'undefined') {
                $(elem).val(val).trigger('input').trigger('change').trigger('keyup').trigger('blur');
            }
        """, elemento, valor)
        time.sleep(0.3)
        if not elemento.get_attribute("value").strip():
            elemento.click()
            elemento.send_keys(Keys.CONTROL + "a")
            elemento.send_keys(Keys.BACKSPACE)
            for char in valor:
                elemento.send_keys(char)
                time.sleep(0.03)
            elemento.send_keys(Keys.TAB)
            time.sleep(0.2)
    except Exception as e:
        logger.warning(f"Erro em campo mascarado: {e}")


def preencher_campo_texto(driver, elemento, texto):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
        elemento.click()
        elemento.send_keys(Keys.CONTROL + "a")
        elemento.send_keys(Keys.BACKSPACE)
        elemento.send_keys(texto)
        time.sleep(0.2)
    except Exception as e:
        logger.warning(f"Erro em campo texto: {e}")


# --- FLUXOS DE AUTOMAÇÃO ---
def executar_fluxo_control_id(driver, ip: str):
    url_base = ip if ip.startswith(("http://", "https://")) else f"http://{ip}"
    CPF_USUARIO = "15366117941"
    MATRICULA_USUARIO = "9999"
    wait = WebDriverWait(driver, 15)
    driver.get(url_base)
    time.sleep(1.5)
    user_input = wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Digite o usuário' or @type='text']")))
    pass_input = wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Digite a senha' or @type='password']")))
    if not user_input.get_attribute("value").strip():
        preencher_campo_texto(driver, user_input, "admin")
        preencher_campo_texto(driver, pass_input, "admin")
    btn_entrar = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Entrar')] | //a[contains(., 'Entrar')] | //input[@value='Entrar']")))
    driver.execute_script("arguments[0].click();", btn_entrar)
    time.sleep(2.5)
    menu_emp = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Empregador')] | //span[contains(., 'Empregador')]")))
    driver.execute_script("arguments[0].click();", menu_emp)
    time.sleep(2.5)
    try:
        inp_cnpj = driver.find_element(By.XPATH, "//label[contains(., 'CNPJ')]/following::input[1]")
        preencher_campo_mascarado(driver, inp_cnpj, "11222333000181")
        inp_cei = driver.find_element(By.XPATH, "//label[contains(., 'CEI') or contains(., 'CNO')]/following::input[1]")
        preencher_campo_mascarado(driver, inp_cei, "000000000000")
        inp_cpf_resp = driver.find_element(By.XPATH, "//label[contains(., 'CPF')]/following::input[1]")
        preencher_campo_mascarado(driver, inp_cpf_resp, CPF_USUARIO)
    except Exception:
        pass
    try:
        input_razao = driver.find_element(By.XPATH, "//label[contains(., 'Razão Social')]/following::input[1]")
        preencher_campo_texto(driver, input_razao, "teste loja")
    except Exception:
        pass
    try:
        input_end = driver.find_element(By.XPATH, "//label[contains(., 'Endereço')]/following::input[1]")
        preencher_campo_texto(driver, input_end, "teste loja")
    except Exception:
        pass
    btn_salvar_emp = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@id='MasterConteudo']//*[contains(@class, 'btn-success') or contains(text(), 'Salvar')]")))
    driver.execute_script("arguments[0].click();", btn_salvar_emp)
    time.sleep(3.0)
    menu_usr = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Usuários')] | //span[contains(., 'Usuários')]")))
    driver.execute_script("arguments[0].click();", menu_usr)
    time.sleep(2.5)
    btn_add_user = wait.until(EC.presence_of_element_located((By.ID, "btnAddUser")))
    driver.execute_script("arguments[0].click();", btn_add_user)
    time.sleep(3.0)
    input_nome = wait.until(EC.presence_of_element_located((By.ID, "name")))
    preencher_campo_texto(driver, input_nome, "teste loja")
    try:
        input_cpf_user = driver.find_element(By.XPATH, "//label[contains(text(),'CPF')]/following::input[1]")
    except Exception:
        input_cpf_user = driver.find_element(By.ID, "pis")
    preencher_campo_mascarado(driver, input_cpf_user, CPF_USUARIO)
    try:
        input_matricula = driver.find_element(By.XPATH, "//label[contains(text(),'Matrícula')]/following::input[1]")
        preencher_campo_texto(driver, input_matricula, MATRICULA_USUARIO)
    except Exception:
        pass
    time.sleep(1.5)
    btn_salvar_user = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn-success') and (contains(., 'Salvar') or contains(., 'SALVAR'))] | //*[contains(@class, 'modal-footer')]//*[contains(text(), 'Salvar')]")))
    driver.execute_script("arguments[0].click();", btn_salvar_user)


def executar_fluxo_foto_modo_ponto(driver, ip: str, image_name: str):
    url = f"http://{ip}" if not ip.startswith("http") else ip
    wait = WebDriverWait(driver, 15)
    driver.get(url)
    time.sleep(3)
    try:
        if driver.find_elements(By.XPATH, "//*[contains(text(), 'Definir Novas Credenciais')]"):
            senha_nova = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Nova senha']")))
            senha_nova.click()
            senha_nova.clear()
            senha_nova.send_keys("admin")
            senha_confirma = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Confirmar senha']")))
            senha_confirma.click()
            senha_confirma.clear()
            senha_confirma.send_keys("admin")
            try:
                checkbox_termos = driver.find_element(By.XPATH, "//input[@type='checkbox']")
                if not checkbox_termos.is_selected():
                    checkbox_termos.click()
            except Exception:
                driver.find_element(By.XPATH, "//*[contains(text(), 'Eu aceito os termos legais')]").click()
            wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Salvar Credenciais')]"))).click()
            time.sleep(3)
    except Exception:
        pass
    login_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Login']")))
    login_field.click()
    login_field.clear()
    login_field.send_keys("admin")
    senha_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Senha']")))
    senha_field.click()
    senha_field.clear()
    senha_field.send_keys("admin")
    wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Entrar')]"))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Cadastros']"))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Usuários']"))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Adicionar']"))).click()
    codigo = wait.until(EC.presence_of_element_located((By.XPATH, "//label[contains(., 'Código')]/following::input[1]")))
    codigo.send_keys("999999")
    driver.find_element(By.XPATH, "//label[contains(., 'Nome')]/following::input[1]").send_keys("Teste Ponto")
    try:
        caminho_imagem = os.path.abspath(image_name)
        file_input = driver.find_element(By.XPATH, "//input[@type='file']")
        file_input.send_keys(caminho_imagem)
        time.sleep(1.5)
    except Exception as ex_upload:
        logger.warning(f"Erro no upload da foto: {ex_upload}")
    driver.find_element(By.XPATH, "//*[text()='Salvar']").click()
    time.sleep(1)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Configurações Faciais']"))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Configurações Gerais']"))).click()
    campo = wait.until(EC.presence_of_element_located((By.XPATH, "//label[contains(., 'Distância')]/following::input[1]")))
    campo.send_keys(Keys.CONTROL + "a")
    campo.send_keys(Keys.BACKSPACE)
    campo.send_keys("60")
    campo.send_keys(Keys.ENTER)
    time.sleep(1)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Acesso']"))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Modo Ponto']"))).click()
    chk_hab = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Habilitar')]/..//input")))
    if not chk_hab.is_selected():
        chk_hab.click()
    chk_tipo = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Habilitar tipos de Batida')]/..//input")))
    if not chk_tipo.is_selected():
        chk_tipo.click()
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Adicionar']"))).click()
    id_field = wait.until(EC.presence_of_element_located((By.XPATH, "//label[contains(., 'ID')]/following::input[1]")))
    id_field.send_keys(Keys.CONTROL + "a")
    id_field.send_keys(Keys.BACKSPACE)
    id_field.send_keys("1")
    driver.find_element(By.XPATH, "//label[contains(., 'Nome')]/following::input[1]").send_keys("Registrar")
    driver.find_element(By.XPATH, "//*[text()='Salvar']").click()
    time.sleep(2)
    driver.find_element(By.XPATH, "//*[text()='Salvar']").click()
    time.sleep(1.5)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[text()='ok' or text()='OK' or text()='Ok']"))).click()


def executar_fluxo_elite40(driver, ip: str):
    url = f"http://{ip}" if not ip.startswith(("http://", "https://")) else ip
    driver.get(url)
    wait = WebDriverWait(driver, 15)
    campo_senha = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
    campo_senha.clear()
    campo_senha.send_keys("123")
    campo_senha.send_keys(Keys.ENTER)
    time.sleep(2)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Usuários')]"))).click()
    time.sleep(1)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Novo usuário') or contains(text(), 'Novo')]"))).click()
    time.sleep(2)
    iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
    driver.switch_to.frame(iframe)
    campo_nome = wait.until(EC.presence_of_element_located((By.XPATH, "//label[contains(text(),'Nome')]/following::input[1] | //td[contains(text(),'Nome')]/following::input[1] | (//input[@type='text'])[2]")))
    campo_nome.click()
    campo_nome.clear()
    campo_nome.send_keys("teste loja")
    time.sleep(1)
    try:
        btn_excluir = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Excluir')] | //a[contains(text(), 'Excluir')] | //*[text()='Excluir']")))
        btn_excluir.click()
        time.sleep(1)
        try:
            alert = driver.switch_to.alert
            alert.accept()
            time.sleep(1)
        except Exception:
            pass
    except Exception:
        pass
    btn_adicionar = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Adicionar no dispositivo')]")))
    btn_adicionar.click()
    time.sleep(3)


# --- ORQUESTRADOR ---
def processar_ip_automatico(ip: str, image_name: str):
    url = ip if ip.startswith(("http://", "https://")) else f"http://{ip}"
    driver = None
    try:
        driver = get_chrome_driver()
        tipo_equipamento = identificar_equipamento(driver, url)
        if tipo_equipamento == "control_id":
            executar_fluxo_control_id(driver, ip)
        elif tipo_equipamento == "foto_modo_ponto":
            executar_fluxo_foto_modo_ponto(driver, ip, image_name)
        elif tipo_equipamento == "elite40":
            executar_fluxo_elite40(driver, ip)
        logger.info(f"✅ [{ip}] Automação concluída!")
    except Exception as e:
        logger.error(f"❌ Erro durante automação do IP {ip}: {e}")
    finally:
        if driver:
            driver.quit()


# --- INTERFACE VISUAL PREMIUM COM DIGITAL EXATA ---
@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ponto Tecnologia - Painel de Automação</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&family=Inter:wght@300;400;600&display=swap');

            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: 'Inter', sans-serif;
                background-color: #030712;
                background-image: 
                    radial-gradient(circle at 15% 20%, rgba(15, 23, 42, 0.9) 0%, transparent 40%),
                    radial-gradient(circle at 85% 80%, rgba(2, 6, 23, 0.9) 0%, transparent 40%);
                color: #f3f4f6;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }

            .container {
                background: rgba(15, 23, 42, 0.75);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 20px;
                padding: 40px;
                max-width: 650px;
                width: 100%;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6), 0 0 50px rgba(56, 189, 248, 0.05);
                text-align: center;
            }

            .logo-wrapper {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 15px;
                margin-bottom: 25px;
            }

            .logo-icon {
                width: 60px;
                height: 60px;
                border: 2px solid #38bdf8;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 0 20px rgba(56, 189, 248, 0.5);
                background: #000;
                overflow: hidden;
            }

            /* Insira a URL direta da imagem da sua digital ou logo aqui se desejar */
            .logo-icon img {
                width: 100%;
                height: 100%;
                object-fit: cover;
            }

            .logo-text h1 {
                font-family: 'Orbitron', sans-serif;
                font-size: 24px;
                font-weight: 700;
                color: #ffffff;
                letter-spacing: 1px;
                text-align: left;
            }

            .logo-text span {
                font-size: 11px;
                color: #94a3b8;
                letter-spacing: 4px;
                text-transform: uppercase;
                display: block;
                text-align: left;
            }

            .status-badge {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: rgba(16, 185, 129, 0.12);
                border: 1px solid rgba(16, 185, 129, 0.3);
                color: #34d399;
                padding: 6px 14px;
                border-radius: 30px;
                font-size: 13px;
                font-weight: 600;
                margin-bottom: 25px;
            }

            .status-dot {
                width: 8px;
                height: 8px;
                background-color: #34d399;
                border-radius: 50%;
                box-shadow: 0 0 8px #34d399;
            }

            .form-group {
                text-align: left;
                margin-bottom: 20px;
            }

            label {
                display: block;
                font-size: 13px;
                font-weight: 600;
                color: #cbd5e1;
                margin-bottom: 8px;
            }

            input[type="text"] {
                width: 100%;
                padding: 14px 16px;
                background: rgba(3, 7, 18, 0.6);
                border: 1px solid #334155;
                border-radius: 10px;
                color: #ffffff;
                font-size: 14px;
                outline: none;
                transition: all 0.3s ease;
            }

            input[type="text"]:focus {
                border-color: #38bdf8;
                box-shadow: 0 0 12px rgba(56, 189, 248, 0.25);
            }

            .btn-primary {
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: 600;
                font-size: 15px;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(2, 132, 199, 0.4);
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
            }

            .btn-primary:hover {
                background: linear-gradient(135deg, #0369a1 0%, #075985 100%);
                box-shadow: 0 6px 20px rgba(2, 132, 199, 0.6);
                transform: translateY(-1px);
            }

            .btn-copy {
                background: transparent;
                border: 1px solid #334155;
                color: #94a3b8;
                padding: 10px;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                margin-top: 15px;
                transition: all 0.2s ease;
            }

            .btn-copy:hover {
                background: rgba(255, 255, 255, 0.05);
                color: #ffffff;
                border-color: #64748b;
            }

            #retorno {
                margin-top: 20px;
                background: rgba(3, 7, 18, 0.8);
                border: 1px solid #1e293b;
                border-radius: 10px;
                padding: 15px;
                font-family: 'Courier New', monospace;
                font-size: 13px;
                color: #34d399;
                text-align: left;
                display: none;
                max-height: 150px;
                overflow-y: auto;
            }

            input#textoParaCopiar { display: none; }
        </style>
    </head>
    <body>

        <div class="container">
            <div class="logo-wrapper">
                <div class="logo-icon">
                    <svg viewBox="0 0 24 24" style="width: 36px; height: 36px; fill: #38bdf8;">
                        <path d="M12 2C6.48 2 2 6.48 2 12c0 2.21.72 4.26 1.93 5.93l1.5-1.3C4.44 15.24 4 13.68 4 12c0-4.41 3.59-8 8-8s8 3.59 8 8c0 1.68-.44 3.24-1.43 4.63l1.5 1.3C21.28 16.26 22 14.21 22 12c0-5.52-4.48-10-10-10zm0 4c-3.31 0-6 2.69-6 6 0 1.16.34 2.24.93 3.15l1.45-1.22C8.16 13.39 8 12.72 8 12c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .72-.16 1.39-.38 1.93l1.45 1.22c.59-.91.93-1.99.93-3.15 0-3.31-2.69-6-6-6zm0 4c-1.1 0-2 .9-2 2 0 .39.11.75.3 1.06l1.46-1.23c-.05-.2-.06-.41-.06-.63 0-.66.54-1.2 1.2-1.2s1.2.54 1.2 1.2c0 .22-.01.43-.06.63l1.46 1.23c.19-.31.3-.67.3-1.06 0-1.1-.9-2-2-2z"/>
                    </svg>
                </div>
                <div class="logo-text">
                    <h1>PONTO</h1>
                    <span>TECNOLOGIA</span>
                </div>
            </div>

            <div class="status-badge">
                <div class="status-dot"></div>
                Sistema Online e Operacional
            </div>

            <div class="form-group">
                <label for="ipsInput">Endereços IP dos Relógios de Ponto:</label>
                <input type="text" id="ipsInput" placeholder="Ex: 192.168.1.50, 192.168.1.51">
            </div>

            <button class="btn-primary" onclick="dispararAutomacao()">
                ⚡ Executar Checklist Automático
            </button>

            <div id="retorno"></div>

            <input type="text" id="textoParaCopiar" value="https://checklistpontotecnologia.onrender.com">
            <button class="btn-copy" onclick="copiarLink()">
                📋 Copiar Link de Acesso
            </button>
        </div>

        <script>
        function dispararAutomacao() {
            var ipsStr = document.getElementById("ipsInput").value;
            if(!ipsStr) {
                alert("Insira pelo menos um IP para iniciar a automação.");
                return;
            }
            var ipsArray = ipsStr.split(',').map(item => item.trim()).filter(item => item.length > 0);
            
            var retornoDiv = document.getElementById("retorno");
            retornoDiv.style.display = "block";
            retornoDiv.innerText = "⏳ Conectando aos dispositivos e analisando modelos...";

            fetch('/api/automacao/auto', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ips: ipsArray })
            })
            .then(response => response.json())
            .then(data => {
                retornoDiv.innerText = "✅ Processo Iniciado com Sucesso!\n" + JSON.stringify(data, null, 2);
            })
            .catch(error => {
                retornoDiv.innerText = "❌ Erro ao processar requisição: " + error;
            });
        }

        function copiarLink() {
            var copyText = document.getElementById("textoParaCopiar");
            copyText.select();
            document.execCommand("copy");
            alert("Link copiado para a área de transferência!");
        }
        </script>
    </body>
    </html>
    """


@app.post("/api/automacao/auto")
def api_run_autodetect(payload: AutomationRequest):
    if not payload.ips:
        raise HTTPException(status_code=400, detail="Lista de IPs vazia.")

    for ip in payload.ips:
        executor.submit(processar_ip_automatico, ip, payload.image_name)

    return {
        "status": "iniciado",
        "message": f"Autodetecção e automação disparadas para os IPs: {payload.ips}",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("checklistlojadoponto:app", host="0.0.0.0", port=8000, reload=True)
