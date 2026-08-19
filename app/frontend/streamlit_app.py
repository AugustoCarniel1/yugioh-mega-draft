import json
from html import escape

import requests
import streamlit as st
import streamlit.components.v1 as components


API_URL = "http://127.0.0.1:8000"


def api_get(path: str, **kwargs):
    response = requests.get(f"{API_URL}{path}", timeout=30, **kwargs)
    response.raise_for_status()
    return response.json()


def api_post(path: str, **kwargs):
    response = requests.post(f"{API_URL}{path}", timeout=60, **kwargs)
    response.raise_for_status()
    return response.json()


def api_delete(path: str):
    response = requests.delete(f"{API_URL}{path}", timeout=60)
    response.raise_for_status()
    return response.json()


def api_patch(path: str, **kwargs):
    response = requests.patch(f"{API_URL}{path}", timeout=60, **kwargs)
    response.raise_for_status()
    return response.json()


def error_message(exc: requests.HTTPError) -> str:
    try:
        payload = exc.response.json()
    except ValueError:
        return exc.response.text
    return payload.get("detail") or exc.response.text


def remember_player(player_id: int) -> None:
    st.session_state["active_player_id"] = player_id


def format_gold(value: float | int) -> str:
    value = float(value)
    return str(int(value)) if value.is_integer() else f"{value:.1f}"


def collection_year_from_item(collection: dict | None) -> int | None:
    if not collection or not collection.get("tcg_date"):
        return None
    try:
        return int(str(collection["tcg_date"]))
    except ValueError:
        return None


def round_gold_gain_for_collection(collection: dict | None) -> int:
    year = collection_year_from_item(collection)
    if year is None:
        return 10
    return 10 + max(year - 2002, 0)


def render_gold_metric(player_id: int, initial_gold: float) -> None:
    payload = {
        "apiUrl": API_URL,
        "playerId": player_id,
        "gold": initial_gold,
    }
    html = """
    <div id="gold-metric-root"></div>
    <style>
      * { box-sizing: border-box; }
      body { margin: 0; font-family: "Source Sans Pro", sans-serif; }
      .gold-metric {
        border-left: 1px solid rgba(49, 51, 63, 0.2);
        padding-left: 0.1rem;
      }
      .gold-label {
        color: white;
        font-size: 0.875rem;
        margin-bottom: 0.25rem;
      }
      .gold-value {
        color: white;
        font-size: 1.5rem;
        font-weight: 700;
        line-height: 1.2;
      }
    </style>
    <script>
      const data = __PAYLOAD__;
      const root = document.getElementById("gold-metric-root");
      let lastGold = Number(data.gold || 0);

      function fmtGold(v) {
        v = Number(v || 0);
        return Number.isInteger(v) ? String(v) : v.toFixed(1);
      }

      function isDirty() {
        try {
          return window.parent.localStorage.getItem("ygo_editor_dirty") === "1";
        } catch (err) {
          return false;
        }
      }

      function render() {
        root.innerHTML = `
          <div class="gold-metric">
            <div class="gold-label">Gold</div>
            <div class="gold-value">${fmtGold(lastGold)}g</div>
          </div>
        `;
      }

      async function refreshGold() {
        const response = await fetch(`${data.apiUrl}/players/${data.playerId}`);
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) return;
        lastGold = Number(payload.gold || 0);
        render();
      }

      render();
      window.setInterval(() => {
        if (isDirty()) {
          refreshGold().catch(() => {});
        }
      }, 900);
    </script>
    """.replace("__PAYLOAD__", json.dumps(payload))
    components.html(html, height=78, scrolling=False)


st.set_page_config(page_title="Yu-Gi-Oh! Mega Draft", layout="wide")
st.markdown(
    """
    <style>
    header[data-testid="stHeader"] {
        display: none !important;
    }

    div[data-testid="stToolbar"] {
        display: none !important;
    }

    section[data-testid="stSidebar"] {
        min-width: 180px !important;
        max-width: 180px !important;
    }

    section[data-testid="stSidebar"] .stHeading,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stCaption {
        font-size: 0.72rem !important;
    }

    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] .stHeading h2 {
        font-size: 0.9rem !important;
        margin-bottom: 0.2rem !important;
    }

    section[data-testid="stSidebar"] .stButton button,
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stTextInput label {
        font-size: 0.72rem !important;
    }

    section[data-testid="stSidebar"] .stButton button {
        min-height: 1.7rem !important;
        padding: 0.05rem 0.4rem !important;
        font-size: 0.72rem !important;
    }

    section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
    section[data-testid="stSidebar"] .stTextInput input {
        min-height: 2rem !important;
        font-size: 0.72rem !important;
        padding-top: 0.15rem !important;
        padding-bottom: 0.15rem !important;
    }

    section[data-testid="stSidebar"] .block-container {
        padding: 0.7rem 0.55rem 0.85rem !important;
    }

    section[data-testid="stSidebar"] .stDivider {
        margin: 0.7rem 0 !important;
    }

    section[data-testid="stSidebar"] .stExpander {
        font-size: 0.72rem !important;
    }

    .block-container {
        padding-top: 1.2rem !important;
    }

    h1 {
        font-size: 2.25rem !important;
        line-height: 1.05 !important;
        margin-bottom: 0.35rem !important;
        padding-top: 0 !important;
    }

    div[data-testid="stMetric"] {
        padding: 0 !important;
    }

    div[data-testid="stMetric"] label {
        font-size: 0.82rem !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.1rem !important;
        line-height: 1.1 !important;
    }

    div[data-testid="stMetricDelta"] {
        font-size: 0.72rem !important;
    }

    div[data-testid="stFileUploader"] {
        margin-top: 0.1rem !important;
    }

    div[data-testid="stButton"] button {
        min-height: 2.2rem;
    }

    div[data-testid="stHorizontalBlock"] {
        overflow: visible;
    }

    .card-thumb-wrap {
        position: relative;
        z-index: 1;
        overflow: visible;
        width: 100%;
    }

    .card-thumb-wrap:hover {
        z-index: 80;
    }

    .card-thumb {
        display: block;
        width: 100%;
        height: auto;
        border-radius: 4px;
        image-rendering: auto;
        transition: box-shadow 120ms ease;
    }

    .card-thumb:hover {
        box-shadow: 0 0 0 2px #38bdf8, 0 10px 26px rgba(0, 0, 0, 0.32);
    }

    .card-thumb-preview {
        background: rgba(2, 6, 23, 0.94);
        border: 1px solid rgba(147, 197, 253, 0.85);
        border-radius: 8px;
        box-shadow: 0 18px 42px rgba(0, 0, 0, 0.45);
        display: none;
        left: 50%;
        max-height: calc(100vh - 28px);
        padding: 8px;
        pointer-events: none;
        position: fixed;
        top: 14px;
        transform: translateX(-50%);
        width: min(520px, 38vw);
        z-index: 999999;
    }

    .card-thumb-preview img {
        border-radius: 5px;
        display: block;
        max-height: calc(100vh - 72px);
        object-fit: contain;
        width: 100%;
    }

    .card-thumb-preview-title {
        color: #e5e7eb;
        font-size: 12px;
        font-weight: 700;
        line-height: 1.2;
        margin-top: 6px;
    }

    .card-thumb-wrap:hover .card-thumb-preview {
        display: block;
    }

    .card-meta {
        color: #6b7280;
        font-size: 0.72rem;
        line-height: 1.15;
        margin-top: 0.15rem;
        min-height: 1.7rem;
    }

    .deck-box {
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 0.65rem;
        margin-bottom: 0.65rem;
        background: #fafafa;
    }

    .deck-box-title {
        font-weight: 700;
        margin-bottom: 0.4rem;
    }

    .deck-card-line {
        align-items: center;
        border-bottom: 1px solid #e5e7eb;
        display: flex;
        font-size: 0.82rem;
        gap: 0.35rem;
        justify-content: space-between;
        min-height: 1.55rem;
        padding: 0.12rem 0;
    }

    .deck-card-name {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .deck-section-label {
        color: #4b5563;
        font-size: 0.75rem;
        font-weight: 700;
        margin-top: 0.45rem;
        text-transform: uppercase;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Yu-Gi-Oh! Mega Draft")

with st.sidebar:
    st.header("Jogador")
    players = api_get("/players")
    player_options = {player["id"]: player for player in players}
    player_ids = [player["id"] for player in players]
    select_options = ["new"] + player_ids
    saved_player_id = st.session_state.get("active_player_id")
    if saved_player_id not in player_ids and player_ids:
        saved_player_id = player_ids[0]
        remember_player(saved_player_id)
    selected_index = select_options.index(saved_player_id) if saved_player_id in player_ids else 0
    if st.session_state.get("player_select") not in select_options:
        st.session_state["player_select"] = saved_player_id if saved_player_id in player_ids else "new"

    def player_label(option: str | int) -> str:
        if option == "new":
            return "Criar novo"
        option_player = player_options[option]
        return f"{option_player['name']} ({format_gold(option_player['gold'])}g)"

    selected_player_key = st.selectbox(
        "Perfil ativo",
        select_options,
        format_func=player_label,
        index=selected_index,
        key="player_select",
    )
    active_player = None

    if selected_player_key == "new":
        st.session_state.pop("active_player_id", None)
    else:
        active_player = player_options[selected_player_key]
        remember_player(active_player["id"])

    if selected_player_key == "new":
        with st.form("create-player"):
            name = st.text_input("Nome")
            submitted = st.form_submit_button("Criar jogador")
            if submitted and name.strip():
                try:
                    active_player = api_post("/players", json={"name": name.strip()})
                    remember_player(active_player["id"])
                    st.success("Jogador criado.")
                    st.rerun()
                except requests.HTTPError as exc:
                    st.error(error_message(exc))

    st.divider()
    if active_player:
        with st.expander("Perfil"):
            st.caption("Excluir remove o perfil, inventario e deck deste jogador.")
            confirm_delete = st.checkbox("Confirmar exclusao", key=f"confirm-delete-{active_player['id']}")
            if st.button("Excluir perfil", disabled=not confirm_delete, key=f"delete-player-{active_player['id']}"):
                try:
                    api_delete(f"/players/{active_player['id']}")
                    st.session_state.pop("active_player_id", None)
                    st.success("Perfil excluido.")
                    st.rerun()
                except requests.HTTPError as exc:
                    st.error(error_message(exc))

    st.divider()
    if st.button("Sincronizar colecoes da API"):
        try:
            result = api_post("/collections/sync")
            st.success(f"{result['synced']} colecoes sincronizadas.")
        except requests.HTTPError as exc:
            st.error(error_message(exc))


if not active_player:
    st.info("Crie ou selecione um jogador para comecar.")
    st.stop()

player = api_get(f"/players/{active_player['id']}")
saved_decks = api_get(f"/players/{player['id']}/decks")
collections = api_get("/collections")
current_collection = next(
    (item for item in collections if item["position"] == player["current_collection_index"]),
    None,
)
current_year = collection_year_from_item(current_collection)
current_round_gold_gain = round_gold_gain_for_collection(current_collection)
round_label = "Inicial" if player["current_collection_index"] < 0 else player["current_collection_index"] + 1
collection_label = current_collection["set_name"] if current_collection else "Sem colecao"

try:
    inventory = api_get(f"/players/{player['id']}/inventory")
except requests.HTTPError as exc:
    st.error(f"Erro ao carregar inventario: {error_message(exc)}")
    st.stop()
starter_imported = any(card.get("source") == "starter_deck" for card in inventory)

try:
    year_pick = api_get(f"/players/{player['id']}/year-pick")
except requests.HTTPError as exc:
    st.error(f"Erro ao carregar pick anual: {error_message(exc)}")
    st.stop()

top_cols = st.columns([1.5, 1.2, 2.8, 1.3], vertical_alignment="top")
with top_cols[0]:
    render_gold_metric(player["id"], player["gold"])
top_cols[1].metric("Rodada", round_label)
top_cols[2].metric("Main Collection", collection_label)
top_cols[3].metric("Gold/Rodada", f"{current_round_gold_gain}g")

if year_pick.get("pending"):
    st.warning(f"Pick anual de {year_pick['year']} pendente antes da loja.")
if player.get("boss_pick_pending"):
    st.info("Escolha seu boss monster inicial para liberar o perfil completo.")

actions = st.columns([1.8, 1.8, 6.4], vertical_alignment="bottom")
if starter_imported:
    actions[0].caption("Starter Deck ja importado.")
else:
    uploaded_file = actions[0].file_uploader("Importar Starter Deck (.ydk)", type=["ydk"])
    if uploaded_file and actions[0].button("Importar .ydk"):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/plain")}
        try:
            result = api_post(f"/players/{player['id']}/import-ydk", files=files)
            remember_player(player["id"])
            st.success(f"{result['imported']} cartas importadas.")
            st.rerun()
        except requests.HTTPError as exc:
            st.error(error_message(exc))

advance_label = f"Passar Rodada (+{current_round_gold_gain}g)"
if actions[1].button(advance_label, disabled=bool(year_pick.get("pending"))):
    try:
        result = api_post(f"/players/{player['id']}/advance-round")
        remember_player(player["id"])
        collection_name = result.get("collection_name") or "sem colecao sincronizada"
        gold_gain = int(result.get("gold_gain", current_round_gold_gain))
        pending_year = result.get("player", {}).get("pending_year_pick_year")
        if pending_year:
            st.success(
                f"Rodada avancada. +{gold_gain}g. Proxima colecao: {collection_name}. "
                f"Pick anual de {pending_year} liberado."
            )
        else:
            st.success(f"Rodada avancada. +{gold_gain}g. Proxima colecao: {collection_name}.")
        st.rerun()
    except requests.HTTPError as exc:
        st.error(error_message(exc))

st.divider()

try:
    deck = api_get(f"/players/{player['id']}/deck")
except requests.HTTPError as exc:
    st.error(f"Erro ao carregar deck: {error_message(exc)}")
    st.stop()


def filtered_cards(cards: list[dict], query: str) -> list[dict]:
    if not query:
        return cards
    needle = query.lower()
    return [
        card for card in cards
        if needle in card["name"].lower()
        or needle in (card.get("type") or "").lower()
        or needle in (card.get("archetype") or "").lower()
    ]


def render_card_image(card: dict) -> None:
    if not card.get("image_url"):
        return
    image_url = escape(f"{API_URL}{card['image_url']}")
    card_name = escape(card["name"])
    st.markdown(
        f"""
        <div class="card-thumb-wrap">
            <img class="card-thumb" src="{image_url}" alt="{card_name}" loading="lazy">
            <div class="card-thumb-preview">
                <img src="{image_url}" alt="{card_name}" loading="lazy">
                <div class="card-thumb-preview-title">{card_name}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.dialog("Escolher Boss Monster")
def render_boss_pick_dialog(player_id: int, available_years: list[int]) -> None:
    st.caption("Escolha 1 monstro de qualquer carta do jogo. Esse pick acontece uma unica vez por perfil.")
    start_year = st.selectbox(
        "Ano inicial da run",
        available_years,
        index=0,
        key=f"boss-start-year-{player_id}",
        help="A run comeca ja na primeira colecao desse ano.",
    )
    query = st.text_input("Buscar monstro", key=f"boss-search-{player_id}", placeholder="Ex.: Blue-Eyes, Chaos, Stardust...")
    if not query.strip():
        st.info("Digite o nome de um monstro para buscar.")
        return

    try:
        results = api_get(f"/players/{player_id}/card-search", params={"q": query.strip(), "monster_only": "true"})
    except requests.HTTPError as exc:
        st.error(error_message(exc))
        return

    if not results:
        st.warning("Nenhum monstro encontrado.")
        return

    columns_per_row = 5
    for start in range(0, len(results), columns_per_row):
        row = st.columns(columns_per_row)
        for column, card in zip(row, results[start:start + columns_per_row]):
            with column:
                if card.get("image_url"):
                    st.image(f"{API_URL}{card['image_url']}", use_container_width=True)
                st.caption(card["name"])
                if st.button("Escolher", key=f"boss-pick-{player_id}-{card['card_id']}"):
                    try:
                        api_post(
                            f"/players/{player_id}/boss-pick",
                            json={"card_id": card["card_id"], "start_year": int(start_year)},
                        )
                        st.success(f"{card['name']} entrou no seu deck inicial. Run iniciada em {start_year}.")
                        st.rerun()
                    except requests.HTTPError as exc:
                        st.error(error_message(exc))


available_start_years = sorted(
    {
        year
        for year in (collection_year_from_item(item) for item in collections)
        if year is not None
    }
)
if player.get("boss_pick_pending"):
    render_boss_pick_dialog(player["id"], available_start_years)


def restriction_icon(status: str | None) -> str:
    if status == "banned":
        return "⊘"
    if status == "limited":
        return "1"
    return ""


def render_banlist_thumb(card: dict, status: str | None = None, max_width: int = 84) -> None:
    if not card.get("image_url"):
        return
    image_url = escape(f"{API_URL}{card['image_url']}")
    card_name = escape(card["name"])
    icon = restriction_icon(status or card.get("status") or card.get("restriction_status"))
    badge_html = (
        f'<div style="position:absolute; left:-4px; top:-4px; width:24px; height:24px; border-radius:50%;'
        f'background:{"#991b1b" if icon == "⊘" else "#b45309"}; color:white; display:flex;'
        f'align-items:center; justify-content:center; font-weight:900; font-size:17px;'
        f'box-shadow:0 0 0 2px #020617;">{icon}</div>'
        if icon
        else ""
    )
    st.markdown(
        f"""
        <div style="max-width: {max_width}px; margin: 0 auto; position: relative;">
            <img src="{image_url}" alt="{card_name}" loading="lazy"
                style="width: 100%; border-radius: 4px; display: block;">
            {badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_collection_grid(cards: list[dict], mode: str) -> None:
    if not cards:
        st.info("Nenhuma carta encontrada.")
        return

    cards_per_row = 6 if mode == "editor" else 12
    for row_start in range(0, len(cards), cards_per_row):
        cols = st.columns(cards_per_row, gap="small")
        for col, card in zip(cols, cards[row_start:row_start + cards_per_row]):
            with col:
                render_card_image(card)
                available = card.get("available_quantity", card["quantity"])
                st.markdown(
                    f"""
                    <div class="card-meta">
                        {available}/{card['quantity']} livre<br>
                        {card['rarity']}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                with st.popover(card["name"], use_container_width=True):
                    st.write(card.get("type") or "")
                    if card.get("race"):
                        st.write(f"Raca: {card['race']}")
                    if card.get("archetype"):
                        st.write(f"Arquetipo: {card['archetype']}")
                    st.write(card.get("desc") or "Sem texto.")
                    if mode == "editor":
                        add_cols = st.columns(3)
                        for zone, label, add_col in (
                            ("main", "Main", add_cols[0]),
                            ("extra", "Extra", add_cols[1]),
                            ("side", "Side", add_cols[2]),
                        ):
                            if add_col.button(label, key=f"add-{zone}-{card['card_id']}"):
                                try:
                                    api_post(
                                        f"/players/{player['id']}/deck/cards",
                                        json={"card_id": card["card_id"], "zone": zone},
                                    )
                                    remember_player(player["id"])
                                    st.rerun()
                                except requests.HTTPError as exc:
                                    st.error(error_message(exc))
                    else:
                        st.caption(f"Venda: {format_gold(card['sell_price'])}g")
                        if st.button("Vender 1 copia", key=f"sell-{card['inventory_id']}"):
                            try:
                                api_post(f"/players/{player['id']}/inventory/{card['inventory_id']}/sell")
                                remember_player(player["id"])
                                st.rerun()
                            except requests.HTTPError as exc:
                                st.error(error_message(exc))


def render_deck_zone(title: str, cards: list[dict], count: int, valid: bool, limit_text: str) -> None:
    status = "OK" if valid else "Ajustar"
    st.markdown(
        f"""
        <div class="deck-box">
            <div class="deck-box-title">{title}: {count} cartas ({limit_text}) - {status}</div>
        """,
        unsafe_allow_html=True,
    )
    grouped = {
        "Monstros": [card for card in cards if card["category"] == "monster"],
        "Spells": [card for card in cards if card["category"] == "spell"],
        "Traps": [card for card in cards if card["category"] == "trap"],
    }
    for group_name, group_cards in grouped.items():
        if not group_cards:
            continue
        st.markdown(f'<div class="deck-section-label">{group_name}</div>', unsafe_allow_html=True)
        for card in group_cards:
            line_cols = st.columns([7, 1])
            line_cols[0].markdown(
                f"""
                <div class="deck-card-line">
                    <span class="deck-card-name">{card['quantity']}x {escape(card['name'])}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if line_cols[1].button("-", key=f"remove-{card['deck_id']}"):
                try:
                    api_delete(f"/players/{player['id']}/deck/cards/{card['deck_id']}")
                    remember_player(player["id"])
                    st.rerun()
                except requests.HTTPError as exc:
                    st.error(error_message(exc))
    st.markdown("</div>", unsafe_allow_html=True)


def render_year_pick_tab(player_id: int, year_pick: dict) -> None:
    if not year_pick.get("pending"):
        st.info("Nenhum pick anual pendente.")
        return
    payload = {
        "apiUrl": API_URL,
        "playerId": player_id,
        "year": year_pick["year"],
        "claims": year_pick.get("claims", {}),
        "quotas": year_pick.get("quotas", {}),
        "cards": [
            editor_card_payload(card)
            | {
                "rarity_bucket": card["rarity_bucket"],
                "rarity": card["rarity"],
            }
            for card in year_pick.get("cards", [])
        ],
    }
    html = """
    <div id="year-pick-root"></div>
    <style>
      * { box-sizing: border-box; }
      body { color:#e5e7eb; font-family:Inter, Segoe UI, Arial, sans-serif; margin:0; }
      .pick-shell { background:linear-gradient(135deg,#090d18,#111827 58%,#0b1020); border:1px solid rgba(148,163,184,.55); border-radius:10px; padding:14px; min-height:760px; }
      .pick-top { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom:12px; }
      .pick-title { color:#f8fafc; font-size:18px; font-weight:850; }
      .pick-subtitle { color:#cbd5e1; font-size:12px; margin-top:4px; }
      .pick-search { width:280px; max-width:100%; height:30px; background:#020617; border:1px solid rgba(148,163,184,.7); border-radius:5px; color:#e5e7eb; padding:0 10px; }
      .pick-section { margin-top:18px; border:1px solid rgba(148,163,184,.22); border-radius:8px; background:rgba(2,6,23,.18); overflow:hidden; }
      .pick-section-toggle { width:100%; display:flex; align-items:center; justify-content:space-between; gap:12px; background:rgba(15,23,42,.82); border:0; color:#f8fafc; cursor:pointer; padding:12px 14px; text-align:left; }
      .pick-section-toggle:hover { background:rgba(30,41,59,.88); }
      .pick-section-title { color:#f8fafc; font-size:18px; font-weight:850; margin:0; }
      .pick-section-meta { color:#93c5fd; font-size:12px; font-weight:700; margin-top:3px; }
      .pick-section-caret { color:#cbd5e1; font-size:18px; font-weight:900; line-height:1; }
      .pick-section-body { padding:12px; }
      .pick-section.collapsed .pick-section-body { display:none; }
      .pick-grid { display:grid; grid-template-columns:repeat(12,minmax(0,1fr)); gap:8px; }
      .pick-card { background:rgba(15,23,42,.72); border:1px solid rgba(148,163,184,.28); border-radius:7px; padding:5px; min-width:0; position:relative; }
      .pick-card:hover { border-color:rgba(56,189,248,.9); box-shadow:0 10px 30px rgba(0,0,0,.28); }
      .pick-img { width:100%; aspect-ratio:421/614; object-fit:cover; border-radius:5px; display:block; }
      .pick-name { color:#f8fafc; font-size:10px; font-weight:750; line-height:1.1; min-height:22px; margin-top:4px; }
      .pick-code { color:#93c5fd; font-size:9px; margin-top:2px; }
      .pick-button { width:100%; height:22px; margin-top:4px; border:0; border-radius:4px; background:#b45309; color:white; font-size:10px; font-weight:850; cursor:pointer; padding:0 4px; }
      .pick-button:disabled { opacity:.45; cursor:not-allowed; }
      .pick-hover-preview {
        background: rgba(2, 6, 23, 0.92);
        border: 1px solid rgba(147, 197, 253, 0.8);
        border-radius: 8px;
        box-shadow: 0 18px 42px rgba(0,0,0,0.45);
        display: none;
        max-height: calc(100vh - 24px);
        padding: 6px;
        pointer-events: none;
        position: fixed;
        width: min(340px, 26vw);
        z-index: 9999;
      }
      .pick-hover-preview img { border-radius:4px; display:block; max-height:calc(100vh - 36px); object-fit:contain; width:100%; }
      .pick-hover-preview-title { display:none; }
      .toast { display:none; margin-bottom:10px; padding:8px; border-radius:6px; background:#450a0a; border:1px solid #fca5a5; color:#fee2e2; font-size:13px; }
      @media (max-width: 1400px) { .pick-grid { grid-template-columns:repeat(10,minmax(0,1fr)); } }
      @media (max-width: 1180px) { .pick-grid { grid-template-columns:repeat(8,minmax(0,1fr)); } }
      @media (max-width: 900px) { .pick-grid { grid-template-columns:repeat(6,minmax(0,1fr)); } }
      @media (max-width: 680px) { .pick-grid { grid-template-columns:repeat(4,minmax(0,1fr)); } .pick-top { flex-direction:column; align-items:stretch; } .pick-search { width:100%; } }
    </style>
    <script>
      let data = __PAYLOAD__;
      const root = document.getElementById("year-pick-root");
      const bucketOrder = ["common", "rare", "super", "ultra", "secret", "prismatic", "other"];
      const bucketLabels = {
        common: "Common",
        rare: "Rare",
        super: "Super",
        ultra: "Ultra",
        secret: "Secret",
        prismatic: "Prismatic",
        other: "Outras"
      };
      let currentFilter = "";
      let collapsedBuckets = {};
      function positionPreview(preview, item){
        const rect = item.getBoundingClientRect();
        const previewWidth = preview.offsetWidth || 340;
        const previewHeight = preview.offsetHeight || Math.floor(previewWidth * 1.46);
        const gutter = 12;
        const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
        const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
        let left = rect.right + gutter;
        if (left + previewWidth > viewportWidth - 8) left = rect.left - previewWidth - gutter;
        if (left < 8) left = Math.max(8, Math.min(viewportWidth - previewWidth - 8, rect.left + gutter));
        let top = rect.top + (rect.height / 2) - (previewHeight / 2);
        top = Math.max(8, Math.min(top, viewportHeight - previewHeight - 8));
        preview.style.left = `${left}px`;
        preview.style.top = `${top}px`;
      }
      function esc(v){return String(v??"").replace(/[&<>\"']/g,c=>({\"&\":\"&amp;\",\"<\":\"&lt;\",\">\":\"&gt;\",'\"':\"&quot;\",\"'\":\"&#39;\"}[c]));}
      function showError(msg){const t=document.querySelector(".toast"); t.textContent=msg; t.style.background="#450a0a"; t.style.borderColor="#fca5a5"; t.style.color="#fee2e2"; t.style.display="block"; setTimeout(()=>t.style.display="none",3000);}
      function showSuccess(msg){const t=document.querySelector(".toast"); t.textContent=msg; t.style.background="#064e3b"; t.style.borderColor="#34d399"; t.style.color="#d1fae5"; t.style.display="block"; setTimeout(()=>t.style.display="none",2200);}
      function markEditorDirty(){try{window.localStorage.setItem("ygo_editor_dirty","1");}catch(err){}}
      function ensureCollapsedState(){
        bucketOrder.forEach(bucket => {
          if (collapsedBuckets[bucket] !== undefined) return;
          const claimed = Number((data.claims || {})[bucket] || 0);
          const quota = Number((data.quotas || {})[bucket] || 2);
          collapsedBuckets[bucket] = claimed >= quota;
        });
      }
      async function claim(cardId){
        const res = await fetch(`${data.apiUrl}/players/${data.playerId}/year-pick/claim`, {
          method:"POST", headers:{"Content-Type":"application/json"},
          body:JSON.stringify({card_id:Number(cardId)})
        });
        const payload = await res.json().catch(()=>({}));
        if(!res.ok) throw new Error(payload.detail || "Nao foi possivel pegar a carta.");
        data.claims = payload.claims || data.claims;
        data.quotas = payload.quotas || data.quotas;
        if (!payload.pending) {
          data.year = null;
          data.cards = [];
        }
      }
      function filteredCards(bucket){
        const needle = currentFilter.trim().toLowerCase();
        return data.cards.filter(card =>
          card.rarity_bucket === bucket && (
            !needle ||
            card.name.toLowerCase().includes(needle) ||
            (card.type || "").toLowerCase().includes(needle) ||
            (card.rarity || "").toLowerCase().includes(needle)
          )
        );
      }
      function cardHtml(card, disabled){
        return `<article class="pick-card">
          <img class="pick-img" src="${esc(card.image_url)}" alt="${esc(card.name)}">
          <div class="pick-name">${esc(card.name)}</div>
          <div class="pick-code">${esc(card.rarity)}</div>
          <button class="pick-button" data-card="${card.card_id}" ${disabled ? "disabled" : ""}>Pegar</button>
        </article>`;
      }
      function render(){
        ensureCollapsedState();
        if (!data.cards.length) {
          root.innerHTML = `<section class="pick-shell"><div class="pick-title">Pick Anual</div><div class="pick-subtitle">Nenhum pick anual pendente.</div></section>`;
          return;
        }
        root.innerHTML = `<section class="pick-shell">
          <div class="pick-hover-preview"><img alt=""><div class="pick-hover-preview-title"></div></div>
          <div class="toast"></div>
          <div class="pick-top">
            <div>
              <div class="pick-title">Pick anual de ${data.year}</div>
              <div class="pick-subtitle">Resolva este resgate antes de acessar a loja do proximo ano.</div>
            </div>
            <input class="pick-search" value="${esc(currentFilter)}" placeholder="Buscar carta, tipo ou raridade">
          </div>
          ${bucketOrder.map(bucket => {
            const claimed = Number((data.claims || {})[bucket] || 0);
            const quota = Number((data.quotas || {})[bucket] || 2);
            const cards = filteredCards(bucket);
            if (!cards.length) return "";
            const disabled = claimed >= quota;
            const collapsed = !!collapsedBuckets[bucket];
            return `<section class="pick-section ${collapsed ? "collapsed" : ""}">
              <button class="pick-section-toggle" data-toggle-bucket="${bucket}">
                <div>
                  <div class="pick-section-title">${bucketLabels[bucket]} - ${claimed}/${quota}</div>
                  <div class="pick-section-meta">${cards.length} cartas disponiveis</div>
                </div>
                <span class="pick-section-caret">${collapsed ? "+" : "-"}</span>
              </button>
              <div class="pick-section-body">
                <div class="pick-grid">${cards.map(card => cardHtml(card, disabled)).join("")}</div>
              </div>
            </section>`;
          }).join("")}
        </section>`;
        const search = document.querySelector(".pick-search");
        search.addEventListener("input", (event) => {
          currentFilter = event.target.value;
          render();
        });
        document.querySelectorAll("[data-toggle-bucket]").forEach(button => {
          button.addEventListener("click", () => {
            const bucket = button.dataset.toggleBucket;
            collapsedBuckets[bucket] = !collapsedBuckets[bucket];
            render();
          });
        });
        document.querySelectorAll(".pick-card").forEach(cardEl => {
          cardEl.addEventListener("mouseenter", () => {
            const image = cardEl.querySelector(".pick-img");
            const preview = document.querySelector(".pick-hover-preview");
            if (!image || !preview) return;
            preview.querySelector("img").src = image.src;
            preview.querySelector("img").alt = image.alt;
            preview.style.display = "block";
            positionPreview(preview, cardEl);
          });
          cardEl.addEventListener("mousemove", () => {
            const preview = document.querySelector(".pick-hover-preview");
            if (!preview || preview.style.display !== "block") return;
            positionPreview(preview, cardEl);
          });
          cardEl.addEventListener("mouseleave", () => {
            const preview = document.querySelector(".pick-hover-preview");
            if (preview) preview.style.display = "none";
          });
        });
        document.querySelectorAll("[data-card]").forEach(btn => {
          btn.addEventListener("click", async () => {
            try {
              const card = data.cards.find(item => Number(item.card_id) === Number(btn.dataset.card));
              await claim(btn.dataset.card);
              if (card) {
                const bucket = card.rarity_bucket;
                const claimed = Number((data.claims || {})[bucket] || 0);
                const quota = Number((data.quotas || {})[bucket] || 2);
                if (claimed >= quota) collapsedBuckets[bucket] = true;
              }
              if (!data.year || !data.cards.length) {
                try { window.parent.location.reload(); } catch (err) {}
                return;
              }
              markEditorDirty();
              render();
              showSuccess("Carta adicionada ao inventario.");
            } catch (err) {
              showError(err.message);
            }
          });
        });
      }
      render();
    </script>
    """.replace("__PAYLOAD__", json.dumps(payload))
    components.html(html, height=880, scrolling=True)


def editor_card_payload(card: dict) -> dict:
    card_type = card.get("type") or ""
    if "Normal" in card_type and "Monster" in card_type:
        sort_category = 0
    elif "Effect" in card_type and "Monster" in card_type and "Ritual" not in card_type:
        sort_category = 1
    elif "Ritual" in card_type:
        sort_category = 2
    elif "Spell" in card_type:
        sort_category = 3
    elif "Trap" in card_type:
        sort_category = 4
    elif "Fusion" in card_type:
        sort_category = 5
    elif "Synchro" in card_type:
        sort_category = 6
    elif "Xyz" in card_type:
        sort_category = 7
    elif "Link" in card_type:
        sort_category = 8
    else:
        sort_category = 9
    return {
        "card_id": card["card_id"],
        "deck_id": card.get("deck_id"),
        "name": card["name"],
        "type": card_type,
        "rarity": card.get("rarity") or "Common",
        "quantity": card.get("quantity", 1),
        "available_quantity": card.get("available_quantity", card.get("quantity", 1)),
        "category": card.get("category", "monster"),
        "sort_category": sort_category,
        "restriction_status": card.get("restriction_status"),
        "image_url": f"{API_URL}{card['image_url']}" if card.get("image_url") else "",
    }


def card_type_sort_key(card: dict) -> tuple[int, str]:
    card_type = card.get("type") or ""
    if "Normal" in card_type and "Monster" in card_type:
        category = 0
    elif "Effect" in card_type and "Monster" in card_type and "Ritual" not in card_type:
        category = 1
    elif "Ritual" in card_type:
        category = 2
    elif "Spell" in card_type:
        category = 3
    elif "Trap" in card_type:
        category = 4
    elif "Fusion" in card_type:
        category = 5
    elif "Synchro" in card_type:
        category = 6
    elif "Xyz" in card_type:
        category = 7
    elif "Link" in card_type:
        category = 8
    else:
        category = 9
    return category, card["name"]


def expanded_deck_cards(cards: list[dict]) -> list[dict]:
    expanded = []
    for card in cards:
        for copy_number in range(card["quantity"]):
            copy = editor_card_payload(card)
            copy["copy_number"] = copy_number + 1
            expanded.append(copy)
    return expanded


def render_deck_editor_component(player_id: int, deck_data: dict, inventory_cards: list[dict]) -> None:
    payload = {
        "apiUrl": API_URL,
        "playerId": player_id,
        "deck": {
            "main": expanded_deck_cards(deck_data["main"]),
            "extra": expanded_deck_cards(deck_data["extra"]),
            "side": expanded_deck_cards(deck_data["side"]),
            "main_count": deck_data["main_count"],
            "extra_count": deck_data["extra_count"],
            "side_count": deck_data["side_count"],
            "is_main_valid": deck_data["is_main_valid"],
            "is_extra_valid": deck_data["is_extra_valid"],
            "is_side_valid": deck_data["is_side_valid"],
        },
        "inventory": [editor_card_payload(card) for card in inventory_cards],
    }
    html = """
    <div id="deck-editor-root"></div>
    <style>
      * { box-sizing: border-box; }
      body {
        color: #e5e7eb;
        font-family: "Inter", "Segoe UI", Arial, sans-serif;
        margin: 0;
      }
      :root {
        --binder-target-height: 930px;
      }
      .editor-shell {
        display: grid;
        gap: 10px;
        grid-template-columns: minmax(860px, 1.95fr) minmax(330px, 0.78fr);
        min-height: 760px;
      }
      .deck-stack, .binder-panel {
        background:
          radial-gradient(circle at top left, rgba(59, 130, 246, 0.14), transparent 34%),
          linear-gradient(180deg, #0a1122 0%, #121a31 100%);
        border: 1px solid rgba(96, 165, 250, 0.26);
        border-radius: 10px;
        box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04);
        overflow: hidden;
      }
      .deck-stack {
        display: grid;
        gap: 6px;
        grid-template-columns: 1fr;
        padding: 6px;
      }
      .zone {
        border: 1px solid rgba(96, 165, 250, 0.18);
        border-radius: 6px;
        padding: 0;
        overflow: hidden;
      }
      .zone-header {
        align-items: center;
        background: linear-gradient(90deg, #162246 0%, #1c2952 58%, #23386c 100%);
        border-bottom: 1px solid rgba(147, 197, 253, 0.22);
        display: flex;
        gap: 8px;
        height: 30px;
        padding: 0 10px;
      }
      .zone-title {
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 0.14em;
        min-width: 52px;
        text-transform: uppercase;
      }
      .zone-count {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 4px;
        font-size: 10px;
        font-weight: 700;
        min-width: 26px;
        padding: 0 7px;
        text-align: center;
      }
      .zone-status {
        color: #dbeafe;
        font-size: 9px;
        letter-spacing: 0.08em;
        margin-left: auto;
        text-transform: uppercase;
      }
      .zone-cards {
        align-content: start;
        background:
          linear-gradient(180deg, rgba(14, 20, 39, 0.98) 0%, rgba(17, 24, 39, 0.96) 100%);
        display: grid;
        gap: 1px;
        overflow: hidden;
        padding: 6px 8px 8px;
      }
      .zone-main .zone-cards {
        grid-template-columns: repeat(12, minmax(0, 1fr));
        min-height: 0;
      }
      .zone-extra .zone-cards, .zone-side .zone-cards {
        grid-template-columns: repeat(15, minmax(0, 1fr));
        min-height: 96px;
      }
      .drop-active {
        outline: 2px solid #38bdf8;
        outline-offset: -3px;
      }
      .card-img {
        aspect-ratio: 421 / 614;
        border-radius: 3px;
        cursor: grab;
        display: block;
        max-width: 100%;
        object-fit: cover;
        user-select: none;
        width: 100%;
      }
      .card-img:active { cursor: grabbing; }
      .deck-card {
        position: relative;
        transform: translateZ(0);
      }
      .zone-main .deck-card {
        justify-self: stretch;
        max-width: none;
        width: 100%;
      }
      .zone-extra .deck-card, .zone-side .deck-card {
        justify-self: stretch;
        max-width: none;
        width: 100%;
      }
      .deck-card:hover .card-img, .binder-card:hover .card-img {
        box-shadow: 0 0 0 2px #38bdf8, 0 8px 20px rgba(0,0,0,0.38);
      }
      .hover-preview {
        background: rgba(2, 6, 23, 0.92);
        border: 1px solid rgba(147, 197, 253, 0.8);
        border-radius: 8px;
        box-shadow: 0 18px 42px rgba(0,0,0,0.45);
        display: none;
        padding: 6px;
        pointer-events: none;
        position: fixed;
        max-height: calc(100vh - 24px);
        width: min(340px, 26vw);
        z-index: 9999;
      }
      .hover-preview img {
        border-radius: 4px;
        display: block;
        max-height: calc(100vh - 36px);
        object-fit: contain;
        width: 100%;
      }
      .hover-preview-title {
        display: none;
      }
      .binder-panel {
        align-self: start;
        display: flex;
        flex-direction: column;
        height: var(--binder-target-height);
        max-height: var(--binder-target-height);
        min-height: 0;
        overflow: hidden;
        padding: 8px;
      }
      .binder-tools {
        display: grid;
        gap: 8px;
        grid-template-columns: 1fr;
        margin-bottom: 8px;
      }
      .binder-title {
        align-items: center;
        display: flex;
        font-size: 11px;
        font-weight: 800;
        justify-content: space-between;
        letter-spacing: 0.12em;
        text-transform: uppercase;
      }
      .binder-title span {
        color: #93c5fd;
        font-size: 8px;
        font-weight: 600;
        text-transform: none;
      }
      .binder-actions {
        display: flex;
        gap: 8px;
        margin-bottom: 2px;
      }
      .binder-action {
        background: linear-gradient(180deg, #0f1831 0%, #0a1121 100%);
        border: 1px solid rgba(147, 197, 253, 0.35);
        border-radius: 4px;
        color: #e5e7eb;
        cursor: pointer;
        font-size: 10px;
        font-weight: 700;
        height: 28px;
        padding: 0 9px;
      }
      .binder-action:hover {
        border-color: rgba(96, 165, 250, 0.9);
      }
      .binder-pager {
        align-items: center;
        color: #cbd5e1;
        display: flex;
        font-size: 10px;
        gap: 6px;
        justify-content: space-between;
      }
      .pager-buttons {
        display: flex;
        gap: 6px;
      }
      .pager-button {
        background: #0b1224;
        border: 1px solid rgba(148, 163, 184, 0.45);
        border-radius: 4px;
        color: #e5e7eb;
        cursor: pointer;
        height: 26px;
        min-width: 26px;
      }
      .pager-button:disabled {
        cursor: default;
        opacity: 0.42;
      }
      .binder-search {
        background: rgba(2, 6, 23, 0.88);
        border: 1px solid rgba(148, 163, 184, 0.46);
        border-radius: 4px;
        color: #e5e7eb;
        height: 30px;
        padding: 0 9px;
        width: 100%;
      }
      .binder-filter {
        background: rgba(2, 6, 23, 0.88);
        border: 1px solid rgba(148, 163, 184, 0.46);
        border-radius: 4px;
        color: #e5e7eb;
        height: 30px;
        padding: 0 9px;
        width: 100%;
      }
      .binder-grid {
        align-content: start;
        display: grid;
        flex: 1;
        gap: 6px 6px;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        justify-items: stretch;
        padding: 2px 0 0;
      }
      .binder-card {
        justify-self: stretch;
        max-width: none;
        min-width: 0;
        position: relative;
        width: 100%;
      }
      .binder-card.disabled {
        cursor: not-allowed;
      }
      .restriction-badge {
        border-radius: 999px;
        color: white;
        font-size: 16px;
        font-weight: 900;
        height: 24px;
        left: -4px;
        line-height: 24px;
        position: absolute;
        text-align: center;
        top: 2px;
        width: 24px;
        box-shadow: 0 0 0 2px #020617;
      }
      .restriction-limited { background: #b45309; }
      .restriction-banned { background: #991b1b; }
      .card-badge {
        background: rgba(2, 6, 23, 0.86);
        border: 1px solid rgba(255,255,255,0.35);
        border-radius: 999px;
        color: #f8fafc;
        font-size: 10px;
        font-weight: 800;
        min-width: 22px;
        padding: 1px 5px;
        position: absolute;
        right: 2px;
        text-align: center;
        top: 2px;
      }
      .empty-zone {
        align-items: center;
        color: #64748b;
        display: flex;
        font-size: 11px;
        grid-column: 1 / -1;
        justify-content: center;
        min-height: 90px;
      }
      .toast {
        background: #450a0a;
        border: 1px solid #fca5a5;
        border-radius: 6px;
        color: #fee2e2;
        display: none;
        font-size: 13px;
        margin-bottom: 8px;
        padding: 8px;
      }
      @media (max-width: 1440px) {
        :root {
          --binder-target-height: 590px;
        }
        .editor-shell {
          grid-template-columns: minmax(760px, 1.8fr) minmax(300px, 0.82fr);
        }
        .zone-main .zone-cards {
          grid-template-columns: repeat(11, minmax(0, 1fr));
        }
      }
      @media (max-width: 1180px) {
        :root {
          --binder-target-height: auto;
        }
        .editor-shell {
          grid-template-columns: 1fr;
        }
        .deck-stack,
        .binder-panel {
          min-height: auto;
        }
        .binder-panel {
          max-height: none;
        }
        .zone-main .zone-cards {
          grid-template-columns: repeat(10, minmax(0, 1fr));
        }
        .zone-extra .zone-cards, .zone-side .zone-cards {
          grid-template-columns: repeat(10, minmax(0, 1fr));
        }
        .binder-grid {
          grid-template-columns: repeat(5, minmax(0, 1fr));
        }
      }
    </style>
    <script>
      let data = __PAYLOAD__;
      let currentFilter = "";
      let currentBinderFilterMode = "all";
      let currentPage = 0;
      const root = document.getElementById("deck-editor-root");
      let lastRefreshAt = 0;
      const DIRTY_FLAG_KEY = "ygo_editor_dirty";

      function esc(value) {
        return String(value ?? "").replace(/[&<>"']/g, (char) => ({
          "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
        }[char]));
      }

      function normalizedImageUrl(imageUrl) {
        if (!imageUrl) return "";
        return imageUrl.startsWith("/") ? `${data.apiUrl}${imageUrl}` : imageUrl;
      }

      function expandedDeckCards(cards) {
        const expanded = [];
        cards.forEach((card) => {
          for (let index = 0; index < Number(card.quantity || 1); index += 1) {
            expanded.push({
              card_id: card.card_id,
              deck_id: card.deck_id,
              name: card.name,
              type: card.type || "",
              rarity: card.rarity || "Common",
              quantity: card.quantity || 1,
              category: card.category || "monster",
              sort_category: card.sort_category ?? 0,
              restriction_status: card.restriction_status || null,
              image_url: normalizedImageUrl(card.image_url),
              copy_number: index + 1
            });
          }
        });
        return expanded;
      }

      function sortCategory(cardType) {
        const type = cardType || "";
        if (type.includes("Normal") && type.includes("Monster")) return 0;
        if (type.includes("Effect") && type.includes("Monster") && !type.includes("Ritual")) return 1;
        if (type.includes("Ritual")) return 2;
        if (type.includes("Spell")) return 3;
        if (type.includes("Trap")) return 4;
        if (type.includes("Fusion")) return 5;
        if (type.includes("Synchro")) return 6;
        if (type.includes("Xyz")) return 7;
        if (type.includes("Link")) return 8;
        return 9;
      }

      function normalizeInventoryCard(card) {
        return {
          card_id: card.card_id,
          name: card.name,
          type: card.type || "",
          rarity: card.rarity || "Common",
          quantity: card.quantity || 0,
          available_quantity: card.available_quantity || 0,
          category: card.category || "monster",
          sort_category: sortCategory(card.type),
          restriction_status: card.restriction_status || null,
          image_url: normalizedImageUrl(card.image_url)
        };
      }

      function normalizeDeck(deckResponse) {
        return {
          main: expandedDeckCards(deckResponse.main || []),
          extra: expandedDeckCards(deckResponse.extra || []),
          side: expandedDeckCards(deckResponse.side || []),
          main_count: deckResponse.main_count || 0,
          extra_count: deckResponse.extra_count || 0,
          side_count: deckResponse.side_count || 0,
          is_main_valid: Boolean(deckResponse.is_main_valid),
          is_extra_valid: Boolean(deckResponse.is_extra_valid),
          is_side_valid: Boolean(deckResponse.is_side_valid)
        };
      }

      async function refreshEditorData() {
        const now = Date.now();
        if (now - lastRefreshAt < 1500) return;
        lastRefreshAt = now;
        const [inventoryResponse, deckResponse] = await Promise.all([
          fetch(`${data.apiUrl}/players/${data.playerId}/inventory`),
          fetch(`${data.apiUrl}/players/${data.playerId}/deck`)
        ]);
        if (!inventoryResponse.ok || !deckResponse.ok) return;
        data.inventory = (await inventoryResponse.json()).map(normalizeInventoryCard);
        data.deck = normalizeDeck(await deckResponse.json());
        try { window.localStorage.removeItem(DIRTY_FLAG_KEY); } catch (err) {}
        render(currentFilter);
      }

      function isEditorDirty() {
        try {
          return window.localStorage.getItem(DIRTY_FLAG_KEY) === "1";
        } catch (err) {
          return false;
        }
      }

      function changeAvailable(cardId, delta) {
        const card = data.inventory.find((item) => Number(item.card_id) === Number(cardId));
        if (!card) return;
        const nextValue = Number(card.available_quantity || 0) + delta;
        card.available_quantity = Math.max(0, Math.min(Number(card.quantity || 0), nextValue));
      }

      async function addCard(cardId, zone) {
        const response = await fetch(`${data.apiUrl}/players/${data.playerId}/deck/cards`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ card_id: Number(cardId), zone })
        });
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload.detail || "Nao foi possivel adicionar a carta.");
        }
        return response.json();
      }

      async function removeDeckCard(deckId) {
        const response = await fetch(`${data.apiUrl}/players/${data.playerId}/deck/cards/${deckId}`, {
          method: "DELETE"
        });
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload.detail || "Nao foi possivel remover a carta.");
        }
        return response.json();
      }

      async function exportDeckYdke() {
        const response = await fetch(`${data.apiUrl}/players/${data.playerId}/deck/export-ydke`);
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(payload.detail || "Nao foi possivel exportar o deck.");
        }
        return payload.ydke || "";
      }

      function showError(message) {
        const toast = document.querySelector(".toast");
        toast.textContent = message;
        toast.style.background = "#450a0a";
        toast.style.borderColor = "#fca5a5";
        toast.style.color = "#fee2e2";
        toast.style.display = "block";
        setTimeout(() => { toast.style.display = "none"; }, 3500);
      }

      function showSuccess(message) {
        const toast = document.querySelector(".toast");
        toast.textContent = message;
        toast.style.background = "#064e3b";
        toast.style.borderColor = "#34d399";
        toast.style.color = "#d1fae5";
        toast.style.display = "block";
        setTimeout(() => { toast.style.display = "none"; }, 2500);
      }

      function markEditorDirty() {
        try {
          window.localStorage.setItem(DIRTY_FLAG_KEY, "1");
        } catch (err) {}
      }

      function deckCardHtml(card, zone) {
        return `
          <div class="deck-card" draggable="true" data-kind="deck" data-card-id="${card.card_id}" data-deck-id="${card.deck_id}" data-zone="${zone}" title="${esc(card.name)}">
            <img class="card-img" src="${esc(card.image_url)}" alt="${esc(card.name)}">
          </div>
        `;
      }

      function zoneHtml(zone, title, count, valid, limit) {
        const cards = data.deck[zone];
        const cardHtml = cards.length ? cards.map((card) => deckCardHtml(card, zone)).join("") : `<div class="empty-zone">Arraste cartas para ${title}</div>`;
        return `
          <section class="zone zone-${zone}">
            <div class="zone-header">
              <div class="zone-title">${title}</div>
              <div class="zone-count">${count}</div>
              <div class="zone-status">${limit} ${valid ? "OK" : "Ajustar"}</div>
            </div>
            <div class="zone-cards" data-zone="${zone}">${cardHtml}</div>
          </section>
        `;
      }

      function binderCardHtml(card) {
        const disabled = Number(card.available_quantity) <= 0 || card.restriction_status === "banned";
        const restrictionBadge = card.restriction_status
          ? `<div class="restriction-badge restriction-${card.restriction_status}">${card.restriction_status === "banned" ? "⊘" : "1"}</div>`
          : "";
        return `
          <div class="binder-card ${disabled ? "disabled" : ""}" draggable="${disabled ? "false" : "true"}"
               data-kind="inventory" data-card-id="${card.card_id}" title="${esc(card.name)}">
            <img class="card-img" src="${esc(card.image_url)}" alt="${esc(card.name)}">
            ${restrictionBadge}
            <div class="card-badge">${card.available_quantity}/${card.quantity}</div>
          </div>
        `;
      }

      function passesBinderFilter(card) {
        if (currentBinderFilterMode === "not_in_deck") {
          return Number(card.available_quantity || 0) === Number(card.quantity || 0);
        }
        if (currentBinderFilterMode === "spare") {
          return Number(card.available_quantity || 0) > 0 && Number(card.available_quantity || 0) < Number(card.quantity || 0);
        }
        return true;
      }

      function binderColumnCount() {
        const viewportWidth = Math.max(window.innerWidth || 0, document.documentElement?.clientWidth || 0, 1280);
        if (viewportWidth <= 1180) return 5;
        return 5;
      }

      function binderPageSize() {
        const viewportWidth = Math.max(window.innerWidth || 0, document.documentElement?.clientWidth || 0, 1280);
        const columns = binderColumnCount();
        const minimumCards = viewportWidth <= 1180 ? 20 : 30;
        const shellGap = viewportWidth <= 1180 ? 0 : 10;
        const editorWidth = Math.max(960, viewportWidth - 120);
        const binderWidth = viewportWidth <= 1180
          ? editorWidth - 16
          : Math.max(330, Math.round((editorWidth - shellGap) * 0.285));
        const horizontalPadding = 16;
        const columnGap = 6;
        const cardWidth = Math.floor((binderWidth - horizontalPadding - (columnGap * (columns - 1))) / columns);
        const cardHeight = Math.floor(cardWidth * (614 / 421));
        const targetZoneHeight = viewportWidth <= 1180 ? 620 : (viewportWidth <= 1440 ? 590 : 610);
        const toolArea = viewportWidth <= 1180 ? 150 : 132;
        const availableHeight = Math.max(150, targetZoneHeight - toolArea);
        const rowHeight = cardHeight + 6;
        const rows = Math.max(3, Math.floor(availableHeight / rowHeight));
        return Math.max(columns * rows, minimumCards);
      }

      function render(filter = "") {
        currentFilter = filter;
        const needle = filter.trim().toLowerCase();
        const pageSize = binderPageSize();
        const inventory = data.inventory
          .filter((card) => passesBinderFilter(card))
          .filter((card) =>
            !needle || card.name.toLowerCase().includes(needle) ||
            card.type.toLowerCase().includes(needle) ||
            card.rarity.toLowerCase().includes(needle)
          )
          .sort((left, right) =>
            Number(left.sort_category ?? 0) - Number(right.sort_category ?? 0) ||
            left.name.localeCompare(right.name)
          );
        const pageCount = Math.max(1, Math.ceil(inventory.length / pageSize));
        currentPage = Math.min(Math.max(currentPage, 0), pageCount - 1);
        const pageStart = currentPage * pageSize;
        const pageInventory = inventory.slice(pageStart, pageStart + pageSize);

        root.innerHTML = `
          <div class="editor-shell">
            <div class="hover-preview">
              <img alt="">
              <div class="hover-preview-title"></div>
            </div>
            <div class="deck-stack">
              ${zoneHtml("main", "Main", data.deck.main_count, data.deck.is_main_valid, "40-60")}
              ${zoneHtml("extra", "Extra", data.deck.extra_count, data.deck.is_extra_valid, "0-15")}
              ${zoneHtml("side", "Side", data.deck.side_count, data.deck.is_side_valid, "0-15")}
            </div>
            <aside class="binder-panel">
              <div class="toast"></div>
               <div class="binder-tools">
                <div class="binder-title">Colecao <span>arraste para o deck ou solte aqui para remover</span></div>
                 <div class="binder-actions">
                   <button class="binder-action" data-export-ydke="true">Copiar .ydke</button>
                 </div>
                 <input class="binder-search" value="${esc(filter)}" placeholder="Buscar carta, tipo ou raridade">
                 <select class="binder-filter">
                   <option value="all" ${currentBinderFilterMode === "all" ? "selected" : ""}>Todas</option>
                   <option value="not_in_deck" ${currentBinderFilterMode === "not_in_deck" ? "selected" : ""}>Fora do deck</option>
                   <option value="spare" ${currentBinderFilterMode === "spare" ? "selected" : ""}>Com copias sobrando</option>
                 </select>
                 <div class="binder-pager">
                   <span>${inventory.length ? pageStart + 1 : 0}-${Math.min(pageStart + pageSize, inventory.length)} de ${inventory.length} cartas</span>
                  <span>Pagina ${currentPage + 1}/${pageCount}</span>
                  <div class="pager-buttons">
                    <button class="pager-button" data-page-delta="-1" ${currentPage <= 0 ? "disabled" : ""}>‹</button>
                    <button class="pager-button" data-page-delta="1" ${currentPage >= pageCount - 1 ? "disabled" : ""}>›</button>
                  </div>
                </div>
               </div>
               <div class="binder-grid">${pageInventory.map(binderCardHtml).join("")}</div>
             </aside>
           </div>
        `;
        wireEvents();
        const search = document.querySelector(".binder-search");
        search.focus();
        search.setSelectionRange(search.value.length, search.value.length);
        search.addEventListener("input", (event) => {
          currentPage = 0;
          render(event.target.value);
        });
        document.querySelector(".binder-filter").addEventListener("change", (event) => {
          currentBinderFilterMode = event.target.value;
          currentPage = 0;
          render(currentFilter);
        });
      }

      function wireEvents() {
        function positionPreview(preview, item) {
          const rect = item.getBoundingClientRect();
          const previewWidth = preview.offsetWidth || 280;
          const previewHeight = preview.offsetHeight || Math.floor(previewWidth * 1.46);
          const gutter = 12;
          const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
          const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
          let left = rect.right + gutter;
          if (left + previewWidth > viewportWidth - 8) {
            left = rect.left - previewWidth - gutter;
          }
          if (left < 8) {
            left = Math.max(8, Math.min(viewportWidth - previewWidth - 8, rect.left + gutter));
          }
          let top = rect.top + (rect.height / 2) - (previewHeight / 2);
          top = Math.max(8, Math.min(top, viewportHeight - previewHeight - 8));
          preview.style.left = `${left}px`;
          preview.style.top = `${top}px`;
        }

        document.querySelectorAll("[draggable='true']").forEach((item) => {
          item.addEventListener("dragstart", (event) => {
            const payload = {
              kind: item.dataset.kind,
              cardId: item.dataset.cardId,
              deckId: item.dataset.deckId,
              zone: item.dataset.zone
            };
            event.dataTransfer.setData("application/json", JSON.stringify(payload));
          });
          item.addEventListener("mouseenter", () => {
            const image = item.querySelector("img");
            const preview = document.querySelector(".hover-preview");
            if (!image || !preview) return;
            preview.querySelector("img").src = image.src;
            preview.querySelector("img").alt = image.alt;
            preview.style.display = "block";
            positionPreview(preview, item);
          });
          item.addEventListener("mousemove", () => {
            const preview = document.querySelector(".hover-preview");
            if (!preview || preview.style.display !== "block") return;
            positionPreview(preview, item);
          });
          item.addEventListener("mouseleave", () => {
            const preview = document.querySelector(".hover-preview");
            if (preview) preview.style.display = "none";
          });
        });

        document.querySelectorAll("[data-page-delta]").forEach((button) => {
          button.addEventListener("click", () => {
            currentPage += Number(button.dataset.pageDelta);
            render(currentFilter);
          });
        });

        const exportButton = document.querySelector("[data-export-ydke='true']");
        exportButton.addEventListener("click", async () => {
          try {
            const ydke = await exportDeckYdke();
            await navigator.clipboard.writeText(ydke);
            showSuccess("Deck .ydke copiado para o clipboard.");
          } catch (err) {
            showError(err.message || "Nao foi possivel copiar o deck.");
          }
        });

        const binderPanel = document.querySelector(".binder-panel");
        binderPanel.addEventListener("wheel", (event) => {
          event.preventDefault();
          const direction = event.deltaY > 0 ? 1 : -1;
          const nextPage = Math.min(Math.max(currentPage + direction, 0), Number.MAX_SAFE_INTEGER);
          if (nextPage !== currentPage) {
            currentPage = nextPage;
            render(currentFilter);
          }
        }, { passive: false });

        async function moveDeckCardBetweenZones(payload, targetZone) {
          if (!payload.deckId || !payload.zone || payload.zone === targetZone) return false;
          const removedDeck = await removeDeckCard(payload.deckId);
          data.deck = normalizeDeck(removedDeck);
          changeAvailable(payload.cardId, 1);
          try {
            const addedDeck = await addCard(payload.cardId, targetZone);
            data.deck = normalizeDeck(addedDeck);
            changeAvailable(payload.cardId, -1);
            markEditorDirty();
            render(currentFilter);
            return true;
          } catch (err) {
            try {
              const restoredDeck = await addCard(payload.cardId, payload.zone);
              data.deck = normalizeDeck(restoredDeck);
              changeAvailable(payload.cardId, -1);
            } catch (restoreErr) {}
            throw err;
          }
        }

        async function removeDeckCardToBinder(payload) {
          if (payload.kind !== "deck") return;
          const deckResponse = await removeDeckCard(payload.deckId);
          data.deck = normalizeDeck(deckResponse);
          changeAvailable(payload.cardId, 1);
          markEditorDirty();
          render(currentFilter);
        }

        document.querySelectorAll(".zone-cards").forEach((zone) => {
          zone.addEventListener("dragover", (event) => {
            event.preventDefault();
            zone.classList.add("drop-active");
          });
          zone.addEventListener("dragleave", () => zone.classList.remove("drop-active"));
          zone.addEventListener("drop", async (event) => {
            event.preventDefault();
            zone.classList.remove("drop-active");
            const payload = JSON.parse(event.dataTransfer.getData("application/json") || "{}");
            try {
              if (payload.kind === "inventory") {
                const deckResponse = await addCard(payload.cardId, zone.dataset.zone);
                data.deck = normalizeDeck(deckResponse);
                changeAvailable(payload.cardId, -1);
                markEditorDirty();
                render(currentFilter);
              } else if (payload.kind === "deck") {
                await moveDeckCardBetweenZones(payload, zone.dataset.zone);
              }
            } catch (err) {
              showError(err.message);
            }
          });
        });

        ["dragover", "dragleave", "drop"].forEach((eventName) => {
          binderPanel.addEventListener(eventName, async (event) => {
            if (eventName === "dragover") {
              event.preventDefault();
              binderPanel.classList.add("drop-active");
              return;
            }
            if (eventName === "dragleave") {
              if (!binderPanel.contains(event.relatedTarget)) {
                binderPanel.classList.remove("drop-active");
              }
              return;
            }
            event.preventDefault();
            binderPanel.classList.remove("drop-active");
            const payload = JSON.parse(event.dataTransfer.getData("application/json") || "{}");
            try {
              await removeDeckCardToBinder(payload);
            } catch (err) {
              showError(err.message);
            }
          });
        });
      }

      render();
      if (isEditorDirty()) {
        refreshEditorData().catch(() => {});
      }
      window.setInterval(() => {
        if (isEditorDirty()) {
          refreshEditorData().catch(() => {});
        }
      }, 900);
    </script>
    """.replace("__PAYLOAD__", json.dumps(payload))
    components.html(html, height=1080, scrolling=False)


def render_collection_component(player_id: int, inventory_cards: list[dict]) -> None:
    payload = {
        "apiUrl": API_URL,
        "playerId": player_id,
        "inventory": [editor_card_payload(card) | {
            "inventory_id": card["inventory_id"],
            "desc": card.get("desc") or "",
            "race": card.get("race") or "",
            "archetype": card.get("archetype") or "",
            "sell_price": card["sell_price"],
        } for card in inventory_cards],
    }
    html = """
    <div id="collection-root"></div>
    <style>
      * { box-sizing: border-box; }
      body {
        color: #e5e7eb;
        font-family: "Inter", "Segoe UI", Arial, sans-serif;
        margin: 0;
      }
      .collection-shell {
        background:
          radial-gradient(circle at top left, rgba(20, 184, 166, 0.16), transparent 34%),
          linear-gradient(135deg, #090d18 0%, #111827 58%, #0b1020 100%);
        border: 1px solid rgba(148, 163, 184, 0.55);
        border-radius: 10px;
        min-height: 820px;
        padding: 14px;
      }
      .collection-head {
        align-items: center;
        display: grid;
        gap: 12px;
        grid-template-columns: 1fr auto;
        margin-bottom: 12px;
      }
      .collection-title {
        font-size: 20px;
        font-weight: 850;
        letter-spacing: 0.02em;
      }
      .collection-subtitle {
        color: #94a3b8;
        font-size: 12px;
        margin-top: 2px;
      }
      .collection-controls {
        align-items: center;
        display: grid;
        gap: 10px;
        grid-template-columns: minmax(260px, 420px) minmax(180px, 220px) auto auto;
      }
      .collection-search {
        background: #020617;
        border: 1px solid rgba(148, 163, 184, 0.72);
        border-radius: 6px;
        color: #e5e7eb;
        height: 36px;
        padding: 0 11px;
        width: 100%;
      }
      .collection-filter {
        background: #020617;
        border: 1px solid rgba(148, 163, 184, 0.72);
        border-radius: 6px;
        color: #e5e7eb;
        height: 36px;
        padding: 0 11px;
        width: 100%;
      }
      .collection-page {
        color: #cbd5e1;
        font-size: 12px;
        min-width: 142px;
        text-align: right;
      }
      .collection-buttons {
        display: flex;
        gap: 6px;
      }
      .collection-button {
        background: #0f172a;
        border: 1px solid rgba(148, 163, 184, 0.75);
        border-radius: 5px;
        color: #e5e7eb;
        cursor: pointer;
        height: 30px;
        min-width: 38px;
      }
      .collection-button:disabled {
        cursor: default;
        opacity: 0.45;
      }
      .collection-grid {
        align-content: start;
        display: grid;
        gap: 12px;
        grid-template-columns: repeat(auto-fit, minmax(102px, 1fr));
        justify-items: center;
        min-height: 680px;
      }
      .collection-card {
        background: rgba(15, 23, 42, 0.7);
        border: 0;
        border-radius: 7px;
        cursor: pointer;
        min-width: 0;
        max-width: 124px;
        padding: 4px;
        position: relative;
        width: 100%;
      }
      .collection-card:hover {
        box-shadow: 0 10px 30px rgba(0,0,0,0.28);
      }
      .collection-hover-preview {
        background: rgba(2, 6, 23, 0.92);
        border: 1px solid rgba(147, 197, 253, 0.8);
        border-radius: 8px;
        box-shadow: 0 18px 42px rgba(0,0,0,0.45);
        display: none;
        max-height: calc(100vh - 24px);
        padding: 6px;
        pointer-events: none;
        position: fixed;
        width: min(340px, 26vw);
        z-index: 9999;
      }
      .collection-hover-preview img {
        border-radius: 4px;
        display: block;
        max-height: calc(100vh - 36px);
        object-fit: contain;
        width: 100%;
      }
      .collection-img {
        aspect-ratio: 421 / 614;
        border-radius: 5px;
        display: block;
        object-fit: cover;
        width: 100%;
      }
      .collection-badge {
        background: rgba(2, 6, 23, 0.88);
        border: 1px solid rgba(255,255,255,0.35);
        border-radius: 999px;
        color: #f8fafc;
        font-size: 11px;
        font-weight: 850;
        padding: 2px 6px;
        position: absolute;
        right: 10px;
        top: 10px;
      }
      @media (max-width: 1180px) {
        .collection-controls {
          grid-template-columns: minmax(220px, 1fr) minmax(150px, 190px) auto auto;
        }
        .collection-grid {
          grid-template-columns: repeat(auto-fit, minmax(98px, 1fr));
        }
      }
      @media (max-width: 860px) {
        .collection-head {
          grid-template-columns: 1fr;
        }
        .collection-controls {
          grid-template-columns: 1fr 180px auto auto;
        }
        .collection-grid {
          grid-template-columns: repeat(auto-fit, minmax(92px, 1fr));
        }
      }
      @media (max-width: 640px) {
        .collection-controls {
          grid-template-columns: 1fr 1fr;
        }
        .collection-page {
          min-width: 0;
          text-align: left;
        }
      }
      .rarity-common { color: #cbd5e1; }
      .rarity-rare { color: #7dd3fc; }
      .rarity-super { color: #facc15; }
      .rarity-ultra { color: #fb923c; }
      .rarity-secret { color: #f0abfc; }
      .collection-modal-backdrop {
        align-items: center;
        background: rgba(2, 6, 23, 0.72);
        display: none;
        inset: 0;
        justify-content: center;
        position: fixed;
        z-index: 9999;
      }
      .collection-modal {
        background: #0f172a;
        border: 1px solid rgba(147, 197, 253, 0.65);
        border-radius: 10px;
        display: grid;
        gap: 18px;
        grid-template-columns: 290px minmax(320px, 520px);
        max-width: 860px;
        padding: 16px;
      }
      .modal-img {
        border-radius: 7px;
        width: 100%;
      }
      .modal-title {
        font-size: 22px;
        font-weight: 850;
        line-height: 1.1;
        margin-bottom: 8px;
      }
      .modal-meta {
        color: #93c5fd;
        font-size: 13px;
        line-height: 1.45;
        margin-bottom: 12px;
      }
      .modal-desc {
        color: #dbeafe;
        font-size: 13px;
        line-height: 1.45;
        max-height: 260px;
        overflow-y: auto;
        padding-right: 8px;
      }
      .modal-actions {
        display: flex;
        gap: 8px;
        margin-top: 16px;
      }
      .sell-button, .close-button {
        border: 0;
        border-radius: 6px;
        color: white;
        cursor: pointer;
        font-weight: 800;
        height: 36px;
        padding: 0 14px;
      }
      .sell-button { background: #b45309; }
      .close-button { background: #334155; }
      .collection-toast {
        background: #450a0a;
        border: 1px solid #fca5a5;
        border-radius: 6px;
        color: #fee2e2;
        display: none;
        font-size: 13px;
        margin-bottom: 10px;
        padding: 8px;
      }
    </style>
    <script>
      let data = __PAYLOAD__;
      let currentFilter = "";
      let currentCollectionFilterMode = "all";
      let currentPage = 0;
      const root = document.getElementById("collection-root");
      const DIRTY_FLAG_KEY = "ygo_editor_dirty";
      let lastRefreshAt = 0;

      function esc(value) {
        return String(value ?? "").replace(/[&<>"']/g, (char) => ({
          "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
        }[char]));
      }

      function rarityClass(rarity) {
        const value = String(rarity || "").toLowerCase();
        if (value.includes("secret")) return "rarity-secret";
        if (value.includes("ultra")) return "rarity-ultra";
        if (value.includes("super")) return "rarity-super";
        if (value.includes("rare")) return "rarity-rare";
        return "rarity-common";
      }

      function normalizedImageUrl(imageUrl) {
        if (!imageUrl) return "";
        return imageUrl.startsWith("/") ? `${data.apiUrl}${imageUrl}` : imageUrl;
      }

      function sortCategory(cardType) {
        const type = cardType || "";
        if (type.includes("Spell")) return 1;
        if (type.includes("Trap")) return 2;
        if (["Fusion", "Synchro", "Xyz", "Link"].some((extraType) => type.includes(extraType))) return 3;
        return 0;
      }

      function normalizeCollectionCard(card) {
        return {
          ...card,
          type: card.type || "",
          rarity: card.rarity || "Common",
          archetype: card.archetype || "",
          desc: card.desc || "",
          race: card.race || "",
          sort_category: card.sort_category ?? sortCategory(card.type),
          image_url: normalizedImageUrl(card.image_url)
        };
      }

      function isDirty() {
        try {
          return window.localStorage.getItem(DIRTY_FLAG_KEY) === "1";
        } catch (err) {
          return false;
        }
      }

      async function refreshCollectionData() {
        const now = Date.now();
        if (now - lastRefreshAt < 1500) return;
        lastRefreshAt = now;
        const response = await fetch(`${data.apiUrl}/players/${data.playerId}/inventory`);
        if (!response.ok) return;
        data.inventory = (await response.json()).map(normalizeCollectionCard);
        try { window.localStorage.removeItem(DIRTY_FLAG_KEY); } catch (err) {}
        render();
      }

      function passesCollectionFilter(card) {
        if (currentCollectionFilterMode === "not_in_deck") {
          return Number(card.available_quantity || 0) === Number(card.quantity || 0);
        }
        if (currentCollectionFilterMode === "in_deck") {
          return Number(card.available_quantity || 0) < Number(card.quantity || 0);
        }
        return true;
      }

      function collectionPageSize() {
        const viewportWidth = Math.max(window.innerWidth || 0, document.documentElement?.clientWidth || 0, 960);
        let minCardWidth = 96;
        if (viewportWidth <= 860) {
          minCardWidth = 88;
        } else if (viewportWidth <= 1180) {
          minCardWidth = 92;
        }
        const shellPadding = 80;
        const usableWidth = Math.max(320, viewportWidth - shellPadding);
        const columns = Math.max(1, Math.floor(usableWidth / (minCardWidth + 12)));
        return Math.max(columns * 4, 24);
      }

      function filteredInventory() {
        const needle = currentFilter.trim().toLowerCase();
        return data.inventory
          .filter((card) => passesCollectionFilter(card))
          .filter((card) =>
            !needle || card.name.toLowerCase().includes(needle) ||
            card.type.toLowerCase().includes(needle) ||
            card.rarity.toLowerCase().includes(needle) ||
            card.archetype.toLowerCase().includes(needle)
          )
          .sort((left, right) =>
            Number(left.sort_category ?? 0) - Number(right.sort_category ?? 0) ||
            left.name.localeCompare(right.name)
          );
      }

      async function sellCard(inventoryId) {
        const response = await fetch(`${data.apiUrl}/players/${data.playerId}/inventory/${inventoryId}/sell`, {
          method: "POST"
        });
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload.detail || "Nao foi possivel vender a carta.");
        }
      }

      function showError(message) {
        const toast = document.querySelector(".collection-toast");
        toast.textContent = message;
        toast.style.background = "#450a0a";
        toast.style.borderColor = "#fca5a5";
        toast.style.color = "#fee2e2";
        toast.style.display = "block";
        setTimeout(() => { toast.style.display = "none"; }, 3500);
      }

      function showSuccess(message) {
        const toast = document.querySelector(".collection-toast");
        toast.textContent = message;
        toast.style.background = "#064e3b";
        toast.style.borderColor = "#34d399";
        toast.style.color = "#d1fae5";
        toast.style.display = "block";
      }

      function markEditorDirty() {
        try { window.localStorage.setItem("ygo_editor_dirty", "1"); } catch (err) {}
      }

      function positionPreview(preview, item) {
        const rect = item.getBoundingClientRect();
        const previewWidth = preview.offsetWidth || 340;
        const previewHeight = preview.offsetHeight || Math.floor(previewWidth * 1.46);
        const gutter = 12;
        const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
        const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
        let left = rect.right + gutter;
        if (left + previewWidth > viewportWidth - 8) left = rect.left - previewWidth - gutter;
        if (left < 8) left = Math.max(8, Math.min(viewportWidth - previewWidth - 8, rect.left + gutter));
        let top = rect.top + (rect.height / 2) - (previewHeight / 2);
        top = Math.max(8, Math.min(top, viewportHeight - previewHeight - 8));
        preview.style.left = `${left}px`;
        preview.style.top = `${top}px`;
      }

      function cardHtml(card) {
        return `
          <article class="collection-card" data-card-id="${card.card_id}">
            <img class="collection-img" src="${esc(card.image_url)}" alt="${esc(card.name)}">
            <div class="collection-badge">${card.available_quantity}/${card.quantity}</div>
          </article>
        `;
      }

      function openModal(card) {
        const modal = document.querySelector(".collection-modal-backdrop");
        modal.innerHTML = `
          <div class="collection-modal">
            <img class="modal-img" src="${esc(card.image_url)}" alt="${esc(card.name)}">
            <div>
              <div class="modal-title">${esc(card.name)}</div>
              <div class="modal-meta">
                ${esc(card.type)}<br>
                ${card.race ? `Raca: ${esc(card.race)}<br>` : ""}
                ${card.archetype ? `Arquetipo: ${esc(card.archetype)}<br>` : ""}
                Raridade: ${esc(card.rarity)}<br>
                Copias: ${card.available_quantity}/${card.quantity} livres
              </div>
              <div class="modal-desc">${esc(card.desc)}</div>
              <div class="modal-actions">
                <button class="sell-button">Vender por ${card.sell_price}g</button>
                <button class="close-button">Fechar</button>
              </div>
            </div>
          </div>
        `;
        modal.style.display = "flex";
        modal.querySelector(".close-button").addEventListener("click", closeModal);
        modal.addEventListener("click", (event) => {
          if (event.target === modal) closeModal();
        }, { once: true });
        modal.querySelector(".sell-button").addEventListener("click", async () => {
          try {
            await sellCard(card.inventory_id);
            card.quantity = Math.max(0, Number(card.quantity) - 1);
            card.available_quantity = Math.max(0, Number(card.available_quantity) - 1);
            if (Number(card.quantity) <= 0) {
              data.inventory = data.inventory.filter((item) => Number(item.inventory_id) !== Number(card.inventory_id));
            }
            markEditorDirty();
            closeModal();
            render();
            showSuccess("Carta vendida.");
          } catch (err) {
            showError(err.message);
          }
        });
      }

      function closeModal() {
        const modal = document.querySelector(".collection-modal-backdrop");
        modal.style.display = "none";
      }

      function render() {
        const inventory = filteredInventory().filter((card) => Number(card.quantity) > 0);
        const pageSize = collectionPageSize();
        const pageCount = Math.max(1, Math.ceil(inventory.length / pageSize));
        currentPage = Math.min(Math.max(currentPage, 0), pageCount - 1);
        const pageStart = currentPage * pageSize;
        const pageInventory = inventory.slice(pageStart, pageStart + pageSize);

        root.innerHTML = `
          <section class="collection-shell">
            <div class="collection-modal-backdrop"></div>
            <div class="collection-hover-preview"><img alt=""></div>
            <div class="collection-toast"></div>
            <div class="collection-head">
              <div>
                <div class="collection-title">Colecao</div>
                <div class="collection-subtitle">Ordenada por monstros, magias, traps e Extra Deck</div>
              </div>
              <div class="collection-controls">
                <input class="collection-search" value="${esc(currentFilter)}" placeholder="Buscar carta, tipo, raridade ou arquetipo">
                <select class="collection-filter">
                  <option value="all" ${currentCollectionFilterMode === "all" ? "selected" : ""}>Todas</option>
                  <option value="not_in_deck" ${currentCollectionFilterMode === "not_in_deck" ? "selected" : ""}>Fora do deck</option>
                  <option value="in_deck" ${currentCollectionFilterMode === "in_deck" ? "selected" : ""}>Em uso no deck</option>
                </select>
                <div class="collection-page">
                  ${inventory.length ? pageStart + 1 : 0}-${Math.min(pageStart + pageSize, inventory.length)} de ${inventory.length}<br>
                  Pagina ${currentPage + 1}/${pageCount}
                </div>
                <div class="collection-buttons">
                  <button class="collection-button" data-page-delta="-1" ${currentPage <= 0 ? "disabled" : ""}>‹</button>
                  <button class="collection-button" data-page-delta="1" ${currentPage >= pageCount - 1 ? "disabled" : ""}>›</button>
                </div>
              </div>
            </div>
            <div class="collection-grid">${pageInventory.map(cardHtml).join("")}</div>
          </section>
        `;

        const search = document.querySelector(".collection-search");
        search.focus();
        search.setSelectionRange(search.value.length, search.value.length);
        search.addEventListener("input", (event) => {
          currentFilter = event.target.value;
          currentPage = 0;
          render();
        });
        document.querySelector(".collection-filter").addEventListener("change", (event) => {
          currentCollectionFilterMode = event.target.value;
          currentPage = 0;
          render();
        });
        document.querySelectorAll("[data-page-delta]").forEach((button) => {
          button.addEventListener("click", () => {
            currentPage += Number(button.dataset.pageDelta);
            render();
          });
        });
        const grid = document.querySelector(".collection-grid");
        grid.addEventListener("wheel", (event) => {
          event.preventDefault();
          currentPage += event.deltaY > 0 ? 1 : -1;
          render();
        }, { passive: false });
        document.querySelectorAll(".collection-card").forEach((cardEl) => {
          cardEl.addEventListener("mouseenter", () => {
            const image = cardEl.querySelector(".collection-img");
            const preview = document.querySelector(".collection-hover-preview");
            if (!image || !preview) return;
            preview.querySelector("img").src = image.src;
            preview.querySelector("img").alt = image.alt;
            preview.style.display = "block";
            positionPreview(preview, cardEl);
          });
          cardEl.addEventListener("mousemove", () => {
            const preview = document.querySelector(".collection-hover-preview");
            if (!preview || preview.style.display !== "block") return;
            positionPreview(preview, cardEl);
          });
          cardEl.addEventListener("mouseleave", () => {
            const preview = document.querySelector(".collection-hover-preview");
            if (preview) preview.style.display = "none";
          });
          cardEl.addEventListener("click", () => {
            const card = data.inventory.find((item) => Number(item.card_id) === Number(cardEl.dataset.cardId));
            if (card) openModal(card);
          });
        });
      }

      render();
      if (isDirty()) {
        refreshCollectionData().catch(() => {});
      }
      window.setInterval(() => {
        if (isDirty()) {
          refreshCollectionData().catch(() => {});
        }
      }, 900);
    </script>
    """.replace("__PAYLOAD__", json.dumps(payload))
    components.html(html, height=880, scrolling=False)


def render_shop_component(player_id: int, player_gold: float, shop: dict) -> None:
    payload = {
        "apiUrl": API_URL,
        "playerId": player_id,
        "playerGold": player_gold,
        "cards": [editor_card_payload(card) | {
            "price": card["price"],
            "set_code": card.get("set_code") or "",
            "rarity": card["rarity"],
        } for card in shop["cards"]],
    }
    html = """
    <div id="shop-root"></div>
    <style>
      * { box-sizing: border-box; }
      body { color:#e5e7eb; font-family:Inter, Segoe UI, Arial, sans-serif; margin:0; }
      .shop-shell { background:linear-gradient(135deg,#090d18,#111827 58%,#0b1020); border:1px solid rgba(148,163,184,.55); border-radius:10px; padding:14px; min-height:760px; }
      .shop-top { display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; }
      .shop-gold { color:#facc15; font-weight:900; }
      .rarity-title { color:#f8fafc; font-size:18px; font-weight:850; margin:18px 0 10px; }
      .shop-grid { display:grid; grid-template-columns:repeat(12,minmax(0,1fr)); gap:8px; }
      .shop-card { background:rgba(15,23,42,.72); border:1px solid rgba(148,163,184,.28); border-radius:7px; padding:5px; min-width:0; position:relative; }
      .shop-card:hover { border-color:rgba(56,189,248,.9); box-shadow:0 10px 30px rgba(0,0,0,.28); }
      .shop-card.recent-buy { border-color:#34d399; box-shadow:0 0 0 1px rgba(52,211,153,.5), 0 12px 30px rgba(6,78,59,.35); }
      .shop-img { width:100%; aspect-ratio:421/614; object-fit:cover; border-radius:5px; display:block; }
      .shop-name { color:#f8fafc; font-size:10px; font-weight:750; line-height:1.1; min-height:22px; margin-top:4px; }
      .shop-code { color:#93c5fd; font-size:9px; margin-top:2px; }
      .shop-hover-preview {
        background: rgba(2, 6, 23, 0.92);
        border: 1px solid rgba(147, 197, 253, 0.8);
        border-radius: 8px;
        box-shadow: 0 18px 42px rgba(0,0,0,0.45);
        display: none;
        max-height: calc(100vh - 24px);
        padding: 6px;
        pointer-events: none;
        position: fixed;
        width: min(340px, 26vw);
        z-index: 9999;
      }
      .shop-hover-preview img {
        border-radius: 4px;
        display: block;
        max-height: calc(100vh - 36px);
        object-fit: contain;
        width: 100%;
      }
      .shop-hover-preview-title { display:none; }
      .buy-button { width:100%; height:22px; margin-top:4px; border:0; border-radius:4px; background:#b45309; color:white; font-size:10px; font-weight:850; cursor:pointer; padding:0 4px; }
      .buy-button:disabled { opacity:.45; cursor:not-allowed; }
      .buy-button.recent-buy { animation:buyPulse .7s ease; background:#059669; }
      @media (max-width: 1400px) { .shop-grid { grid-template-columns:repeat(10,minmax(0,1fr)); } }
      @media (max-width: 1180px) { .shop-grid { grid-template-columns:repeat(8,minmax(0,1fr)); } }
      @media (max-width: 900px) { .shop-grid { grid-template-columns:repeat(6,minmax(0,1fr)); } }
      @media (max-width: 680px) { .shop-grid { grid-template-columns:repeat(4,minmax(0,1fr)); } }
      @keyframes buyPulse {
        0% { transform:scale(1); box-shadow:0 0 0 rgba(52,211,153,0); }
        35% { transform:scale(1.04); box-shadow:0 0 0 5px rgba(52,211,153,.22); }
        100% { transform:scale(1); box-shadow:0 0 0 rgba(52,211,153,0); }
      }
      .toast { display:none; margin-bottom:10px; padding:8px; border-radius:6px; background:#450a0a; border:1px solid #fca5a5; color:#fee2e2; font-size:13px; }
    </style>
    <script>
      let data = __PAYLOAD__;
      const root = document.getElementById("shop-root");
      const rarityOrder = ["Common", "Rare", "Super Rare", "Ultra Rare", "Secret Rare", "Demais raridades"];
      let recentBoughtCardId = null;
      function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
      function fmtGold(v){v=Number(v||0); return Number.isInteger(v) ? String(v) : v.toFixed(1);}
      function positionPreview(preview, item){
        const rect = item.getBoundingClientRect();
        const previewWidth = preview.offsetWidth || 340;
        const previewHeight = preview.offsetHeight || Math.floor(previewWidth * 1.46);
        const gutter = 12;
        const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
        const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
        let left = rect.right + gutter;
        if (left + previewWidth > viewportWidth - 8) left = rect.left - previewWidth - gutter;
        if (left < 8) left = Math.max(8, Math.min(viewportWidth - previewWidth - 8, rect.left + gutter));
        let top = rect.top + (rect.height / 2) - (previewHeight / 2);
        top = Math.max(8, Math.min(top, viewportHeight - previewHeight - 8));
        preview.style.left = `${left}px`;
        preview.style.top = `${top}px`;
      }
      function typeSort(card){
        const t = card.type || "";
        if (t.includes("Spell")) return 1;
        if (t.includes("Trap")) return 2;
        if (["Fusion","Synchro","Xyz","Link"].some(x=>t.includes(x))) return 3;
        return 0;
      }
      function showError(msg){const t=document.querySelector(".toast"); t.textContent=msg; t.style.background="#450a0a"; t.style.borderColor="#fca5a5"; t.style.color="#fee2e2"; t.style.display="block"; setTimeout(()=>t.style.display="none",3000);}
      function showSuccess(msg){const t=document.querySelector(".toast"); t.textContent=msg; t.style.background="#064e3b"; t.style.borderColor="#34d399"; t.style.color="#d1fae5"; t.style.display="block";}
      function markEditorDirty(){try{window.localStorage.setItem("ygo_editor_dirty","1");}catch(err){}}
      async function buy(card){
        const res = await fetch(`${data.apiUrl}/players/${data.playerId}/shop/buy`, {
          method:"POST", headers:{"Content-Type":"application/json"},
          body:JSON.stringify({card_id:card.card_id, rarity:card.rarity})
        });
        const payload = await res.json().catch(()=>({}));
        if(!res.ok) throw new Error(payload.detail || "Nao foi possivel comprar.");
        data.playerGold = payload.player_gold;
      }
      function cardHtml(card){
        const disabled = Number(data.playerGold) < Number(card.price);
        const recent = Number(recentBoughtCardId) === Number(card.card_id);
        return `<article class="shop-card ${recent ? "recent-buy" : ""}">
          <img class="shop-img" src="${esc(card.image_url)}" alt="${esc(card.name)}">
          <div class="shop-name">${esc(card.name)}</div>
          <div class="shop-code">${esc(card.set_code)}</div>
          <button class="buy-button ${recent ? "recent-buy" : ""}" data-card="${card.card_id}" ${disabled?"disabled":""}>${recent ? "Comprado" : `Comprar ${card.price}g`}</button>
        </article>`;
      }
      function render(){
        const groups = {};
        rarityOrder.forEach(r=>groups[r]=[]);
        data.cards.forEach(card => (groups[groups[card.rarity] ? card.rarity : "Demais raridades"]).push(card));
        root.innerHTML = `<section class="shop-shell"><div class="shop-hover-preview"><img alt=""><div class="shop-hover-preview-title"></div></div><div class="toast"></div><div class="shop-top"><strong>Loja</strong><span class="shop-gold">${fmtGold(data.playerGold)}g</span></div>${
          rarityOrder.map(r=>{
            const cards=(groups[r]||[]).sort((a,b)=>typeSort(a)-typeSort(b)||a.name.localeCompare(b.name));
            if(!cards.length) return "";
            return `<div class="rarity-title">${r} - ${cards[0].price}g</div><div class="shop-grid">${cards.map(cardHtml).join("")}</div>`;
          }).join("")
        }</section>`;
        document.querySelectorAll(".shop-card").forEach(cardEl=>{
          cardEl.addEventListener("mouseenter", ()=>{
            const image = cardEl.querySelector(".shop-img");
            const preview = document.querySelector(".shop-hover-preview");
            if(!image || !preview) return;
            preview.querySelector("img").src = image.src;
            preview.querySelector("img").alt = image.alt;
            preview.style.display = "block";
            positionPreview(preview, cardEl);
          });
          cardEl.addEventListener("mousemove", ()=>{
            const preview = document.querySelector(".shop-hover-preview");
            if(!preview || preview.style.display !== "block") return;
            positionPreview(preview, cardEl);
          });
          cardEl.addEventListener("mouseleave", ()=>{
            const preview = document.querySelector(".shop-hover-preview");
            if(preview) preview.style.display = "none";
          });
        });
        document.querySelectorAll("[data-card]").forEach(btn=>{
          btn.addEventListener("click", async ()=>{
            const card = data.cards.find(c=>Number(c.card_id)===Number(btn.dataset.card));
            try {
              await buy(card);
              markEditorDirty();
              recentBoughtCardId = card.card_id;
              render();
              window.setTimeout(()=>{
                if(Number(recentBoughtCardId)===Number(card.card_id)){
                  recentBoughtCardId = null;
                  render();
                }
              }, 950);
            } catch(err){ showError(err.message); }
          });
        });
      }
      render();
    </script>
    """.replace("__PAYLOAD__", json.dumps(payload))
    components.html(html, height=820, scrolling=True)


def render_banlist_component(player_id: int) -> None:
    payload = {"apiUrl": API_URL, "playerId": player_id}
    html = """
    <div id="banlist-root"></div>
    <style>
      * { box-sizing:border-box; }
      body { margin:0; color:#e5e7eb; font-family:Inter, Segoe UI, Arial, sans-serif; }
      .ban-shell { background:linear-gradient(135deg,#090d18,#111827 58%,#0b1020); border:1px solid rgba(148,163,184,.55); border-radius:10px; padding:14px; min-height:680px; }
      .search-row { display:flex; gap:8px; margin-bottom:12px; }
      .search { flex:1; height:36px; background:#020617; border:1px solid rgba(148,163,184,.72); border-radius:6px; color:#e5e7eb; padding:0 11px; }
      .action { height:36px; border:0; border-radius:6px; background:#b91c1c; color:white; font-weight:850; padding:0 14px; cursor:pointer; }
      .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(86px,1fr)); gap:10px; margin-bottom:18px; }
      .card { position:relative; background:rgba(15,23,42,.72); border:1px solid rgba(148,163,184,.28); border-radius:7px; padding:6px; cursor:pointer; }
      .card:hover { border-color:rgba(248,113,113,.95); box-shadow:0 10px 30px rgba(0,0,0,.28); }
      .img { width:100%; aspect-ratio:421/614; border-radius:5px; object-fit:cover; display:block; }
      .name { font-size:10px; line-height:1.1; margin-top:5px; min-height:22px; color:#f8fafc; }
      .badge { position:absolute; left:1px; top:1px; width:26px; height:26px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:white; font-weight:900; font-size:18px; box-shadow:0 0 0 2px #020617; }
      .limited { background:#b45309; }
      .banned { background:#991b1b; }
      .section-title { font-weight:850; margin:12px 0 10px; }
      .toast { display:none; margin-bottom:10px; padding:8px; border-radius:6px; background:#450a0a; border:1px solid #fca5a5; color:#fee2e2; font-size:13px; }
    </style>
    <script>
      const data = __PAYLOAD__;
      const root = document.getElementById("banlist-root");
      let results = [];
      let restrictions = [];
      function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
      function imgUrl(url){return url && url.startsWith("/") ? `${data.apiUrl}${url}` : (url || "");}
      function badge(status){ if(!status) return ""; return `<div class="badge ${status}">${status==="banned"?"⊘":"1"}</div>`; }
      function showError(msg){const t=document.querySelector(".toast"); t.textContent=msg; t.style.display="block"; setTimeout(()=>t.style.display="none",3000);}
      async function loadRestrictions(){
        const res = await fetch(`${data.apiUrl}/players/${data.playerId}/restrictions`);
        restrictions = await res.json();
      }
      async function search(q){
        if(!q.trim()){results=[]; render(); return;}
        const res = await fetch(`${data.apiUrl}/players/${data.playerId}/card-search?q=${encodeURIComponent(q.trim())}`);
        if(!res.ok) throw new Error("Busca falhou.");
        results = await res.json();
        render();
      }
      async function restrict(cardId){
        const res = await fetch(`${data.apiUrl}/players/${data.playerId}/restrictions`, {
          method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({card_id:Number(cardId)})
        });
        if(!res.ok){const p=await res.json().catch(()=>({})); throw new Error(p.detail||"Nao foi possivel alterar.");}
        restrictions = await res.json();
        render();
      }
      function resultCard(card){return `<article class="card" data-restrict="${card.card_id}"><img class="img" src="${esc(imgUrl(card.image_url))}"><div class="name">${esc(card.name)}</div></article>`;}
      function restrictionCard(card){return `<article class="card"><img class="img" src="${esc(imgUrl(card.image_url))}">${badge(card.status)}</article>`;}
      function render(){
        root.innerHTML = `<section class="ban-shell"><div class="toast"></div><div class="search-row"><input class="search" placeholder="Pesquisar carta"><button class="action">Buscar</button></div><div class="grid">${results.map(resultCard).join("")}</div><div class="section-title">Cartas limitadas e banidas</div><div class="grid">${restrictions.map(restrictionCard).join("")}</div></section>`;
        const input=document.querySelector(".search");
        document.querySelector(".action").addEventListener("click",()=>search(input.value).catch(e=>showError(e.message)));
        input.addEventListener("keydown",e=>{if(e.key==="Enter") search(input.value).catch(err=>showError(err.message));});
        document.querySelectorAll("[data-restrict]").forEach(el=>el.addEventListener("click",()=>restrict(el.dataset.restrict).catch(e=>showError(e.message))));
      }
      loadRestrictions().then(render).catch(e=>{render(); showError(e.message);});
    </script>
    """.replace("__PAYLOAD__", json.dumps(payload))
    components.html(html, height=740, scrolling=True)


editor_tab, collection_tab, shop_tab, year_pick_tab, banlist_tab = st.tabs(
    ["Editor de Deck", "Colecao", "Loja", "Pick Anual", "Banlist"]
)

with editor_tab:
    deck_options = saved_decks.get("decks", [])
    active_deck_id = saved_decks.get("active_deck_id")
    active_deck = next((item for item in deck_options if item["id"] == active_deck_id), None)
    active_deck_name = deck.get("active_deck_name") or (active_deck["name"] if active_deck else "Deck Principal")

    manager_cols = st.columns([3.4, 2.2, 2.4], vertical_alignment="bottom")
    deck_ids = [item["id"] for item in deck_options]
    deck_labels = {item["id"]: item["name"] for item in deck_options}
    if active_deck_id in deck_ids:
        selected_index = deck_ids.index(active_deck_id)
    else:
        selected_index = 0

    selected_deck_id = manager_cols[0].selectbox(
        "Deck ativo",
        deck_ids,
        index=selected_index,
        format_func=lambda deck_id: deck_labels.get(deck_id, f"Deck {deck_id}"),
        key=f"active-deck-select-{player['id']}",
    )
    if selected_deck_id != active_deck_id:
        try:
            api_post(f"/players/{player['id']}/decks/{selected_deck_id}/activate")
            st.rerun()
        except requests.HTTPError as exc:
            st.error(error_message(exc))

    with manager_cols[1].form(f"rename-deck-{player['id']}"):
        renamed_deck = st.text_input("Renomear deck ativo", value=active_deck_name)
        rename_submitted = st.form_submit_button("Salvar nome")
        if rename_submitted:
            try:
                api_patch(
                    f"/players/{player['id']}/decks/{active_deck_id}",
                    json={"name": renamed_deck},
                )
                st.success("Nome do deck atualizado.")
                st.rerun()
            except requests.HTTPError as exc:
                st.error(error_message(exc))

    with manager_cols[2].form(f"create-deck-{player['id']}"):
        new_deck_name = st.text_input("Novo deck", placeholder="Ex.: Chaos Control")
        copy_active_deck = st.checkbox("Duplicar deck atual", value=False)
        create_submitted = st.form_submit_button("Criar e abrir")
        if create_submitted:
            try:
                api_post(
                    f"/players/{player['id']}/decks",
                    json={"name": new_deck_name, "copy_active_deck": copy_active_deck},
                )
                st.success("Novo deck criado.")
                st.rerun()
            except requests.HTTPError as exc:
                st.error(error_message(exc))

    st.caption(f"Editando agora: {active_deck_name}")
    if not inventory:
        st.info("Inventario vazio. Importe um .ydk para popular o binder inicial.")
    render_deck_editor_component(player["id"], deck, inventory)

with collection_tab:
    render_collection_component(player["id"], inventory)

with shop_tab:
    current_shop_collection = current_collection["set_name"] if current_collection else "Passe a primeira rodada para abrir LOB"
    st.caption(f"Colecao atual: {current_shop_collection}")
    if not current_collection:
        st.info("Passe a primeira rodada para liberar a primeira colecao da loja.")
    elif year_pick.get("pending"):
        st.warning(f"Resolva primeiro o pick anual de {year_pick['year']} para liberar a loja.")
    else:
        try:
            shop = api_get(f"/players/{player['id']}/shop")
        except requests.HTTPError as exc:
            st.error(f"Erro ao carregar loja: {error_message(exc)}")
            st.stop()
        render_shop_component(player["id"], player["gold"], shop)

with year_pick_tab:
    render_year_pick_tab(player["id"], year_pick)

with banlist_tab:
    st.caption("Clique em uma carta para limitar. Clique de novo para banir.")
    render_banlist_component(player["id"])
