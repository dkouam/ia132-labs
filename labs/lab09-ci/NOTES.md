# Notes — lab 09

Mesures prises sur ce poste ; elles varient selon la machine et la charge.

Scénario standard (2 000 requêtes, 20 utilisateurs, 20 % de créations) : p95 5,4 ms et 0 % d'erreurs. Objectif de service respecté.

Scénario de forte concurrence (5 000 requêtes, 100 utilisateurs, 20 % de créations) : p95 16,0 ms, p99 209,3 ms et 0 % d'erreurs. Objectif de service respecté : le critère porte sur p95 < 50 ms et moins de 1 % d'erreurs, pas sur la p99.

Scénario de pic (5 000 requêtes, 100 utilisateurs, 100 % de créations) : p95 19,9 ms, p99 268,2 ms et 0 % d'erreurs. Objectif de service respecté selon les mêmes seuils.
