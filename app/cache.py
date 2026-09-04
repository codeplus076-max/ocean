import time

class TTLCache:
    def __init__(self, ttl_seconds: int = 1800):
        self.ttl = ttl_seconds
        self._store: dict = {}

    def get(self, key):
        item = self._store.get(key)
        if item and time.time() - item[0] < self.ttl:
            return item[1]
        return None

    def set(self, key, value):
        self._store[key] = (time.time(), value)

    def clear(self):
        self._store.clear()

cache = TTLCache(ttl_seconds=3600)