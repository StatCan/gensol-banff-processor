# Guide de migration du processeur Banff version 1

## Avant-propos

Ce document est destiné aux utilisateurs de la version SAS du processeur Banff et sert de complément au guide de l'utilisateur principal pour faciliter la transition de SAS (processeur Banff version 1) vers Python (processeur Banff version 2).

## Migration de SAS vers Python

La version SAS du Banff Processor remonte à 2008, elle est utilisée à Statistique Canada depuis de nombreuses années. La version Python est semblable à la version SAS à bien des égards et des efforts ont été déployés pour rendre les métadonnées rétrocompatibles lorsque c'est possible. Ce guide met en évidence certaines des principales différences pour aider les utilisateurs à migrer vers la nouvelle version.

En général, les fichiers de métadonnées XML de la version 1 sont compatibles avec la version 2, avec les exceptions suivantes:

- Les programmes personnalisés basés sur SAS (ou les programmes définis par l'utilisateur) ne fonctionneront pas; ils doivent être remplacés par des plugiciels. Les directives pour développer des plugiciels sont disponibles dans le guide de l'utilisateur.
- La syntaxe des expressions doit être révisée; Les expressions propres à SAS doivent être converties en syntaxe SQL-Lite.
- Le processeur basé sur SAS incluait certains comportements par défaut qui ont été supprimés pour augmenter la modularité et la transparence. Le comportement passé peut être reproduit avec des contrôles de processus; voir la section sur les contrôles de processus dans le guide de l'utilisateur pour plus de détails.

### Nouvelles fonctionnalités

- Blocs de processus: les blocs de processus permettent aux utilisateurs d'appeler une stratégie au sein d'une stratégie. Dans le processeur SAS, la table des tâches pouvait contenir plusieurs tâches, mais elles peuvent désormais être enchaînées pour créer une tâche principale. Cela se fait en utilisant le processus appelé tâche et en spécifiant l'identification d'une stratégie dans la colonne specid.
- Contrôles de processus: les contrôles de processus permettent d'apporter des modifications aux entrées d'une étape de traitement sans risquer de modifier les principaux ensembles de données de travail. Cela se faisait généralement dans le processeur SAS avec des processus définis par l'utilisateur, ou les modifications d'entrée étaient codées en dur dans le processeur lui-même.
- Le processeur Banff prend désormais en charge les longueurs variables jusqu'à 64 caractères. Une variable doit toujours commencer par un caractère ou un trait de soulignement et se composer uniquement de caractères alphabétiques, de chiffres et de traits de soulignement (les espaces avec les noms de variables ne sont pas pris en charge).

## Changements de comportement

1. Une différence clé est que le processeur SAS Banff était un générateur de code. Le processeur créait un programme SAS, puis le programme était exécuté. Il y avait une option pour enregistrer le programme généré, qui pouvait être exécuté et utilisé à des fins de débogage. Ce n'est plus le cas avec le processeur Python, le processus est exécuté de manière dynamique en un seul passage.

2. Dans le processeur SAS, la bibliothèque de travail SAS était utilisée pour stocker et accéder aux ensembles de données temporaires. Dans Python, il existe quelques alternatives. En général, les données sont accessibles dans des processus définis par l'utilisateur (plugiciels) via l'objet ProcessorData, cependant, les développeurs de plugiciels peuvent choisir de stocker les fichiers de diagnostic dans un autre emplacement tel qu'une base de données duckdb ou un dossier approprié. L'utilisation de la bibliothèque tempfile est une option, mais elle enregistre les données dans le profil de l'utilisateur par défaut, ce qui peut ne pas être approprié dans certaines situations.

3. Le processeur ne supprime plus automatiquement les enregistrements trouvés dans le fichier de rejet des données d'entrée d'une étape d'imputation. Si ce comportement est souhaité, le [contrôle de processus](./processor-user-guide.md#contrôles-de-processus) `exclude_rejected` peut être utilisé. Notez que les données rejetées sont accessibles dans un processus défini par l'utilisateur avec `processor_data.get_output_dataset("outreject")`.

4. Lors de l'appel de la procédure ErrorLoc, le statut des valeurs aberrantes n'est plus pris en compte, seules les valeurs marquées comme FTI dans le fichier de statut d'entrée. Si ce comportement est souhaité, un processus défini par l'utilisateur (plugiciels) peut être créé. Le plan à moyen terme serait de remplacer cette fonctionnalité par un contrôle/filtre de processus.

## Les entrées

### Paramètres de macro SAS

Les variables de macro SAS sont désormais des paramètres de fonction Python. Avec le nouveau processeur, ces paramètres peuvent être spécifiés dans un fichier JSON. Alternativement, les entrées peuvent être spécifiées directement lors de la création d'un objet `Processor`.

Les noms de paramètres ont été modifiés pour respecter les conventions de dénomination Python et améliorés pour être plus cohérents et descriptifs. Certains ont été remplacés par des options plus génériques ou ne sont plus applicables. Notez également que les noms de paramètres sont désormais **sensibles à la casse**.

|SAS|Python|Remarques|
|--|--|--|
|jobid|job_id||
|id|unit_id|Cette modification était nécessaire car id est une fonction Python et il n'est pas recommandé de l'utiliser comme nom de variable.|
|dataLib|input_folder|Dans SAS, dataLib était un libref, dans Python, un dossier de fichiers est spécifié. Cependant, les ensembles de données peuvent également être spécifiés directement lors de la création d'un objet Processor. Si aucun ensemble de données n'est spécifié, le processeur recherchera dans le dossier d'entrée le nom de fichier spécifié associé au fichier d'entrée.|
|curFile|indata_filename||
|outdataLib|output_folder||
|auxFile|auxdata_filename||
||instatus_filename|Il s'agit d'un nouveau paramètre facultatif dans le processeur Python qui permet de spécifier les valeurs d'état initiales.|
|histFile|histdata_filename||
|histStatus|histstatus_filename||
|custProgFref|user_plugins_folder||
|flatfileFref||Supprimé du processeur Python car cette option était rarement utilisée.|
|seed|seed||
|logType|log_level|Le paramètre log_level fournit des fonctionnalités similaires à logType.|
|editstatsOutputType||Remplacé par process_output_type.|
|estimatorOutputType||Remplacé par process_output_type.|
|massImputOutputType||Remplacé par process_output_type.|
|randnumvar|randnumvar||
|genCode/fgenprog||N'est plus applicable, un code de programme n'est plus généré et exécuté.|
|editGroupFilter||Remplacé par le contrôle de processus EDIT_GROUP_FILTER.|
|tempLib||N'est plus applicable.|
|bpOptions||Ne sont plus applicables, ces options étaient TIME, KEEPTEMP et NOBYGRPSTATS.|
||save_format|Il s'agit d'une nouvelle option du processeur Python, le processeur SAS a produit des ensembles de données SAS. Parquet est actuellement le format d'enregistrement recommandé (.parq), CSV est fourni à des fins de test et de débogage.|

## Fichiers d'entrée

### Fichiers de données d'entrée

Dans le processeur SAS, les fichiers de données d'entrée étaient des ensembles de données SAS. Il y avait essentiellement deux types de données: caractères (chaînes de largeur fixe) et numériques (nombres à virgule flottante 64 bits). Dans le processeur Python, les fichiers parquet sont le format de fichier recommandé. Ces fichiers sont lus et principalement stockés sous forme de tableaux fléchés, bien que, dans certains cas, les données soient converties dans d'autres formats tels que les trames de données pandas ou les tables duckdb. Il existe de nombreux types différents, nous recommandons généralement str (chaînes de longueur variable) et float64 (nombres à virgule flottante 64 bits), bien que différents types puissent être utilisés (float32, float16, int8, int16, ...). Les types de variables doivent être vérifiés et ajustés si nécessaire. La principale raison pour laquelle les fichiers CSV ne sont pas recommandés est le manque de métadonnées pour garantir que les types sont définis correctement lors de la lecture et de l'écriture des fichiers.

### Fichiers de métadonnées

- La structure des fichiers de métadonnées dans le processeur Python est essentiellement la même que celle de la version basée sur SAS, tous les nouveaux éléments sont facultatifs. Cependant, le contenu des métadonnées peut devoir être ajusté. Les expressions devront probablement être mises à jour pour refléter la nouvelle syntaxe.

- Les longueurs maximales de la plupart des colonnes de métadonnées ont été augmentées. Par exemple, auparavant, de nombreux champs d'ID avaient une limite de 30 caractères, cette limite a été augmentée à 100 caractères.

- Bien que les fichiers de métadonnées acceptent toujours les valeurs YES/NO ou Y/N, elles sont stockées dans le processeur sous forme de valeurs booléennes et seront donc converties en valeurs Vrai/Faux.

- Le processeur Banff dispose toujours d'un modèle Excel pour faciliter la création de fichiers XML comme prévu par le processeur Banff, cependant, la macro Excel a été supprimée du modèle et le package banffprocessor inclut désormais un utilitaire pour convertir le classeur Excel en XML. Cet utilitaire peut être appelé à partir de la ligne de commande ou à partir d'un programme Python. L'utilitaire de ligne de commande s'appelle `banffconvert`. L'utilitaire est défini dans `banffprocessor.util.metadata_excel_to_xml`

|Fichier de métadonnées|Remarques|
|--|--|
|JOBS|Jobs dispose d'un nouvel élément facultatif appelé controlid. Cette nouvelle colonne est utilisée pour lier les spécifications dans les métadonnées des contrôles de processus. Notez également que SEQNO peut désormais contenir des décimales, alors qu'auparavant SEQNO ne pouvait contenir qu'un entier.|
|USERVARS|La structure n'a pas changé.|
|EDITS|La structure n'a pas changé. La syntaxe des modifications n'a pas changé.|
|EDITGROUPS|Aucun changement.|
|VERIFYEDITSPECS|Aucun changement.|
|OUTLIERSPECS|Aucun changement.|
|ERRORLOCSPECS|Aucun changement.|
|DONORSPECS|Aucun changement.|
|ESTIMATORSPECS|Aucun changement.|
|PRORATESPECS|Aucun changement.|
|MASSIMPUTATIONSPECS|Aucun changement.|
|ALGORITHMS|Les algorithmes définis par l'utilisateur ne peuvent plus remplacer les algorithmes des estimateurs intégrés, un nouveau nom doit être choisi.|
|ESTIMATORS|Aucun changement.|
|EXPRESSIONS|La structure n'a pas changé. Cependant, les expressions sont désormais basées sur SQLite tel qu'implémenté dans [duckdb](https://duckdb.org/docs/sql/expressions/overview). Une différence par exemple serait que les constantes de chaîne doivent être placées entre guillemets simples plutôt qu'entre guillemets doubles ; `P53_05_1="1"` devrait être remplacé par `P53_05_1='1'`.|
|VARLISTS|Aucun changement.|
|WEIGHTS|Aucun changement.|
|PROCESSCONTROLS|Il s'agit d'un nouveau fichier de métadonnées utilisé pour créer des spécifications de contrôle de processus.|
|PROCESSOUTPUTS|Il s'agit d'un nouveau fichier de métadonnées utilisé pour contrôler les sorties conservées. Il est utilisé lorsque process_output_type='Custom'|

### Processus définis par l'utilisateur (PDU)

|SAS|Python|Remarques|
|--|--|--|
|parmKeyVar, parmByList, parmSeqno, ...|processor_data.input_params.unit_id,  processor_data.by_varlist, processor_data.current_job_step.seqno, ... |Dans le processeur SAS, les variables macro globales SAS étaient utilisées pour accéder aux paramètres d'entrée. Désormais, les paramètres d'entrée sont disponibles via les attributs d'objet processor_data tels que input_params et current_job_step|
|work.jobs| processor_data.dbconn.sql("select * from Banff.JOBS").to_arrow_table()|Au lieu d'accéder aux tables de métadonnées sous forme d'ensembles de données SAS dans la bibliothèque de travail SAS, les tables de métadonnées sont accessibles dans une base de données duckdb via processor_data.dbconn.|
|work.statusall|status_table = processor_data.get_dataset("status_file", table_format="arrow")|Au lieu d'accéder aux tables de données sous forme d'ensembles de données SAS dans la bibliothèque de travail SAS, les ensembles de données sont accessibles via la fonction get_dataset de processor_data. L'ensemble de données peut être renvoyé au format arrow ou pandas. La fonction set_dataset peut être utilisée pour enregistrer un ensemble de données de sortie.|

## Output files

Le processeur SAS produisait un fichier cumulatif avec le suffixe all. Ce suffixe a été supprimé.

|SAS|Python|Remarques|
|--|--|--|
|imputedfile|imputed_file|Cette sortie reste la même.|
|statusall|status_file|Les colonnes du fichier d'état ont été réduites. Les colonnes standard sont la variable d'ID d'unité ainsi que FIELDID, STATUS, VALUE, JOBID et SEQNO. VALUE est une nouvelle colonne, editgroupid, outliersstatus et les variables by ont été supprimées.|
|cumulatifstatusall|status_log|Comme le fichier d’état, les colonnes de cette sortie ont été standardisées.|
||time_store|Il s'agit d'un nouvel ensemble de données qui stocke l'heure de début, l'heure de fin et la durée de chaque étape de traitement ainsi que le temps d'exécution cumulé.|
|acceptableall|outacceptable||
|donormapall|outdonormap||
|editapplicall|outedit_applic||
|editstatusall|outedit_status||
|estefall|outest_ef||
|estlrall|outest_lr||
|estparmsall|outest_parm||
|globalstatusall|outglobal_status||
|keditsstatusall|outk_edits_status||
|matchfieldstatall|outmatching_fields||
|outlierstatusall|outlier_status||
|randomerrorall|outrand_err||
|reducededitsall|outedits_reduced||
||outreject|Le fichier outreject est le dernier ensemble de données outreject généré par Prorate ou ErrorLoc. Il s'agissait uniquement d'un ensemble de données de travail dans la version SAS appelé `rejected`, dans la version Python, il est inclus comme ensemble de données de sortie.|
|rejectedall|outreject_all|Le fichier rejeté est un cas particulier où le suffixe `all` a été conservé. Cela est dû au fait que Prorate et ErrorLoc traitent cet ensemble de données de manière légèrement différente. Consultez le guide de l'utilisateur pour plus d'informations.|
|varsroleall|outvars_role||

## Conclusion

Pour plus d'informations sur l'utilisation de Banff et du processeur Banff, veuillez consulter les principaux guides d'utilisation. Nous espérons que ces informations vous aideront à passer de la version 1 à la version 2.
