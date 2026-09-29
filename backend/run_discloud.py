"""
Ponto de entrada pra hospedar o backend na Discloud.

A Discloud espera um app escutando em 0.0.0.0:8080, não importa o
framework (ver docs.discloud.com/how-to-host/frameworks). app/main.py só
define a instância do FastAPI (`app`), sem subir um servidor sozinho —
esse script existe só pra rodar o uvicorn com o host/porta certos.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080)
