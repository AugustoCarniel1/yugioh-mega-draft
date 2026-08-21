from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db import SessionLocal, init_db
from app.services.ygoprodeck import catalog_sync_status, sync_card_catalog, sync_collections


def main() -> int:
    init_db()
    with SessionLocal() as session:
        collection_count = sync_collections(session)
        print(f"Colecoes configuradas: {collection_count}")
        before = catalog_sync_status(session)
        print(
            f"Base antes: {before['synced_collections']}/{before['total_collections']} colecoes, "
            f"{before['cards']} cartas e {before['printings']} impressoes."
        )
        result = sync_card_catalog(session, retry_failed=True)
        after = catalog_sync_status(session)
        print(
            f"Sincronizacao concluida: {result['synced_collections']} colecoes, "
            f"{result['cards']} cartas processadas e {result['printings']} impressoes novas."
        )
        print(
            f"Base agora: {after['synced_collections']}/{after['total_collections']} colecoes, "
            f"{after['cards']} cartas e {after['printings']} impressoes."
        )
        if after.get("unavailable_collections"):
            print(
                f"{after['unavailable_collections']} colecao(oes) futura(s) ainda nao esta(ao) cadastrada(s) na YGOProDeck."
            )
        if result["errors"]:
            print("\nSets que falharam e poderao ser retomados ao executar este arquivo novamente:")
            for error in result["errors"]:
                print(f"- {error['set_name']}: {error['error']}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
