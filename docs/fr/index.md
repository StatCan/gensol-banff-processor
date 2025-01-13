# Processeur Banff

Le processeur Banff fait partie du projet Banff. Il s'agit d'un outil qui peut être installé en complément du package Banff Procedure. Cet outil permet de mettre en œuvre une stratégie d'imputation, qui est essentiellement une séquence d'étapes de traitement. Une étape de traitement peut être une procédure Banff standard, un processus défini par l'utilisateur (plugin) ou un bloc de processus (une autre séquence d'étapes de traitement).

Les stratégies d'imputation sont définies à l'aide de fichiers XML. Un modèle Excel a été fourni avec un utilitaire permettant de convertir les métadonnées créées avec le modèle en fichiers XML requis par le processeur. Le résultat d'une tâche de processeur est le fichier imputé accompagné d'un journal et de divers fichiers d'état et de diagnostic facultatifs.


## Documentation utilisateur

-  [Guide de l'utilisateur](./processor-user-guide.md) - *Informations détaillées sur l'utilisation du processeur Banff basé sur Python*
-  [Guide de migration](./migrating-from-sas-python.md.md) - *Informations détaillées sur l'utilisation des différences entre les processeurs basés sur Python et SAS*
-  [Blocs de processus et contrôles de processus](./process-blocks-and-controls.md) - *Une introduction*
-  [Notes de version](./release-notes.md) - *Résumé des changements*
