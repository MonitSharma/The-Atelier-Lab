from store import Store


def search(rows, query, limit=10):
    store = Store(rows)
    return store.find(query)[:limit]
