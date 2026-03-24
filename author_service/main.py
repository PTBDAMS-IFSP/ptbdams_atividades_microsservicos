from fastapi import FastAPI, HTTPException
import asyncio

app = FastAPI()

autores_db = {
    1: {"nome": "Machado de Assis", "pais": "Brasil", "estilo": "Realismo"},
    2: {"nome": "Clarice Lispector", "pais": "Brasil", "estilo": "Introspectivo"},
    3: {"nome": "Virginia Woolf", "pais": "Reino Unido", "estilo": "Modernismo"}
}

@app.get("/author/{id}")
async def get_author(id: int, delay: int = 0):
    if delay > 0:
        await asyncio.sleep(delay)

    if id not in autores_db:
        raise HTTPException(status_code=404, detail="Autor não encontrado na nossa biblioteca, diva!")
    return autores_db[id]