"""Tests d'intégration : un VRAI serveur HTTP, de vraies requêtes. À compléter (voir README).

La fixture `serveur` démarre l'API sur un port libre et l'arrête à la fin du module.
"""

import json
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import pytest

from api import creer_serveur


class SansRedirection(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # pour lire la réponse 302 elle-même


ouvrir = urllib.request.build_opener(SansRedirection).open


@pytest.fixture(scope="module")
def serveur():
    srv = creer_serveur()
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def requete(base, methode, chemin, corps=None):
    """Retourne (statut, en-têtes, corps JSON ou None) sans lever d'exception sur 4xx."""
    donnees = corps.encode() if isinstance(corps, str) else json.dumps(corps).encode() if corps is not None else None
    req = urllib.request.Request(base + chemin, data=donnees, method=methode, headers={"Content-Type": "application/json"})
    try:
        with ouvrir(req, timeout=5) as r:
            brut = r.read()
            return r.status, r.headers, json.loads(brut) if brut else None
    except urllib.error.HTTPError as e:
        brut = e.read()
        return e.code, e.headers, json.loads(brut) if brut else None


def test_sante(serveur):
    statut, _, corps = requete(serveur, "GET", "/sante")
    assert (statut, corps) == (200, {"statut": "ok"})


def creer_lien(serveur, url):
    statut, _, corps = requete(serveur, "POST", "/liens", {"url": url})
    assert statut == 201
    return corps["code"]


def test_creation_retourne_un_code_et_url(serveur):
    url = "https://exemple.ca/article"

    statut, _, corps = requete(serveur, "POST", "/liens", {"url": url})

    assert statut == 201
    assert len(corps["code"]) == 6
    assert corps["url"] == url


def test_suivi_redirige_vers_la_destination(serveur):
    url = "https://exemple.ca/destination"
    code = creer_lien(serveur, url)

    statut, entetes, _ = requete(serveur, "GET", f"/l/{code}")

    assert statut == 302
    assert entetes["Location"] == url


def test_statistiques_comptent_trois_visites(serveur):
    url = "https://exemple.ca/stats"
    code = creer_lien(serveur, url)
    for _ in range(3):
        assert requete(serveur, "GET", f"/l/{code}")[0] == 302

    statut, _, corps = requete(serveur, "GET", f"/stats/{code}")

    assert statut == 200
    assert corps == {"code": code, "url": url, "clics": 3}


def test_url_invalide_est_refusee(serveur):
    statut, _, corps = requete(serveur, "POST", "/liens", {"url": "javascript:alert(1)"})

    assert statut == 400
    assert corps == {"erreur": "url invalide : http(s)://… attendu"}


def test_json_invalide_est_refuse(serveur):
    statut, _, corps = requete(serveur, "POST", "/liens", "{json invalide")

    assert statut == 400
    assert corps == {"erreur": "JSON invalide"}


def test_code_inconnu_est_introuvable(serveur):
    statut_suivi, _, corps_suivi = requete(serveur, "GET", "/l/inconnu")
    statut_stats, _, corps_stats = requete(serveur, "GET", "/stats/inconnu")

    assert (statut_suivi, corps_suivi) == (404, {"erreur": "lien inconnu"})
    assert (statut_stats, corps_stats) == (404, {"erreur": "lien inconnu"})


def test_200_creations_concurrentes_produisent_des_codes_uniques(serveur):
    def creer(index):
        return requete(serveur, "POST", "/liens", {"url": f"https://exemple.ca/concurrent/{index}"})

    with ThreadPoolExecutor(max_workers=20) as pool:
        resultats = list(pool.map(creer, range(200)))

    assert all(statut == 201 for statut, _, _ in resultats)
    codes = [corps["code"] for _, _, corps in resultats]
    assert len(set(codes)) == 200


def test_route_inconnue_est_introuvable(serveur):
    statut, _, corps = requete(serveur, "GET", "/route-inconnue")

    assert statut == 404
    assert corps == {"erreur": "route inconnue"}
