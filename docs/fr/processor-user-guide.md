# Guide d'utilisation du processeur Banff

## Introduction

Le processeur Banff est un paquet Python utilisé pour exécuter un processus de vérification statistique des données (VSD), également appelé communément vérification et imputation. Un processus VSD spécifique se compose généralement de nombreuses étapes de processus individuelles, chacune exécutant une fonction VSD telle que la localisation d'erreurs, la détection de valeurs aberrantes ou l'imputation. Le flux de processus décrit les étapes de processus à exécuter et la séquence dans laquelle elles sont exécutées. Étant donné un ensemble de tables de métadonnées d'entrée qui décrivent le flux de processus VSD, y compris chaque étape individuelle, le processeur Banff exécute chaque étape de processus en séquence, en gérant toute la gestion des données intermédiaires. L'avantage du système piloté par métadonnées du processeur Banff est que la conception et la modification du processus VSD sont gérées à partir de tables de métadonnées plutôt que du code source.

Autres notes sur le processeur Banff:

- Simplicité: Une fois les tables de métadonnées créées, le processeur peut être exécuté à partir d'une seule ligne de code
- Efficacité: Conçu pour les processus VSD de niveau production
- Modularité: Au sein d'une étape de processus, les utilisateurs peuvent appeler les procédures Banff intégrées ou les [procédures définies par l'utilisateur](#procédures-définies-par-lutilisateur)
- Flexibilité: Les [Contrôles de processus](#contrôles-de-processus) et les [Blocs de processus](#blocs-de-processus) permettent aux utilisateurs de spécifier des flux de processus complexes
- Informatif: Le processeur produit des diagnostics à partir de chaque étape et pour le processus global
- Transparence: Le code source est disponible et librement partagé

Le guide de l'utilisateur utilise souvent la terminologie du [**Modèle générique de vérification statistique des données** (MGVSD)](https://statswiki.unece.org/spaces/sde/pages/117771706/GSDEM). Les utilisateurs sont encouragés à se référer au MGVSD pour la terminologie commune concernant les concepts VSD.

## Table des matières

- [Fichiers de métadonnées d'entrée](#fichiers-de-métadonnées-dentrée)
- [Outil de génération de métadonnées](#outil-de-génération-de-métadonnées)
- [Paramètres d'entrée](#paramètres-dentrée-du-processeur-banff)
- [Exécution du processeur en tant qu'utilitaire de ligne de commande](#exécution-du-processeur-en-tant-quutilitaire-de-ligne-de-commande)
- [Exécution du processeur à partir d'un processus Python](#exécution-du-processeur-à-partir-dun-script-python)
- [Procédures définies par l'utilisateur](#procédures-définies-par-lutilisateur)
- [Contrôles de processus](#contrôles-de-processus)
- [Blocs de processus](#blocs-de-processus)
- [Les Sorties](#les-sorties)

## Fichiers de métadonnées d'entrée

Le processeur Banff est piloté par des tables de métadonnées décrivant à la fois le flux global du processus, ainsi que les paramètres requis pour les étapes individuelles du processus. La table de métadonnées principale est appelée JOBS, et spécifie le flux global du processus, en particulier les procédures Banff intégrées et/ou les programmes définis par l'utilisateur (plugins) à exécuter et leur séquencement relatif. La table JOBS peut contenir plusieurs tâches (c'est-à-dire le flux du processus), spécifiées par le `jobid` (identifiant de stratégie), bien qu'une seule stratégie puisse être attendue à la fois par le processeur Banff. Chaque stratégie comprendra une ligne par étape du processus ; les colonnes clés sont:

- `jobid`: identifiant de stratégie.
- `seqno`: numéro de séquence des étapes individuelles du processus.
- `process`: nom de la procédure intégrée ou du programme défini par l'utilisateur à exécuter à chaque étape du processus.
- `specid`: identifiant de spécification, reliant d'autres tables de métadonnées contenant des paramètres spécifiques au `process` déclaré.

Les colonnes supplémentaires de la table JOBS incluent un identifiant de contrôle de processus facultatif (`controlid`) ainsi que des paramètres communs à plusieurs procédures (`editgroupid`,`byid`,`acceptnegative`).

Au total, le processeur Banff utilise 18 tables de métadonnées, qui peuvent être classées comme suit:

- Tables décrivant le flux global du processus: `JOBS` `PROCESSCONTROLS`
- Paramètres des étapes du processus pour les procédures Banff intégrées: `VERIFYEDITSPECS` `OUTLIERSPECS` `ERRORLOCSPECS` `DONORSPECS` `ESTIMATORSPECS` `ESTIMATORS` `ALGORITHMS` `PRORATESPECS` `MASSIMPUTATIONSPECS`
- Paramètres des étapes du processus pour les [procédures définies par l'utilisateur](#procédures-définies-par-lutilisateur): `USERVARS`
- Tables utilisées pour définir les modifications: `EDITS` `EDITGROUPS`
- Paramètres utilisés par plusieurs procédures: `VARLISTS` `WEIGHTS` `EXPRESSIONS`
- Gestion des données: `PROCESSOUTPUTS`

Seule la table JOBS est obligatoire, bien que d'autres tables soient requises en fonction des procédures ou des options utilisées. Une description complète de toutes les tables de métadonnées est incluse dans ce document: [Tables de métadonnées](metadata-tables.md)

### Formatage

Les tables de métadonnées doivent être enregistrées au format `.xml`. Les utilisateurs peuvent créer les fichiers `.xml` eux-mêmes ou utiliser le modèle de processeur Banff (../../banffprocessor_template.xlsx) pour créer et enregistrer les métadonnées, et [l'outil de génération de métadonnées](#outil-de-génération-de-métadonnées) pour convertir le fichier modèle en tables `.xml`. Par défaut, le processeur recherchera les fichiers XML au même emplacement que votre fichier d'entrée `.json`, soit directement dans le même dossier, soit dans un sous-dossier `\metadata`. Vous pouvez également fournir un emplacement spécifique en définissant le paramètre `metadata_folder` dans votre fichier JSON d'entrée.

### Exemple (tableau JOBS)

Le tableau suivant définit un travail unique, `Principal`, qui comprend quatre étapes de processus.

| jobid | seqno | controlid | process       | specid       | edigroupid | byid    | acceptnegative |
| ----- | ----- | --------- | ------------- | ------------ | ---------- | ------- | -------------- |
| Main  | 1     |           | ERRORLOC      | errloc_specs | edits_1    |         | Y              |
| Main  | 2     |           | DETERMINISTIC |              | edits_1    |         | Y              |
| Main  | 10    |           | DONORIMP      | donor_specs  | edits_1    | by_list | Y              |
| Main  | 99    |           | PRORATE       | pro_specs    | edits_2    |         | Y              |

- Seul l'ordre des numéros de séquence (`seqno`) est important ; ils n'ont pas besoin d'être des entiers séquentiels.
- Ce travail comprend quatre étapes de processus, exécutées séquentiellement, composées de quatre procédures Banff intégrées: `ERRORLOC`, `DETERMINSITIC`, `DONORIMP` et `PRORATE`.
- Les paramètres `editgroupid`, `byid` et `acceptnegative`, qui sont communs à de nombreuses procédures Banff intégrées, sont inclus dans la table JOBS.
- La plupart des procédures incluent des paramètres obligatoires et/ou facultatifs qui définissent exactement comment la procédure doit être exécutée. Ceux-ci sont contenus dans des tables de métadonnées supplémentaires et liés à des étapes de processus spécifiques via la colonne `specid`. Les procédures qui n'ont pas de paramètres supplémentaires (au-delà de ceux inclus dans la table JOBS) ne nécessitent pas de `specid`.
- La colonne `controlid` est facultative et peut être utilisée pour spécifier les [contrôles de processus](#contrôles-de-processus).

Des exemples supplémentaires peuvent être trouvés dans le dossier 'examples' du projet.

## Outil de génération de métadonnées

Les métadonnées stockées dans le [modèle de processeur Banff](../../banffprocessor_template.xlsx) doivent être converties en fichiers XML avant d'exécuter le processeur. Un outil de conversion est fourni à cet effet. Avec le package banffprocessor installé dans votre environnement Python, l'outil de conversion peut être exécuté avec la commande suivante:

```shell
banffconvert "\path\to\your\excel_metadata.xlsx" -o "\my\output\directory" -l fr
```

or:

```shell
banffconvert "\path\to\your\excel_metadata.xlsx" --outdir="\my\output\directory" --lang en
```

Alternativement pour exécuter en tant que module:

```shell
python -m banffprocessor.util.metadata_excel_to_xml "\path\to\your\excel_metadata.xlsx" -o "\my\output\directory"
```

- __NOTE__: Le paramètre '-o'/'--outdir' est facultatif. S'il n'est pas fourni, l'outil de conversion enregistrera les fichiers XML dans le même répertoire que le fichier d'entrée.
- __NOTE__: Le paramètre '-l'/'--lang' est facultatif. Les valeurs valides sont en et fr. Si elles ne sont pas spécifiées, la valeur par défaut est en.

Enfin, l’outil peut être inclus et exécuté directement dans un script python:

```python
import banffprocessor.util.metadata_excel_to_xml as e2x

e2x.convert_excel_to_xml("\\path\\to\\your\\excel_metadata.xlsx", "\\my\\output\\directory")
```

## Paramètres d'entrée du processeur Banff

Les paramètres d'entrée sont spécifiés dans un fichier `.json` ou un objet `ProcessorInput`, tous deux transmis au processeur et utilisés pour spécifier les paramètres de votre tâche. Voici les paramètres actuellement disponibles:

|Nom|Objectif|Obligatoire?|
|--|--|--|
|job_id|L'ID de stratégie de votre `jobs.xml` que vous souhaitez exécuter.|Y|
|unit_id|La variable d'identification de l'unité est l'identifiant unique sur les fichiers de microdonnées pour la stratégie|Y|
|indata_filename|Le nom de fichier ou le chemin d'accès complet de votre fichier de données d'entrée/actuel|Y (sauf si vous exécutez uniquement *VerifyEdits*)|
|indata_aux_filename|Le nom de fichier ou le chemin d'accès complet de votre fichier de données auxiliaires|N|
|indata_hist_filename|Le nom de fichier ou le chemin d'accès complet de votre fichier de données historiques|N|
|instatus_hist_filename|Le nom de fichier ou le chemin d'accès complet de votre fichier de données d'état historique|N|
|instatus_filename|Le nom de fichier ou le chemin d'accès complet d'un fichier d'état à utiliser comme entrée pour le premier processus de votre stratégie nécessitant un fichier d'état.[^1]|N|
|user_plugins_folder|L'emplacement facultatif du dossier contenant vos plugins de procédure Python personnalisés. *Voir ci-dessous pour une description de la façon de créer vos propres plugins*|N|
|metadata_folder|Le chemin facultatif vers un dossier où vos métadonnées XML peuvent être trouvées|N|
|output_folder|Le chemin facultatif vers un dossier dans lequel vos fichiers de sortie seront enregistrés|N|
|process_output_type|Contrôle les ensembles de données de sortie conservés par chaque processus. Les options incluent `all`, `minimal` et `custom`. Lorsque `all` est spécifié, toutes les sorties sont conservées. Si `minimal` est spécifié, seuls les fichiers imputed_file, status_file et status_log sont conservés. Lorsque la valeur est `custom`, le processeur examine les métadonnées `ProcessOutputs` pour déterminer ce qu'il faut conserver.|N|
|seed|La valeur de départ à utiliser pour des résultats cohérents lors de l'utilisation des mêmes données d'entrée et paramètres|N|
|no_by_stats| Si spécifié, détermine si no_by_stats est défini sur True lors de l'appel des procédures standard.|N|
|randnumvar|Spécifiez une variable de nombre aléatoire à utiliser lorsque vous devez faire un choix lors de la localisation d'erreur ou de l'imputation par donneur. Ce paramètre est facultatif et n'est utilisé que par ErrorLoc et DonorImputation simultanément (il ne peut pas être utilisé dans l'un et pas dans l'autre). Veuillez consulter le document Guide de l'utilisateur de Banff pour plus de détails sur l'utilisation de l'option `randnumvar` dans les procédures ErrorLoc et DonorImputation.<BR><BR>Cette option peut être utile lorsqu’il est nécessaire d’obtenir les mêmes résultats de localisation d’erreur ou d’imputation d’une exécution à l’autre.|N|
|save_format|Liste facultative des extensions de fichier utilisées pour déterminer le format d'enregistrement des fichiers de sortie. Une ou plusieurs extensions peuvent être fournies. Prend actuellement en charge les extensions CSV et Parquet.|N|
|log_level|Configure la création ou non d'un fichier journal et le niveau de messages qu'il doit contenir. La valeur doit être 0, 1 (par défaut) ou 2. Voir [Les Sorties](#les-sorties).|N|

[^1]: Si aucune colonne `JOBID` ou `SEQNO` n'est trouvée dans le fichier, elles sont ajoutées et leurs valeurs sont initialisées aux paramètres d'entrée `job_id` et 0 respectivement. Si elles sont présentes, tous les enregistrements avec un `JOBID` ou un `SEQNO` manquant ou tous les enregistrements avec un JOBID qui se trouve également dans vos métadonnées Jobs actuelles auront les valeurs de `JOBID` et de `SEQNO` modifiées en NaN.

Exemple de fichier d'entrée JSON:

```json
{
    "job_id": "j1",
    "unit_id": "ident",
    "indata_filename": "indata.parq",
    "indata_aux_filename": "C:\\full\\filepath\\to\\auxdata.parq",
    "indata_hist_filename": "histdata.parq",
    "instatus_hist_filename": "histstatus.parq",
    "instatus_filename": "instatus.parq",
    "user_plugins_folder": "C:\\path\\to\\my\\plugins",
    "metadata_folder": "C:\\path\\to\\xml\\metadata",
    "output_folder": "my_output_subfolder",
    "process_output_type": "All",
    "seed": 1234,
    "no_by_stats": "N",
    "randnumvar": "",
    "save_format": [".parq", ".csv"],
    "log_level": 2
}
```

Exemple de création d'un objet `ProcessorInput` en ligne:

```python
from banffprocessor.processor import Processor
from banffprocessor.processor_input import ProcessorInput
from pathlib import Path

# Fournir les paramètres directement, au lieu d'un fichier d'entrée
input_params = ProcessorInput(job_id="j1", 
                              unit_id="ident",
                              # Obtient le chemin d'accès au dossier contenant ce fichier
                              input_folder=Path(__file__).parent,
                              indata_filename="indata.parq",
                              indata_hist_filename="C:\\full\\filepath\\to\\histdata.parq",
                              seed=1234, 
                              save_format=[".parq", ".csv"],
                              log_level=2)

# Méthode normale avec un fichier JSON
#my_bp = Processor("C:\\path\\to\\my\\processor_input.json")
# Méthode lors de la fourniture de paramètres en ligne
my_bp = Processor(input_params)
```

Remarques:

- Tous les emplacements de dossier peuvent être indiqués sous forme de chemins de fichiers absolus ou relatifs au dossier d'entrée (soit l'emplacement du fichier .json d'entrée, soit le paramètre input_folder fourni si vous créez des entrées en ligne comme indiqué ci-dessus).
- Cet emplacement input_folder est également utilisé comme emplacement par défaut pour d'autres fichiers requis par le processeur si aucune valeur n'est fournie pour eux, tels que les métadonnées, les fichiers de données d'entrée et les procédures définies par l'utilisateur
- Les chemins de fichiers doivent avoir des barres obliques inverses `\` échappées en les remplaçant par une double barre oblique inverse `\\`. Par exemple, `C:\this\is\a\filepath` deviendrait `C:\\this\\is\\a\\filepath`
- Les champs qui ne sont pas nécessaires à l'exécution des procédures décrites dans votre fichier de tâches peuvent être omis ou laissés vides
- Le format `CSV` a été inclus à des fins de test et n'est pas destiné à la production. Parquet est actuellement le format recommandé pour la production pour des raisons liées à la précision, aux performances et à l'efficacité

## Exécution du processeur en tant qu'utilitaire de ligne de commande

Avec le package banffprocessor installé dans votre environnement Python, le processeur peut être exécuté avec la commande suivante:

```shell
banffprocessor "\path\to\your\processor_input.json" -l fr
```

Alternativement pour exécuter en tant que module:

```shell
python -m banffprocessor.processor "\path\to\your\processor_input.json" --lang fr
```

- __NOTE__: Le paramètre '-l'/'--lang' est facultatif. Les valeurs valides sont en et fr. Si elles ne sont pas spécifiées, la valeur par défaut est en.

### Exécution du processeur à partir d'un script Python

```python
import banffprocessor

# Facultatif: définissez la langue sur fr pour que les messages du journal et de la console soient écrits en français.
banffprocessor.set_language(banffprocessor.SupportedLanguage.fr)

bp = banffprocessor.Processor.from_file("path\\to\\my\\input_file.json")
bp.execute()
bp.save_outputs()
```

Vous pouvez également charger vos fichiers de données d'entrée par programmation sous forme de Pandas DataFrames:

```python
from banffprocessor.processor import Processor
import pandas as pd

indata = pd.DataFrame()
indata_aux = pd.DataFrame()
instatus = pd.DataFrame()
...
# Chargez vos dataframes avec des données
...
bp = Processor.from_file(input_filepath="path\\to\\my\\input_file.json", indata=indata, instatus=instatus)
bp.execute()
bp.save_outputs()
```

## Procédures définies par l'utilisateur

En plus des procédures Banff standard automatiquement intégrées au processeur, vous pouvez également inclure vos propres fichiers `.py` implémentant des procédures personnalisées. Par défaut, le processeur recherchera les fichiers Python placés dans un sous-dossier `\plugins` au même emplacement que votre fichier JSON d'entrée. Vous pouvez également fournir un emplacement spécifique pour charger les plugins dans le paramètre `user_plugins_folder` de votre fichier JSON d'entrée. Vous pouvez fournir autant de fichiers de plugin que nécessaire pour votre travail, et chaque fichier de plugin peut contenir autant de classes de procédures que vous le souhaitez tant que chaque classe est enregistrée dans une méthode `register()`.

Votre plugin doit définir une classe qui implémente le protocole `ProcedureInterface` qui se trouve dans les fichiers sources du package à `\src\banffprocessor\procedures\procedure_interface.py`. Votre classe d'implémentation doit avoir exactement les mêmes noms d'attributs et les mêmes signatures de fonctions que l'interface. Voici un exemple de plugin qui implémente le protocole:

```python
class MyProcClass:
    
    @classmethod
    def execute(cls, processor_data) -> int:
        # Ceux-ci vous donnent des données sous forme de tableau pyarrow
        #indata = processor_data.indata
        #indata = processor_data.get_dataset("indata", ds_format="pyarrow")
        # Cela vous donne des données sous forme de Pandas DataFrame
        indata = processor_data.get_dataset("indata", ds_format="pandas")
        
        # Récupérez la variable utilisateur var1 à partir de la collection de métadonnées, par défaut un type `string»
        my_var1 = processor_data.current_uservars["var1"]   
        # Si la variable utilisateur est censée être numérique, nous devons la convertir
        #my_var1 = int(processor_data.current_uservars["var1"])
        
        # Créer un DataFrame outdata contenant les enregistrements indata avec la valeur d'identification R01
        outdata = pd.DataFrame(indata.loc[indata['ident'] == 'R01'])

        # Nous nous attendons à avoir au moins un enregistrement trouvé
        # Si ce n'est pas le cas, renvoyez 1 pour indiquer qu'une erreur s'est produite et que le travail doit se terminer.
        if(outdata.empty):
            return 1

        # Définissez le champ v1 dans les enregistrements récupérés pour qu'il contienne la valeur de la variable utilisateur
        outdata['v1'] = my_var1

        # Pour que le processeur mette à jour notre fichier imputé, nous devons définir le fichier de données de sortie 
        processor_data.outdata = outdata
        
        # Si nous y sommes parvenus, renvoyez 0 pour indiquer qu'il n'y a eu aucune erreur
        return 0

# Enregistre toutes les classes de plug-ins dans l'usine
# `myproc` est le même nom que vous fournirez dans les entrées de votre fichier Jobs comme 
# nom de processus, en utilisant la majuscule que vous souhaitez (c'est-à-dire mYpRoC, MyProc, myProc, etc.)
def register(factory) -> None:
    factory.register("myproc", MyProcClass)
    # You may provide multiple names for your proc, if you like
    #factory.register(["myproc", "also_myproc"], MyProcClass)
```

- Lorsque votre `execute()` est terminé, le processeur met automatiquement à jour le *status_file* et/ou le *imputed_file* avec le contenu des ensembles de données *outstatus*/*outdata* correspondants, si vous en avez défini un.
- Cette opération ne peut pas ajouter ou supprimer des données de votre *imputed_file*, elle ne peut que mettre à jour les enregistrements existants. Si vous avez besoin d'ajouter ou de supprimer des données de *imputed_file*, vous devez le faire dans votre plugin et définir `processor_data.indata` pour pointer vers vos données mises à jour. Cela enregistrera un avertissement dans votre fichier journal, mais il peut être ignoré si cela était prévu.

- De plus, le processeur ajoute automatiquement tous les autres ensembles de données que vous générez à partir d'un plug-in personnalisé à une seule version `cumulative` si le type de sortie du processus est défini sur `Tous` ou `Personnalisé` et que le nom de l'ensemble de données est spécifié dans une entrée de métadonnées ProcessOutput pour ce plug-in personnalisé

- La méthode `execute()` est marquée comme une méthode de classe, ce qui signifie que son premier argument `cls` est une référence à `MyProcClass`. Elle possède également un deuxième argument `processor_data` qui est un objet de type `ProcessorData` (dont la définition se trouve dans `src\banffprocessor\processor_data.py`). Cet objet comprend les fichiers d'entrée, les fichiers de sortie (à partir des procédures précédemment exécutées et de la procédure en cours), les métadonnées et les paramètres de votre fichier JSON d'entrée.
- Votre méthode `execute()` doit également renvoyer un `int` représentant le code de retour du plug-in. Tout nombre différent de 0 indique que le plugin n'a pas été exécuté avec succès et que le processeur doit arrêter de traiter les étapes suivantes de la stratégie d'imputation. Une exception peut également être levée.

- Enfin, le module de votre plugin doit implémenter une fonction `register()`, en dehors de toute définition de classe dans votre fichier de plugin. Cette fonction a un paramètre `factory`. La fonction doit appeler la fonction `register()` de l'objet factory, en fournissant le nom de votre procédure tel qu'il apparaîtra dans vos métadonnées et le nom de la classe qui l'implémente. Bien qu'un plugin par fichier soit recommandé, si vous avez plusieurs classes dans le même fichier qui implémentent l'interface de procédure Banff, vous pouvez les enregistrer toutes en utilisant la même fonction register. Incluez simplement un appel `factory.register(...)` pour chaque procédure de plugin que vous souhaitez enregistrer.

- __NOTE__: Le nom enregistré dans la factory est le même que celui que vous fournirez dans vos entrées Jobs comme nom du `process`. Les noms de processus ne sont pas sensibles à la casse.

Pour un exemple de travail qui inclut une procédure définie par l'utilisateur, voir `banffprocessor\banff-processor\tests\integration_tests\udp_test` avec le plugin situé dans `\plugins\my_plugin.py`.

## Contrôles de processus

__Note__: Les contrôles de processus sont une nouvelle fonctionnalité introduite avec la version 2.0.0 du processeur Python.

Les contrôles de processus sont des processus qui s'exécutent avant une étape d'imputation. Un exemple est un filtre appliqué aux données d'entrée ou au fichier d'état. Cela permet aux utilisateurs de définir des contrôles de processus qui permettent au processeur d'être plus générique, de réduire le nombre d'étapes dans une stratégie d'imputation et d'améliorer les informations fournies aux processus ultérieurs (SEVANI).

Cette fonctionnalité nécessite l'utilisation d'un nouveau champ dans le fichier de métadonnées Jobs, `controlid`. Ce champ fait référence à une entrée (ou à des entrées) dans un nouveau fichier de métadonnées, *processcontrols.xml* (produit à partir de la feuille de calcul PROCESSCONTROLS dans le modèle Excel):

|controlid|targetfile|paramètre|valeur|
|--|--|--|--|
|Identifie le contrôle ou l'ensemble de contrôles à appliquer aux étapes Jobs avec le même controlid|Le [nom du jeu de données](#noms-de-table-disponibles) auquel appliquer le contrôle (les noms doivent être écrits dans la même casse que celle dans laquelle ils apparaissent dans le tableau)|Le type de contrôle souhaité|Déterminé par le [type de contrôle](#types-de-contrôle)|
|_control1_|_indata_|_row_filter_|_strat > 15 et (rec_id not in (SELECT * FROM instatus WHERE status != 'FTI'))_|
|_control1_|_instatus_|_column_filter_|_IDENT, AREA, V1_|
|_control1_|_indata_|_exclude_rejected_|_True_|
|_control1_|_N/A_|_edit_group_filter_|_N/A_|

Tous les contrôles de processus avec le `controlid` spécifié sont appliqués à leurs `targetfile` respectifs pour l'étape de travail unique sur laquelle ils sont déclarés. Une fois l'étape de travail terminée, les `targetfile` affectés reviennent à leur état d'origine et le travail continue. Cependant, si l'étape de travail commence l'exécution d'un nouveau bloc de processus, le `targetfile` restera dans l'état créé par le(s) contrôle(s) de processus appliqué(s) pendant la durée du bloc de processus (et de tous les sous-blocs qu'il contient).

Un ID de contrôle peut être utilisé autant de fois que nécessaire par `targetfile`. Si un ID de contrôle est répété pour le même `targetfile` ET le même `parameter`, alors la `value` de ces contrôles est combinée en une seule. Cela a pour but de permettre une plus grande modularité dans les ensembles de contrôles, car les parties individuelles des conditions à plusieurs parties peuvent être interchangées à volonté sans affecter les autres parties.

### Types de contrôle

- ROW_FILTER
  - Filtre `targetfile` à l'aide d'une clause SQL WHERE
  - `value` - La condition SQL qui peut inclure des noms de colonnes et/ou des noms de tables (exactement comme indiqué dans [noms de tables disponibles](#noms-de-table-disponibles))
  - Si `controlid`, `targetfile` et `parameter` sont répétés pour plusieurs entrées, les conditions dans leurs champs `value` sont jointes par `AND`
- COLUMN_FILTER (peut en appliquer plusieurs pour un ID, les listes de noms de colonnes sont combinées en une seule)
  - Filtre les `targetfile` pour supprimer les colonnes qui n'apparaissent pas dans la liste dans le champ `value`
  - `value` - Une liste séparée par des virgules de noms de colonnes à CONSERVER dans `targetfile`
  - Si `controlid`, `targetfile` et `parameter` sont répétés pour plusieurs entrées, les listes de colonnes dans leurs champs `value` sont combinées
- EXCLUDE_REJECTED
  - Filtre `targetfile` en supprimant toutes les entrées avec un `unit_id` qui apparaît dans la table `outreject`
  - `value` - Le texte 'True' ou 'False', indiquant si le contrôle doit être appliqué ou non
  - Pour un `controlid`, un seul contrôle EXCLUDE_REJECTED peut être utilisé par `targetfile`
  - __NOTE__ Errorloc et Prorate produisent chacun des fichiers `outreject` légèrement différents.
    - Errorloc: `outreject`, produit par l'appel errorloc actuel, écrase tout fichier `outreject` existant. Le contenu de `outreject` est également ajouté à `outreject_all`.
    - Prorata: le contenu de l'ensemble de données `outreject` produit par l'appel de prorata actuel est ajouté à `outreject_all` et également ajouté à l'ensemble de données `outreject` existant (ou simplement défini comme la table `outreject` s'il n'en existe pas encore).
- EDIT_GROUP_FILTER
  - Filtre `instatus` en supprimant toutes les entrées avec un `editgroupid` correspondant à l'étape de travail actuelle OU toutes les entrées produites par une étape Outlier avec une valeur d'état de `FTI` ou `FTE`
  - Les champs `value` et `targetfile` ne doivent pas être indiqués pour ce type de contrôle
  - Remplace la fonctionnalité SAS existante où ce filtre était automatiquement appliqué avant d'exécuter une procédure `DonorImputation` ou `Deterministic`

- __NOTE__: les noms de colonnes de vos fichiers d'entrée d'origine doivent être référencés dans leur casse d'origine, ceux qui sont créés ou ajoutés par le processeur doivent être en MAJUSCULES.

### Noms de table disponibles

|Nom de la table|Notes|
|--|--|
|status_log|Contient tous les fichiers `outstatus` produits ajoutés dans l'ordre|
|indata|Les données d'entrée de l'étape de travail en cours. Alias: imputed_file|
|indata_aux|Les données d'entrée auxiliaires.|
|indata_hist|Les données d'entrée historiques.|
|instatus|Les données d'état d'entrée de l'étape de travail en cours. Alias: status_file|
|instatus_hist|Les données d'état d'entrée historiques.|
|time_store|Informations concernant le temps d'exécution et l'exécution de chaque étape d'un travail|
|outreject et outreject_all|Produits par Errorloc et Prorate|
|outedit_applic|Peut être produit par Editstats|
|outedit_status|Peut être produit par Editstats|
|outedits_reduced|Peut être produit par Editstats|
|outglobal_status|Peut être produit par Editstats|
|outk_edits_status|Peut être produit par Editstats|
|outvars_role|Peut être produit par Editstats|
|outacceptable|Peut être produit par Estimator|
|outest_ef|Peut être produit par Estimator|
|outest_lr|Peut être produit par Estimator|
|outest_parm|Peut être produit par Estimator|
|outrand_err|Peut être produit par Estimator|
|outmatching_fields|Produit par DonorImputation|
|outdonormap|Produit par DonorImputation et MassImputation|
|outlier_status|Peut être produit par Outlier|

- Les jeux de données facultatifs ne sont disponibles pendant l'exécution et enregistrés sur le disque que si le paramètre d'entrée process_output_type est défini sur `All` (2) ou si le nom du jeu de données est spécifié dans une entrée de table de métadonnées ProcessOutput pour le processus qui le produit et process_output_type est défini sur `Custom` (3)
- Le nom de la table ou son alias peuvent être utilisés, les deux font référence à la même table et aux mêmes données
- Les fichiers indata et instatus sont toujours disponibles
- Si instatus est la première étape d'un travail qui ne fournit pas de fichier instatus pour commencer, il n'est pas disponible pour être utilisé dans un filtre pour la première étape, bien qu'il soit disponible dans les étapes suivantes
- Tout fichier spécifique à une procédure n'est pas disponible pour référence jusqu'à ce qu'une étape de travail pour cette procédure ait été exécutée dans une étape précédente, et uniquement si le fichier référencé est produit selon le `process_output_type`
- Tous les fichiers auront les colonnes SEQNO et JOBID ajoutées. Celles-ci peuvent être filtrées pour obtenir des données d'une étape de travail spécifique.
- Le champ `value` prend en charge les références aux tables situées sur le disque ainsi que les noms de tables en mémoire mentionnés ci-dessus
  - Ceci ne s'applique pas à `targetfile`, qui doit être une table en mémoire référencée par son nom.
  - Le chemin d'accès au fichier doit être absolu ou relatif au Répertoire de Travail Actuel (Python CWD) du processus python qui exécute le processeur.
  - Le chemin d'accès au fichier doit être entre guillemets simples, par exemple:  
  `ident in (SELECT ident FROM '.\subfolder\of\input_folder\idents.csv')`
  - Voir [DuckDB docs] (https://duckdb.org/docs/stable/data/overview) pour des informations sur les types de fichiers pris en charge (par exemple, seul '.parquet' est pris en charge, PAS '.parq').

## Blocs de processus

__Note__: Les blocs de processus sont une nouvelle fonctionnalité introduite dans la version 2.0.0 du processeur Python.

Un travail dans le processeur Banff est un ensemble d'entrées de table de métadonnées de travaux, toutes reliées par un identifiant de travail commun (jobid) et traitées séquentiellement selon le numéro de séquence (seqno). Un seul travail est spécifié lors de l'exécution du processeur, ce qui est fait en spécifiant le paramètre d'entrée `job_id`. Un bloc de processus est essentiellement un travail appelé à partir d'un travail. Les blocs de processus organisent les travaux en sous-travaux avec les objectifs suivants:

- permettre à un contrôle de processus d'être associé à plusieurs étapes de travail.
- permettre la réutilisation d'une séquence d'étapes répétées avec différentes entrées.
- permettre aux utilisateurs de concevoir et de mettre en œuvre des stratégies d'imputation à l'aide d'une approche modulaire. Cela signifie que des travaux plus petits peuvent être développés et testés de manière isolée plutôt que d'avoir un seul gros travail.

Les blocs de processus sont utilisés en définissant le champ *process* d'une entrée de table de métadonnées Jobs sur `job` (plutôt qu'une procédure Banff traditionnelle telle que `prorate` ou `donorimputation`) et en définissant le champ *specid* comme étant le `jobid` du bloc de processus à exécuter.

Les blocs de processus peuvent appeler d'autres blocs de processus, offrant ainsi une plus grande flexibilité. Lors de la préparation de l'exécution du `Processor` de Banff, les métadonnées Jobs sont validées à l'aide du paramètre d'entrée `job_id` comme racine de la structure globale du travail. Cette validation garantit qu'aucun cycle (boucle infinie) n'existe lorsque le travail comporte des blocs de processus imbriqués. Si un cycle est trouvé, une erreur sera imprimée sur la console et/ou dans le fichier journal et le problème devra être corrigé afin d'exécuter le travail avec succès.

|jobid|seqno|controlid|process|specid|editgroupid|byid|acceptnegative|
|--|--|--|--|--|--|--|--|
|main_job|1|*n/a*|job|sub_job|*n/a*|*n/a*|*n/a*|
|main_job|2|*n/a*|outlier|outlier_spec1|*n/a*|*n/a*|*n/a*|
|main_job|3|*n/a*|job|sub_job|*n/a*|*n/a*|*n/a*|
|sub_job|1|*n/a*|prorate|prorate_spec1|*n/a*|*n/a*|*n/a*|
|sub_job|2|*n/a*|donorimp|donorimp_spec1|*n/a*|*n/a*|*n/a*|

Par exemple, le tableau Jobs ci-dessus entraînerait l'exécution de:

1. prorate (sub_job, 1)
2. donorimp (sub_job, 2)
3. outlier (main_job, 2)
4. prorate (sub_job, 1)
5. donorimp (sub_job, 2)

Un exemple fonctionnel d'une tâche avec un bloc de processus peut être trouvé dans le répertoire du projet sous 'examples/example4'.

## Les Sorties

### Sauvegarde des sorties

Si l'exécution se fait à partir d'un script Python, les ensembles de données de sortie peuvent être enregistrés sur le disque en appelant la fonction `save_outputs()` de l'objet `banffprocessor` contenant les résultats d'un appel à `execute()`. Si l'exécution se fait à partir de la ligne de commande, `save_outputs()` sera appelé automatiquement une fois que le processeur aura terminé une tâche.

Pendant l'opération, si aucun paramètre `output_folder` n'est fourni, le processeur créera un dossier `out` au même emplacement que votre fichier de paramètres JSON d'entrée pour enregistrer le journal Banff ainsi que les fichiers d'état et de données de sortie créés pendant et après l'exécution de chaque procédure Banff. Les fichiers d'état et de données seront enregistrés au format déterminé par:

1. Le paramètre `saveFormat` dans votre fichier JSON d'entrée
2. Si aucune valeur n'est fournie pour 1., utilise le même format que le fichier dans `indata_filename`
3. Si ni 1. ni 2. ne sont fournis, la valeur par défaut est le format `.parq`

### Fichiers/ensembles de données de sortie

Les fichiers de sortie de chaque procédure peuvent être conservés et enregistrés. Le processeur ajoutera automatiquement les colonnes `JOBID` et `SEQNO` aux sorties. Lorsqu'une sortie portant le même nom est générée et conservée, le processeur ajoutera ces ensembles de données de sortie ensemble et les ensembles de données devront être filtrés par `JOBID` et `SEQNO` pour limiter les données à une étape de traitement spécifiée.

#### Tableaux de sortie minimale

|Fichier de données|Description|
|--|--|
|imputed_file|Ce fichier de données contient les données actuelles imputées finales.|
|status_file|Ce fichier de données contient les statuts des données imputées finales.|
|status_log|Ce fichier de données contient l'historique de la façon dont les statuts ont changé pendant la stratégie d'imputation.|
|outreject|Ce fichier de données est généré par les procédures ErrorLoc et Prorate. Il contient l'identification des répondants qui n'ont pas pu être traités et la raison pour laquelle.|
|time_store|Ce fichier de données stocke l'heure de début, l'heure de fin et la durée de chaque étape de traitement ainsi que le temps d'exécution cumulé.|

#### Sorties optionnelles

|Fichier de données|Procédure associée|Description|
|--|--|--|
|outlier_status|Valeur aberrante|Il contient le fichier d'état final incluant les variables supplémentaires de l'option `outlier_stats` (qui est toujours en vigueur dans le processeur Banff).|
|outmatching_fields|Imputation du donneur|Il contient l'état des champs correspondants de l'option `outmatching_fields` (qui est toujours en vigueur dans le processeur Banff).|
|outdonormap|Imputation du donneur|Il contient les identifiants des destinataires qui ont été imputés ainsi que leur identifiant de donneur et le nombre de donneurs essayés avant que le destinataire ne passe les modifications post-imputation.|
|outedits_reduced|EditStats|Ce fichier de données contient l'ensemble minimal de modifications.|
|outedit_status|EditStats|Ce fichier de données contient le nombre d'enregistrements qui ont réussi, manqué et échoué pour chaque modification.|
|outk_edits_status|EditStats|Ce fichier de données contient la distribution des enregistrements qui ont réussi, manqué et échoué K modifications.|
|outglobal_status|EditStats|Ce fichier de données contient le nombre total d'enregistrements réussis, manqués et échoués.|
|outedit_applic|EditStats|Ce fichier de données contient le nombre d'applications de modification de statut réussi, manqué ou échoué qui impliquent chaque champ.|
|outvars_role|EditStats|Ce fichier de données contient le nombre d'enregistrements de statut réussi, manqué ou échoué pour lesquels le champ j a contribué au statut global de l'enregistrement.|
|outrand_err|Estimator|Cet ensemble de données contient le rapport d'erreur aléatoire si au moins une des spécifications d'estimateur a la variable `RANDOMERROR` dans la table de métadonnées ESTIMATOR définie sur `Y`.|
|outest_ef|Estimator|Cet ensemble de données contient le rapport sur le calcul des moyennes pour les fonctions d'estimateur si au moins une des spécifications d'estimateur utilise une fonction d'estimateur (type EF).|
|outest_parm|Estimator|Cet ensemble de données contient le rapport sur les statistiques d'imputation par estimateur.|
|outest_lr|Estimateur|Cet ensemble de données contient le rapport sur le calcul des coefficients `beta` pour les estimateurs de régression linéaire si au moins une des spécifications de l'estimateur utilise une régression linéaire (type LR).|
|outacceptable|Estimateur|Ce fichier de données contient le rapport sur les observations acceptables retenues pour calculer les paramètres de chaque estimateur donné dans les spécifications. Ce fichier peut être volumineux et peut ralentir l'exécution.|

Remarques:

- Reportez-vous au Guide de l'utilisateur de la procédure Banff pour une description complète d'un fichier généré par une procédure Banff.
- Les fichiers de sortie facultatifs seront conservés si process_output_type = `all` ou si process_output_type = `custom` et que le nom du jeu de données est spécifié dans les métadonnées ProcessOutputs pour le processus donné.
- Les plugins peuvent générer des fichiers de sortie facultatifs supplémentaires.

### Le journal

Le processeur Python peut générer un journal d'exécution qui fournit des informations précieuses sur le processus d'imputation, utiles à des fins de débogage et d'analyse. Le niveau d'informations enregistrées peut être configuré via le paramètre `log_level` de votre fichier JSON d'entrée.

- Si 0, aucun fichier journal n'est produit, seuls les avertissements, les erreurs et un résumé de chaque procédure sont écrits sur la console après son exécution. Ce résumé est toujours imprimé, même aux niveaux 1 et 2.

- Si 1 (la valeur par défaut si `log_level` n'est pas définie), le fichier journal contient des messages de niveau INFO, qui sont principalement la sortie de l'exécution de chaque procédure du package Banff, ainsi que des avertissements et des erreurs.

- Enfin, si 2, le fichier journal contient tous les messages de 1 ainsi que tous les messages de niveau DEBUG, tels que des informations plus détaillées sur les ensembles de données produits et traités.

Le processeur conserve un maximum de 6 fichiers journaux à la fois. Le travail le plus récent est toujours enregistré dans `banffprocessor.log` et lorsqu'un nouveau travail est exécuté, un numéro est ajouté à l'ancien fichier journal et un nouveau journal est créé pour le nouveau travail. La numérotation va du plus récent au plus ancien (c'est-à-dire que `banffprocessor.log` est le journal du travail le plus récent, `banffprocessor.log.1` est celui du travail le plus récent et `banffprocessor.log.5` est celui du travail le plus ancien).

### Sortie du bloc de processus

Lorsqu'un nouveau bloc de processus doit être exécuté, un dossier spécial est créé dans le dossier de sortie pour le bloc appelant. Ce nouveau dossier de sortie est nommé d'après les paramètres du nouveau bloc et, une fois le bloc terminé, il contiendra tous les fichiers créés par le bloc enfant. Cependant, aucun nouveau fichier journal n'est créé. Toutes les sorties de journal des blocs enfants se trouvent dans le fichier journal principal qui se trouve dans le dossier d'entrée racine.
