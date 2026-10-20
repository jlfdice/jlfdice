# JLF D'ICE — La collection

Site de la collection de tableaux en dés JLF D'ICE.

- `index.html` : le site (intro, collection 3D, commandes)
- `etat.json` : statut des œuvres (`dispo`, `reserve`, `vendu`, `privee`, `bientot`) et nom Instagram
- `manifest.webmanifest` + `icon-*.png` : installation sur l'écran d'accueil

## Atelier : commandes « portrait en dés »

Le client envoie sa **fiche** (avec le *code atelier*, ex. `JLFD-C61-R82-D10-Z8KX`) et sa **photo originale**.
`atelier/commande.py` régénère exactement la même conversion et produit le plan de fabrication :

```
python3 atelier/commande.py --photo photo_client.jpg --code JLFD-C61-R82-D10-Z8KX --client "Prénom"
```

Sorties : `Plan_fabrication_<REF>.pdf` (caractéristiques, liste de dés par face, carte et pages de sections),
`photo_originale_HD_<REF>.jpg`, `version_des_HD_<REF>.png`, `grille_<REF>.csv`.
