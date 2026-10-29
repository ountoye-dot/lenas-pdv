# lenas-pdv
Synchronisation quotidienne des points de vente Lena's  (lenas.be) vers la carte de lenasjuices.com
# Points de vente Lena's

Ce dépôt met à jour automatiquement la liste des points de vente affichée sur
https://lenasjuices.com/pages/points-de-vente

## Fonctionnement
- Chaque jour à 06:00 UTC, `scripts/sync_pdv.py` lit la liste des revendeurs sur https://www.lenas.be/
- Les nouvelles adresses sont géocodées (OpenStreetMap / Nominatim)
- Le résultat est enregistré dans `data/points-de-vente.json`, lu par la page Shopify

## Lancement manuel
Onglet Actions > « Synchroniser les points de vente » > Run workflow.

## En cas d'erreur
Si lenas.be change de structure, le script échoue sans modifier le fichier :
la page continue d'afficher la dernière liste valide.
