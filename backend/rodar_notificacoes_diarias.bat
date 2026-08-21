@echo off
REM ============================================================
REM  Executa o envio do resumo diario de licitacoes por e-mail,
REM  usando o Python do venv. Agende no Agendador de Tarefas do
REM  Windows pra rodar TODO DIA, uns 30 minutos DEPOIS do
REM  rodar_coletor_diario.bat (precisa que a coleta do dia ja
REM  tenha terminado).
REM
REM  Antes de agendar, configure as variaveis de ambiente de SMTP
REM  (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM)
REM  como variaveis de ambiente do sistema/usuario no Windows -
REM  veja o README para detalhes.
REM ============================================================

cd /d "%~dp0"

echo. >> "%~dp0log_notificacoes.txt"
echo ============================================================ >> "%~dp0log_notificacoes.txt"
echo INICIO da execucao: %date% %time% >> "%~dp0log_notificacoes.txt"
echo ============================================================ >> "%~dp0log_notificacoes.txt"

"%~dp0..\venv\Scripts\python.exe" "%~dp0enviar_notificacoes_diarias.py" >> "%~dp0log_notificacoes.txt" 2>&1

if %ERRORLEVEL% EQU 0 (
    echo RESULTADO: concluido com sucesso >> "%~dp0log_notificacoes.txt"
) else (
    echo RESULTADO: terminou com erro ^(codigo %ERRORLEVEL%^) -- confira o log acima >> "%~dp0log_notificacoes.txt"
)

"%~dp0..\venv\Scripts\python.exe" "%~dp0enviar_alertas_documentos.py" >> "%~dp0log_notificacoes.txt" 2>&1

if %ERRORLEVEL% EQU 0 (
    echo RESULTADO ^(documentos^): concluido com sucesso >> "%~dp0log_notificacoes.txt"
) else (
    echo RESULTADO ^(documentos^): terminou com erro ^(codigo %ERRORLEVEL%^) -- confira o log acima >> "%~dp0log_notificacoes.txt"
)

echo FIM da execucao: %date% %time% >> "%~dp0log_notificacoes.txt"
