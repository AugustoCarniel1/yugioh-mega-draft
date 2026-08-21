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

## Base local de cartas

Depois de atualizar o projeto, execute uma vez no Windows:

```powershell
.\sincronizar_cartas.bat
```

O processo importa todas as colecoes configuradas, as cartas e cada impressao/raridade para o banco local.
Ele pode demorar alguns minutos na primeira vez e e seguro executa-lo novamente: colecoes concluidas sao ignoradas e eventuais falhas sao retomadas.
As imagens continuam sendo baixadas somente quando uma carta aparece na interface.

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
