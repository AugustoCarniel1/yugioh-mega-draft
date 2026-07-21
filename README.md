# Yu-Gi-Oh! Mega Draft

Aplicacao local leve para gerenciar um formato RPG/Progression de Yu-Gi-Oh! entre jogadores.

## Stack

- FastAPI para API local
- Streamlit para interface reativa
- SQLite com SQLModel
- Cache local de dados e imagens da YGOProDeck API

## Rodando

Jeito mais facil no Windows:

```powershell
.\start_local.bat
```

Isso cria a `.venv` se precisar, instala as dependencias, inicializa o banco e abre backend + frontend em janelas separadas.

Manual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/init_db.py
```

Em um terminal:

```powershell
uvicorn app.backend.main:app --reload
```

Em outro terminal:

```powershell
streamlit run app/frontend/streamlit_app.py
```

O banco fica em `data/yugioh_mega_draft.db` e as imagens em `app/static/images`.
