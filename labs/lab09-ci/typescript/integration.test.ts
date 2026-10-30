// Tests d'intégration : un VRAI serveur HTTP, de vraies requêtes. À compléter (voir README).
import assert from 'node:assert/strict';
import type { AddressInfo } from 'node:net';
import { after, before, test } from 'node:test';
import { creerServeur } from './api.ts';

const serveur = creerServeur();
let base = '';

before(async () => {
  await new Promise<void>((ok) => serveur.listen(0, '127.0.0.1', ok));
  base = `http://127.0.0.1:${(serveur.address() as AddressInfo).port}`;
});
after(async () => {
  await new Promise<void>((ok, erreur) => serveur.close((err) => (err ? erreur(err) : ok())));
});

// redirect: 'manual' pour lire la réponse 302 elle-même.
const appel = (chemin: string, init: RequestInit = {}) => fetch(base + chemin, { redirect: 'manual', ...init });
const creerLien = (url: string) =>
  appel('/liens', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });

test('santé', async () => {
  const r = await appel('/sante');
  assert.equal(r.status, 200);
  assert.deepEqual(await r.json(), { statut: 'ok' });
});

test('créer un lien retourne son code et son URL', async () => {
  const url = 'https://exemple.ca/article';
  const reponse = await creerLien(url);
  const resultat = (await reponse.json()) as { code: string; url: string };

  assert.equal(reponse.status, 201);
  assert.match(resultat.code, /^[A-Za-z0-9]{6}$/);
  assert.equal(resultat.url, url);
});

test('suivre un lien redirige vers sa destination', async () => {
  const url = 'https://exemple.ca/destination';
  const creation = await creerLien(url);
  const { code } = (await creation.json()) as { code: string };

  const reponse = await appel(`/l/${code}`);

  assert.equal(reponse.status, 302);
  assert.equal(reponse.headers.get('location'), url);
});

test('les statistiques comptent les visites du lien', async () => {
  const creation = await creerLien('https://exemple.ca/stats');
  const { code } = (await creation.json()) as { code: string };

  for (let visite = 0; visite < 3; visite++) {
    const reponse = await appel(`/l/${code}`);
    assert.equal(reponse.status, 302);
  }

  const reponseStats = await appel(`/stats/${code}`);
  assert.equal(reponseStats.status, 200);
  assert.deepEqual(await reponseStats.json(), { code, url: 'https://exemple.ca/stats', clics: 3 });
});

test('une URL invalide est refusée', async () => {
  const reponse = await creerLien('javascript:alert(1)');

  assert.equal(reponse.status, 400);
  assert.deepEqual(await reponse.json(), { erreur: 'url invalide : http(s)://… attendu' });
});

test('un corps JSON invalide est refusé', async () => {
  const reponse = await appel('/liens', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{json invalide',
  });

  assert.equal(reponse.status, 400);
  assert.deepEqual(await reponse.json(), { erreur: 'JSON invalide' });
});

test('un code inconnu renvoie 404 pour le suivi et les statistiques', async () => {
  const suivi = await appel('/l/inconnu');
  const statistiques = await appel('/stats/inconnu');

  assert.equal(suivi.status, 404);
  assert.deepEqual(await suivi.json(), { erreur: 'lien inconnu' });
  assert.equal(statistiques.status, 404);
  assert.deepEqual(await statistiques.json(), { erreur: 'lien inconnu' });
});

test('200 créations concurrentes produisent 200 codes distincts', async () => {
  const reponses = await Promise.all(
    Array.from({ length: 200 }, (_, index) => creerLien(`https://exemple.ca/concurrent/${index}`)),
  );
  const resultats = await Promise.all(
    reponses.map(async (reponse) => {
      assert.equal(reponse.status, 201);
      return (await reponse.json()) as { code: string };
    }),
  );
  const codes = resultats.map(({ code }) => code);

  assert.equal(new Set(codes).size, 200);
});

test('une route inconnue renvoie 404', async () => {
  const reponse = await appel('/route-inconnue');

  assert.equal(reponse.status, 404);
  assert.deepEqual(await reponse.json(), { erreur: 'route inconnue' });
});
