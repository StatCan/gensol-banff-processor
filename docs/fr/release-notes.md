# Notes de version du processeur Banff

## 2025-Juin-2 (Version `2.0.3`)

* Diverses mises à jour de la documentation pour la version publique sur github

## 2025-Mars-07 (Version `2.0.2`)

* Correction d'un bogue où l'on s'attendait à ce que toutes les procs d'un fichier de travail existent, plutôt que les procs appelées dans la séquence de travail active.
* Nouveaux paramètres d'entrée ajoutés
    * "indata_hist_filename", "indata_aux_filename" et "instatus_hist_filename"
    * Destiné à remplacer les anciens "histdata_filename", "auxdata_filename" et "histstatus_filename", bien que l'un ou l'autre puisse être utilisé jusqu'à ce qu'ils soient complètement obsolètes.
* Correction d'un bogue empêchant les contrôles de processus utilisant le même identifiant de contrôle, le même paramètre et le même fichier cible, mais des valeurs différentes.
* Une clarification concernant l'utilisation de tables sur disque dans les champs de valeur des contrôles de processus a été ajoutée au guide de l'utilisateur du processeur.

## 2025-24-janvier (Version `2.0.1`)

* Documentation : 
    * Diverses mises à jour mineures
    * La version française de metadata-tables.md a été ajoutée.
* Dépendances : 
    * Les versions de Duckdb et de Pyarrow sont maintenant limitées à moins à 2 et 19, respectivement, suite à des problèmes de compatibilité avec la version 19 de pyarrow et les versions disponibles de pandas et de duckdb.

## 2025-13-janvier (Version `2.0.0`)

Version de production initiale de la version Python du processeur Banff.
* Compatible avec banff v3.1
* Pour une description détaillée des nouvelles fonctionnalités et des différences entre les versions basées sur SAS, veuillez consulter notre [guide de migration](./migrating-from-sas-python.md)
