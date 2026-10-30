"""Talks to the Java backend over a local HTTP connection (standard library only)."""
import json
import urllib.error
import urllib.parse
import urllib.request


class ApiError(Exception):
    """The backend refused a request; the message is safe to show to the user."""


class Api:
    def __init__(self, port):
        self.base = f"http://127.0.0.1:{port}"
        # never use a system proxy for the local backend
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def _call(self, method, path, data=None, timeout=10):
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(self.base + path, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        try:
            with self._opener.open(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read().decode("utf-8")).get("error", "Request failed.")
            except Exception:
                msg = "Request failed."
            raise ApiError(msg)
        except (urllib.error.URLError, OSError, ValueError):
            raise ApiError("Cannot reach the program engine.")

    def health(self):
        return self._call("GET", "/health")

    def items(self):
        return self._call("GET", "/items")

    def search(self, text):
        return self._call("GET", "/search?q=" + urllib.parse.quote(text))

    def create(self, item):
        return self._call("POST", "/items", item)

    def update(self, item_id, item):
        return self._call("PUT", f"/items/{item_id}", item)

    def delete(self, item_id):
        return self._call("DELETE", f"/items/{item_id}")

    def sell_first(self):
        return self._call("POST", "/sell-first")

    def load_sample(self):
        return self._call("POST", "/sample")

    def sale(self, name, quantity):
        return self._call("POST", "/sale", {"name": name, "quantity": quantity})

    def stock_names(self):
        return self._call("GET", "/stock-names")["names"]

    def remove_expired(self):
        return self._call("POST", "/remove-expired")

    def history(self):
        return self._call("GET", "/history")

    def line(self):
        return self._call("GET", "/line")

    def join_line(self, name):
        return self._call("POST", "/line", {"name": name})

    def call_next(self):
        return self._call("POST", "/line/next")

    def benchmark(self):
        return self._call("GET", "/benchmark", timeout=120)
