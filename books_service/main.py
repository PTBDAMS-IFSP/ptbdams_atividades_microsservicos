from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI()

livros_db = {
    101: {"titulo": "Dom Casmurro", "author_id": 1},
    102: {"titulo": "A Hora da Estrela", "author_id": 2},
    103: {"titulo": "Mrs. Dalloway", "author_id": 3}
}

@app.get("/book/{id}")
async def get_book_details(id: int, delay: int = 0):
    if id not in livros_db:
        raise HTTPException(status_code=404, detail="Livro não consta no catálogo!")

    livro = livros_db[id]

    url_autor = f"http://authors_service:8000/author/{livro['author_id']}?delay={delay}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url_autor, timeout=2.0) # 2 segundos de limite
            response.raise_for_status()
            dados_autor = response.json()
            return {
                "livro": livro["titulo"],
                "detalhes_do_autor": dados_autor,
                "status": "Ficha técnica completa com sucesso!"
            }
    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="O serviço de autores demorou demais para responder (Timeout).")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Não foi possível conectar ao serviço de autores (Falha de Comunicação).")