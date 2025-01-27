# Notes de version du processeur Banff

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
