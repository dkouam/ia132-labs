"""Lab 09 — Mini-API de liens courts (bibliothèque standard uniquement).

    python api.py              # http://localhost:8009

    POST /liens        {"url": "https://…"}   → 201 {"code", "url"}
    GET  /l/<code>                            → 302 vers l'URL
    GET  /stats/<code>                        → 200 {"code", "url", "clics"}
    GET  /sante                               → 200 {"statut": "ok"}
"""

import json
import secrets
import string
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ALPHABET = string.ascii_letters + string.digits
LONGUEUR_CODE = 6
TAILLE_MAX_URL = 2_048


def url_valide(url: object) -> bool:
    if not isinstance(url, str) or len(url) > TAILLE_MAX_URL:
        return False
    p = urlparse(url)
    return p.scheme in {"http", "https"} and bool(p.netloc)


def nouveau_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(LONGUEUR_CODE))


class Depot:
    """Stockage en mémoire, protégé par un verrou (le serveur est multithread)."""

    def __init__(self) -> None:
        self._liens: dict[str, dict] = {}
        self._verrou = threading.Lock()

    def creer(self, url: str) -> str:
        with self._verrou:
            code = nouveau_code()
            while code in self._liens:
                code = nouveau_code()
            self._liens[code] = {"url": url, "clics": 0}
            return code

    def visiter(self, code: str) -> str | None:
        with self._verrou:
            lien = self._liens.get(code)
            if lien is None:
                return None
            lien["clics"] += 1
            return lien["url"]

    def stats(self, code: str) -> dict | None:
        with self._verrou:
            lien = self._liens.get(code)
            return None if lien is None else {"code": code, **lien}


class Gestionnaire(BaseHTTPRequestHandler):
    depot: Depot  # injecté par creer_serveur()

    def log_message(self, *args) -> None:  # silencieux pendant les tests
        pass

    def _json(self, statut: int, corps: dict) -> None:
        donnees = json.dumps(corps, ensure_ascii=False).encode()
        self.send_response(statut)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(donnees)))
        self.end_headers()
        self.wfile.write(donnees)

    def do_GET(self) -> None:  # noqa: N802 (nom imposé par http.server)
        if self.path == "/sante":
            return self._json(200, {"statut": "ok"})
        if self.path.startswith("/l/"):
            url = self.depot.visiter(self.path[3:])
            if url is None:
                return self._json(404, {"erreur": "lien inconnu"})
            self.send_response(302)
            self.send_header("Location", url)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        if self.path.startswith("/stats/"):
            stats = self.depot.stats(self.path[7:])
            return self._json(200, stats) if stats else self._json(404, {"erreur": "lien inconnu"})
        return self._json(404, {"erreur": "route inconnue"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/liens":
            return self._json(404, {"erreur": "route inconnue"})
        try:
            longueur = int(self.headers.get("Content-Length", 0))
            corps = json.loads(self.rfile.read(longueur) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"erreur": "JSON invalide"})
        url = corps.get("url") if isinstance(corps, dict) else None
        if not url_valide(url):
            return self._json(400, {"erreur": "url invalide : http(s)://… attendu"})
        code = self.depot.creer(url)
        return self._json(201, {"code": code, "url": url})


def creer_serveur(port: int = 0) -> ThreadingHTTPServer:
    """Serveur prêt à démarrer ; port 0 = un port libre choisi par le système."""
    gestionnaire = type("G", (Gestionnaire,), {"depot": Depot()})
    return ThreadingHTTPServer(("127.0.0.1", port), gestionnaire)


if __name__ == "__main__":
    serveur = creer_serveur(8009)
    print("API de liens courts sur http://localhost:8009 (Ctrl+C pour arrêter)")
    serveur.serve_forever()
