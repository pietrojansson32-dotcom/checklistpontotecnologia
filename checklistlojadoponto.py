import io
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
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
    title="Checklist Loja do Ponto - Autodetecção e Automação",
    description="API para automação de equipamentos com detecção automática do modelo.",
    version="2.0.0",
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
    """Acessa o IP e identifica automaticamente o tipo de dispositivo."""
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


# --- FLUXO 1: CONTROL ID ---
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


# --- FLUXO 2: FOTO & MODO PONTO ---
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


# --- FLUXO 3: ELITE 40 ---
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


# --- ORQUESTRADOR COM AUTODETECÇÃO ---
def processar_ip_automatico(ip: str, image_name: str):
    url = ip if ip.startswith(("http://", "https://")) else f"http://{ip}"
    driver = None
    try:
        driver = get_chrome_driver()
        tipo_equipamento = identificar_equipamento(driver, url)

        if tipo_equipamento == "control_id":
            logger.info(f"▶️ Executando Control iD para o IP {ip}")
            executar_fluxo_control_id(driver, ip)
        elif tipo_equipamento == "foto_modo_ponto":
            logger.info(f"▶️ Executando Foto/Modo Ponto para o IP {ip}")
            executar_fluxo_foto_modo_ponto(driver, ip, image_name)
        elif tipo_equipamento == "elite40":
            logger.info(f"▶️ Executando Elite 40 para o IP {ip}")
            executar_fluxo_elite40(driver, ip)

        logger.info(f"✅ [{ip}] Automação concluída!")
    except Exception as e:
        logger.error(f"❌ Erro durante automação do IP {ip}: {e}")
    finally:
        if driver:
            driver.quit()


# --- ENDPOINTS DA API ---
@app.get("/")
def read_root():
    return {"status": "online", "message": "API Ativa e Pronta para Autodetecção"}


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
