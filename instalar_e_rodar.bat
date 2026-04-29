@echo off
echo ============================================
echo   CRM Mari Amaral - Instalacao e Execucao
echo ============================================
echo.

echo [1/3] Instalando pacotes Python...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERRO: Falha ao instalar pacotes. Verifique se o Python esta instalado.
    pause
    exit /b 1
)

echo.
echo [2/3] Fazendo login no Google (BigQuery)...
echo Uma janela do navegador vai abrir para voce fazer login com sua conta Google.
gcloud auth application-default login
if errorlevel 1 (
    echo AVISO: Login falhou. Verifique se o Google Cloud SDK esta instalado.
    echo Baixe em: https://cloud.google.com/sdk/docs/install
    pause
    exit /b 1
)

echo.
echo [3/3] Iniciando o CRM...
echo Acesse no navegador: http://localhost:8501
echo Para fechar, pressione Ctrl+C nesta janela.
echo.
streamlit run app.py
pause
