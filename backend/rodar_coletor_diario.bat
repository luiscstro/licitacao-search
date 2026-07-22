@echo off
REM ============================================================
REM  Executa o coletor de licitacoes do backend usando o Python
REM  do venv. Usado pelo Agendador de Tarefas do Windows para
REM  rodar sozinho todo dia, populando a base compartilhada que
REM  o Dashboard le automaticamente.
REM ============================================================

cd /d "%~dp0"

REM Ajuste os caminhos abaixo se sua pasta do venv estiver em outro lugar.
REM Esse .bat assume que esta na pasta "backend", e que o venv esta
REM um nivel acima (na raiz do projeto).

echo. >> "%~dp0log_coletor.txt"
echo ============================================================ >> "%~dp0log_coletor.txt"
echo INICIO da execucao: %date% %time% >> "%~dp0log_coletor.txt"
echo ============================================================ >> "%~dp0log_coletor.txt"

"%~dp0..\venv\Scripts\python.exe" "%~dp0collector_pncp.py" >> "%~dp0log_coletor.txt" 2>&1

if %ERRORLEVEL% EQU 0 (
    echo RESULTADO: concluido com sucesso >> "%~dp0log_coletor.txt"
) else (
    echo RESULTADO: terminou com erro ^(codigo %ERRORLEVEL%^) -- confira o log acima >> "%~dp0log_coletor.txt"
)

echo FIM da execucao: %date% %time% >> "%~dp0log_coletor.txt"