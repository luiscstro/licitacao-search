@echo off
REM ============================================================
REM  Executa o buscador de licitacoes usando o Python do venv.
REM  Usado pelo Agendador de Tarefas do Windows para rodar sozinho
REM  todo dia, sem precisar abrir o terminal manualmente.
REM ============================================================

cd /d "%~dp0"

REM Ajuste esse caminho se o venv estiver em outro lugar
"%~dp0venv\Scripts\python.exe" "%~dp0buscar_licitacoes_pncp.py" >> "%~dp0log_execucoes.txt" 2>&1

echo Execucao concluida em %date% %time% >> "%~dp0log_execucoes.txt"