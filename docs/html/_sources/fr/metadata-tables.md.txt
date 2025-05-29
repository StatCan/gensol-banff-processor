# Fichiers de métadonnées

Au total, le processeur Banff utilise 18 tables de métadonnées, qui peuvent être classées comme suit:

Tables décrivant le déroulement global du processus:

* JOBS (obligatoire): définit le flux global du processus, y compris les étapes du processus à exécuter et le séquençage
* PROCESSCONTROLS: les [contrôles de processus](./processor-user-guide.md#process-controls) facultatifs donnent plus de contrôle sur les étapes individuelles du processus

Tables définissant les paramètres des étapes de processus pour les procédures Banff intégrées:

* VERIFYEDITSPECS: spécifications pour la procédure `verifyedits`
* OUTLIERSPECS: spécifications pour la procédure `outlier`
* ERRORLOCSPECS: spécifications pour la procédure `errorloc`
* DONORSPECS: spécifications pour la procédure `donorimp`
* ESTIMATORSPECS: spécifications pour la procédure `estimator`
* ESTIMATORS: paramètres supplémentaires pour la table `inestimator`
* ALGORITHMS: paramètres supplémentaires pour la table `inalgorithm`
* PRORATESPECS: spécifications pour la procédure `prorate`
* MASSIMPUTATIONSPECS: spécifications pour la procédure `massimp`

Tables utilisées pour définir les modifications, utilisées par les procédures `verifyedits`,`editstats`,`errorloc`,`deterministic`,`donorimp` et `prorate`:

* EDITS: Liste des modifications individuelles
* EDITGROUPS: Combinaisons de modifications référencées par des étapes de processus individuelles

Paramètres utilisés par plusieurs procédures:

* VARLISTS: Listes de variables et ordre de tri
* WEIGHTS: Poids, utilisés par certaines procédures
* EXPRESSIONS: Expressions d'exclusion utilisées par certaines procédures

Paramètres des étapes de processus pour les [procédures définies par l'utilisateur](./processor-user-guide.md#procédures-définies-par-lutilisateur):

* USERVARS: Spécifications pour les procédures définies par l'utilisateur (plugins)

Gestion des données:

* PROCESSOUTPUTS: Spécifiez les sorties à enregistrer pour chaque procédure

## Remarques générales

* Les champs de métadonnées d'ID tels que jobid ou controlid peuvent comporter jusqu'à 100 caractères
* Les noms de variables sur vos ensembles de données d'entrée peuvent comporter jusqu'à 64 caractères.
* Sensibilité à la casse: la cohérence doit être maintenue entre les métadonnées en ce qui concerne la casse. Cela inclut la correspondance des champs tels que specID et controlID ainsi que des noms de variables.
* Les noms de variables doivent respecter la casse des noms de colonnes sur l'entrée applicable. Dans certains contextes, `revenu` et `INCOME` peuvent être considérés comme des variables différentes sur une table, mais dans d'autres, ils ne le sont pas. Par exemple, les expressions metadata ne sont pas sensibles à la casse. Pour cette raison, il est recommandé de ne pas réutiliser les noms de colonnes simplement avec une casse différente et de respecter la casse dans les fichiers de données et de métadonnées.

## Jobs

Définissez vos flux de processus d’édition de données statistiques.

|Colonne|Type|Clé primaire|Clé étrangère|Obligatoire|Description|
|--|--|--|--|--|--|
|jobid|string|&#x2714;||&#x2714;|La valeur de la colonne jobid est utilisée pour extraire de la table toutes les lignes appartenant à la même stratégie E&I ou au même bloc de processus.|
|seqno|float| &#x2714; ||&#x2714;|L'ordre d'exécution est défini par la colonne seqno qui est lue de la valeur la plus basse à la plus grande. Le processeur Banff s'exécutera même s'il y a des écarts dans les valeurs seqno. Par exemple, une valeur de SEQNO=10 peut être suivie dans la ligne suivante par une valeur de 20.|
|controlid|string|  | &#x2714; ||Pointe vers un ID défini dans la table de métadonnées ProcessControls.|
|process|string|  | &#x2714; |&#x2714;|La valeur de la colonne de processus identifie le nom de la procédure ou du plug-in Banff à exécuter.|
|specid|string|| &#x2714; |&#x2714;|La colonne specid pointe vers un ID dans d'autres tables de métadonnées en fonction de la valeur de la colonne PROCESS.|
|editgroupid|string||&#x2714;||La colonne editgroupid pointe vers une entrée dans la table de métadonnées EditGroups.|
|byid|string||&#x2714;||La colonne byid pointe vers la table de métadonnées VarLists. Elle peut être utilisée par toutes les procédures à l'exception de VerifyEdits et du processus Job. La liste de variables indiquée sera utilisée pour le traitement par groupe.|
|acceptnegative|string| | ||La colonne acceptnegative est utilisée pour indiquer si les valeurs négatives sont considérées comme des valeurs valides ou non par le processus. Si elle n'est pas spécifiée (laissée vide) ou si la valeur est N, l'option accept negative ne sera pas spécifiée, sinon (si la valeur de la colonne est Y), l'option accept negative sera définie sur True.|

## ProcessControls

Définir les spécifications des contrôles de processus.

|Column|Type|Primary Key|Foreign Key|Required|Description|
|--|--|--|--|--|--|
|controlid|string|&#x2714;||&#x2714;|ID utilisé pour identifier le contrôle.|
|targetfile|string|&#x2714;||&#x2714;|Le nom du fichier de jeu de données auquel appliquer le contrôle. Ce champ n'est PAS obligatoire si parameter=EDIT_GROUP_FILTER.|
|parameter|string|&#x2714;||&#x2714;|Le type de contrôle de processus à appliquer.|
|value|string|||&#x2714;|La requête (dans la syntaxe SQL-lite) à appliquer pour ce contrôle. Ce champ n'est pas obligatoire et doit être vide si parameter=EDIT_GROUP_FILTER.|

## Edits

Définissez les modifications de cohérence linéaire à utiliser par les procédures Banff.

|Column|Type|Primary Key|Foreign Key|Required|Description|
|--|--|--|--|--|--|
|editid|string|&#x2714;||&#x2714;|ID utilisé pour identifier la modification.|
|leftside|string|||&#x2714;|Le côté gauche de l'équation.|
|operator|string|||&#x2714;|L'opérateur, les valeurs valides incluent >, >=, <, <=, = et !=.|
|rightside|string|||&#x2714;|Le côté droit de l'équation.|
|modifier|string||||La valeur du modificateur. La valeur par défaut de PASS indique que l'équation doit être True, FAIL peut être spécifié pour indiquer que l'équation doit être fausse.<BR><BR>ACCEPTE et REJET sont également des valeurs valides et peuvent être utilisées à la place de PASS et FAIL respectivement.|

## EditGroups

Définir des ensembles de modifications à référencer par des étapes de processus individuelles.

|Colonne|Type|Clé primaire|Clé étrangère|Obligatoire|Description|
|--|--|--|--|--|--|
|editgroupid|string|&#x2714;||&#x2714;|ID utilisé pour identifier le groupe de modifications.|
|editid|string|&#x2714;|&#x2714;|&#x2714;|ID utilisé pour identifier la modification appartenant au groupe.|

## Expressions

Expressions SQL utilisées pour exclure les donneurs du traitement dans la procédure `DonorImp` ou les enregistrements à utiliser dans les calculs de la procédure `Estimator`.

|Column|Type|Primary Key|Foreign Key|Required|Description|
|--|--|--|--|--|--|
|expressionid|string|&#x2714;||&#x2714;|L'ID utilisé pour identifier l'expression.|
|expressions|string|||&#x2714;|L'expression SQL.|

## Uservars

Définir les noms et les valeurs des variables de substitution dans les processus définis par l'utilisateur (plugins).

|Column|Type|Primary Key|Foreign Key|Required|Description|
|--|--|--|--|--|--|
|process|string|&#x2714;||&#x2714;|Le nom du processus défini par l'utilisateur auquel cette uservar s'applique. Il doit s'agir du même nom (ou de l'un des noms) que celui utilisé lors de l'appel de `factory.register()` dans la fonction `register()` requise pour un module UDP.|
|specid|string|&#x2714;||&#x2714;|Le specid de l'étape de travail spécifique à laquelle cette uservar s'applique.|
|var|string|&#x2714;||&#x2714;|Le nom de cette variable.|
|value|string|||&#x2714;|La valeur de la variable. Pour les valeurs numériques, convertissez la valeur de chaîne donnée au format souhaité dans l'UDP à l'aide de cette variable.

## Varlists

Répertorie les noms des variables utilisées dans les instructions de procédure qui nécessitent une liste de noms de variables. Tous les noms de variables dans la colonne `fieldid` qui ont la même valeur que `varlistid` seront collectés et utilisés avec l'instruction pour laquelle la liste est créée. La variable `seqno` définit l'ordre dans lequel les variables apparaîtront dans la liste. `seqno` est obligatoire et est important en particulier pour l'instruction BY.

|Column|Type|Primary Key|Foreign Key|Required|Description|
|--|--|--|--|--|--|
|varlistid|string|&#x2714;||&#x2714;|ID utilisé pour identifier la liste de variables.|
|seqno|float|&#x2714;||&#x2714;|Définit l'ordre de cet identifiant de champ dans la liste de variables globale de la valeur la plus basse à la plus grande. Les espaces dans la séquence sont autorisés, les nombres doivent simplement former un ordre logique.|
|fieldid|string|||&#x2714;|ID utilisé pour identifier ce champ spécifique dans la liste de variables.|

## Weights

Contient les noms des champs groupés par `weightid` et la valeur du poids pour chaque champ.

|Column|Type|Primary Key|Foreign Key|Required|Description|
|--|--|--|--|--|--|
|weightid|string|&#x2714;||&#x2714;|ID utilisé pour identifier cette pondération.|
|fieldid|string|&#x2714;||&#x2714;|Identifie le champ auquel cette pondération s'applique.|
|weight|float|||&#x2714;|La valeur de pondération du champ.|

## ProcessOutputs

Définissez les sorties à conserver pour chaque type de processus. Les métadonnées sont utilisées lorsque process_output_type est défini sur `custom`.

|Column|Type|Primary Key|Foreign Key|Required|Description|
|--|--|--|--|--|--|
|process|string|&#x2714;||&#x2714;|Le nom du processus pour lequel enregistrer ce fichier de sortie.|
|output_name|string|&#x2714;||&#x2714;|Le nom de l'ensemble de données à créer et à conserver à la fin du processus spécifié, puis à enregistrer sur le disque à la fin de la tâche globale.|

## Métadonnées spécifiques aux procédures Banff intégrées

Les tables de métadonnées suivantes sont utilisées pour stocker les paramètres d'entrée des procédures Banff intégrées. Chaque table de métadonnées comprend la colonne `specid`, qui relie les paramètres spécifiques à la procédure répertoriés dans chaque ligne à l'étape de processus associée dans la table de métadonnées `jobs`.

* VERIFYEDITSPECS: Spécifications pour la procédure `verifyedits`
* OUTLIERSPECS: Spécifications pour la procédure `outlier`
* ERRORLOCSPECS: Spécifications pour la procédure `errorloc`
* DONORSPECS: Spécifications pour la procédure `donorimp`
* ESTIMATORSPECS: Spécifications pour la procédure `estimator`
* ESTIMATORS: Paramètres supplémentaires pour la table `inestimator`
* ALGORITHMS: Paramètres supplémentaires pour la table `inalgorithm`
* PRORATESPECS: Spécifications pour la procédure `prorate`
* MASSIMPUTATIONSPECS: Spécifications pour la procédure `massimp`

Pour obtenir des informations sur les paramètres des procédures Banff intégrées, veuillez consulter le guide de l'utilisateur Banff dans le référentiel des procédures Banff.

## Conseils pour les programmeurs

Des *schémas XML* sont disponibles pour chaque fichier de métadonnées dans le sous-package `banffprocessor.metadata.models`. Ces schémas peuvent être utiles à des fins de débogage ou pour les développeurs d'applications qui doivent générer ces fichiers sans utiliser le modèle de métadonnées Excel. Par exemple, le schéma du fichier Algorithms.xml peut être imprimé avec les 2 lignes suivantes pour le code:

```python
from banffprocessor.metadata.models.algorithms import Algorithms

print(Algorithms.get_schema())
```

Une base de données *duckdb* est utilisée pour stocker les métadonnées pendant le traitement et peut être exportée à la fin du processus à des fins de débogage ou d'information. La connexion à la base de données est accessible via l'attribut `dbconn` de votre objet Processor comme illustré dans l'extrait de code ci-dessous:

```python
my_bp = Processor.from_file(input_file)
my_bp.dbconn.execute("EXPORT DATABASE '<chemin vers le dossier pour enregistrer les fichiers exportés>'")
```

```mermaid
---
title: Diagramme entité-relation des métadonnées du processeur Banff
---
erDiagram
    ALGORITHMS {
        string algorithmname PK
        string type
        string status
        string formula
        string description
    }
    DONORSPECS {
        string specid PK
        int mindonors
        real pcentdonors
        int n
        string eligdon
        boolean random
        int nlimit
        real mrl
        string dataexclvar FK
        string mustmatchid FK
        string posteditgroupid FK
    }
    EDITGROUPS {
        string editgroupid PK
        string editid PK
    }
    EDITS {
        string editid PK
        string leftside
        string operator
        string rightside
        string modifier
        string edit
    }
    ERRORLOCSPECS {
        string specid PK
        real cardinality
        real timeperobs
        string weightid
    }
    ESTIMATORS {
        string estimatorid PK
        int seqno PK
        string fieldid
        string auxvariables
        string weightvariable
        string variancevariable
        real varianceexponent
        string varianceperiod
        boolean excludeimputed
        boolean excludeoutliers
        int countcriteria
        real percentcriteria
        boolean randomerror
        string algorithmname FK    
    }
    ESTIMATORSPECS {
        string specid  PK
        string dataexclvar FK
        string histexclvar FK
        string Estimatorid FK
    }
    EXPRESSIONS {
        string expressionid PK
        string expressions
    }
    MASSIMPUTATIONSPECS {
        string specid
        int mindonors
        real pcentdonors
        boolean random
        int nlimit
        real mrl
        string mustimputeid
        string mustmatchid   
    }
    OUTLIERSPECS {
        string specid PK
        string method
        real mei
        real mii
        real mdm
        real exponent
        int minobs
        string varid
        string withid
        string dataexclvar FK
        real betae
        real betai
        string weight FK
        string sigma
        string side
        real startcentile
        boolean acceptzero
    }
    PRORATESPECS {
        string specid PK
        int decimal
        real lowerbound
        real upperbound
        string modifier
        string method
    }
    USERVARS {
        string process PK
        string specid PK
        string var PK
        string value
    }
    VARLISTS {
        string varlistid PK
        real seqno PK
        string fieldid
    }
    VERIFYEDITSPECS {
        string specid PK
        int imply
        int extremal
    }
    WEIGHTS {
        string weightid PK
        string fieldid  PK
        real weight        
    } 
    PROCESSCONTROLS {
        string controlid PK
        string targetfile PK
        string parameter PK
        string value
    }  
    PROCESSOUTPUTS {
        string process PK
        string output_name PK
    }
    JOBS {
        string jobid PK
        real seqno PK
        string controlid FK
        string process FK
        string specid FK
        string editgroupid FK
        string byid FK
        boolean acceptnegative
    }
    
    DONORSPECS ||--}o JOBS: "Définit les spécifications"
    ERRORLOCSPECS ||--}o JOBS: "Définit les spécifications"
    ESTIMATORSPECS ||--}o JOBS: "Définit les spécifications"
    OUTLIERSPECS ||--}o JOBS: "Définit les spécifications"
    PRORATESPECS ||--}o JOBS: "Définit les spécifications"
    MASSIMPUTATIONSPECS||--}o JOBS: "Définit les spécifications"
    VERIFYEDITSPECS ||--}o JOBS: "Définit les spécifications"
    USERVARS ||--}o JOBS: "Définit des paramètres personnalisés pour les plugins"

    EDITGROUPS ||--}o JOBS: "Définit le groupe d'édition"
    EDITGROUPS ||--}o DONORSPECS: "Définit le groupe d'édition de post"
    EDITS ||--}o EDITGROUPS: "Définit les groupes d'édition"
    
    ALGORITHMS ||--}o ESTIMATORS: "Définit un algorithme personnalisé"
    ESTIMATORS ||--}o ESTIMATORSPECS: "Définit l'estimateur"
    EXPRESSIONS ||--}o ESTIMATORSPECS: "Définit dataexclvar et histexclvar"
    EXPRESSIONS ||--}o DONORSPECS: "Définit dataexclvar"

    VARLISTS ||--}o JOBS: "Définit les variables utilisées pour créer des groupes de traitement"
    VARLISTS ||--}o DONORSPECS: "Définit mustmatchid"
    VARLISTS ||--}o OUTLIERSPECS: "Définit varid et withid"
    VARLISTS ||--}o MASSIMPUTATIONSPECS: "Defines mustimputeid"
    
    WEIGHTS ||--}o ERRORLOCSPECS: "Définit le poids variable"
    PROCESSCONTROLS ||--}o JOBS: "Définit les contrôles de processus"
    PROCESSOUTPUTS ||--}o JOBS: "Définit les ensembles de données à conserver"
```
