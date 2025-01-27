[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![GitHub Scan](https://github.com/StatCan/gensol-banff-processor/actions/workflows/scan.yml/badge.svg?event=release&status=success)](https://github.com/StatCan/gensol-banff-processor/actions/workflows/scan.yml?query=event%3Arelease+is%3Asuccess)
[![GitHub Build](https://github.com/StatCan/gensol-banff-processor/actions/workflows/build.yml/badge.svg?event=release&status=success)](https://github.com/StatCan/gensol-banff-processor/actions/workflows/build.yml?query=event%3Arelease+is%3Asuccess)

[(Le message en français suit)](#aperçu)

# Banff Processor

Welcome to the project repository for the Banff Processor, please consider watching this repo to be notified of updates.

## Overview

The Banff Processor is part of the Banff project. It is a tool that can be installed in addition to the Banff Procedure package. This tool is used to implement an imputation strategy, which is essentially a sequence of processing steps. A processing step can be a standard Banff Procedure, a user-defined process (plugin) or a process block (another sequence of processing steps). 

Imputation strategies are defined using XML files, an Excel template has been provided along with a utility to convert metadata created with the template to the XML files required by the processor. The output of a processor job is the imputed file along with a log and various status and optional diagnostic files.

## Project Overview

The Banff Processor was originally written in SAS 9 using the SAS macro language. In 2023-24, the Banff Processor was redeveloped as a python package and released as version 2. New features were added such as Process Controls and Process Blocks.

## Installation

The Banff Processor package is installed using the `pip` package installer for Python. For general information about `pip`, please see https://pip.pypa.io/en/stable/cli/pip_install/.

You can find the Banff Processor packages on Statistics Canada’s GitHub release page : https://github.com/StatCan/gensol-banff-processor/releases. A PyPI release will be available soon.

Download the binary artifact from the release page. Then, follow the installation instructions below :

```shell
pip install --no-cache-dir package_name.whl 
```

## Handling of Sensitive Statistical Information

Please respect your organization's policies regarding the handling for Sensitive Statistical Information. Output files may require encryption and need to stored in a secure location. The consumer of the package is responsible for ensuring sensitive data is processed in a secure environment.

## Documentation

For details on the Banff Processor, please see our [user guide](./docs/en/processor-user-guide.md).

Users familiar with the SAS version of Banff, our [migration guide](./docs/en/migrating-from-sas-python.md) will be helpful.

## Testing

In our source code repository, we have integration and unit tests which were developed and run with the [pytest](https://pypi.org/project/pytest/) package. A testing module has been developed in the banff package which we used in our tests and you can use too. 

### Sample Code

Examples have been included for both the Banff Processor and the Metadata Conversion Tool which can be downloaded and run. Examples can be found [here](./examples).

## Providing Feedback

Feedback is always welcome. Please submit an issue if you find a bug, have a suggestion or questions.

[Issues](https://github.com/StatCan/gensol-banff-processor/issues)

## More Information

- Banff was presented at United Nations Economic Commission for Europe (UNECE) conference in October of 2024. The presentation is available [here](https://unece.org/statistics/documents/2024/10/working-documents/paper-presentation-building-new-banff-open-source)
- The Banff often uses terminology from the [Generic Statistical Data Editing Model (GSDEM)](https://unece.org/fileadmin/DAM/stats/documents/ece/ces/ge.58/2020/mtg1/SDE2020_T4_GSDEM_Kilchmann_Presentation.pdf). Users are encouraged to reference the GSDEM for common terminology regarding statistical data editing concepts.

---
# Processeur Banff

Bienvenue dans le référentiel du projet pour le processeur Banff, veuillez envisager de surveiller ce référentiel pour être informé des mises à jour.

## Aperçu

Le processeur Banff fait partie du projet Banff. Il s'agit d'un outil qui peut être installé en complément du package Banff Procedure. Cet outil permet de mettre en œuvre une stratégie d'imputation, qui est essentiellement une séquence d'étapes de traitement. Une étape de traitement peut être une procédure Banff standard, un processus défini par l'utilisateur (plugin) ou un bloc de processus (une autre séquence d'étapes de traitement).

Les stratégies d'imputation sont définies à l'aide de fichiers XML. Un modèle Excel a été fourni avec un utilitaire permettant de convertir les métadonnées créées avec le modèle en fichiers XML requis par le processeur. Le résultat d'une tâche de processeur est le fichier imputé accompagné d'un journal et de divers fichiers d'état et de diagnostic facultatifs.

## Aperçu du projet

Le processeur Banff a été initialement écrit en SAS 9 à l'aide du langage macro SAS. En 2023-24, le processeur Banff a été redéveloppé sous forme de package Python et publié en version 2. De nouvelles fonctionnalités ont été ajoutées, telles que les contrôles de processus et les blocs de processus.

## Installation

Le paquet Banff Processor est installé à l'aide du programme d'installation du paquet `pip` de Python. Pour de l'information générale sur `pip`, veuillez consulter https://pip.pypa.io/en/stable/cli/pip_install/.

Vous pouvez trouver le package Banff Processor sur la page de publication GitHub de Statistique Canada : https://github.com/StatCan/gensol-banff-processor/releases. Une version PyPI sera bientôt disponible.

Téléchargez le binaire depuis la page de publication. Ensuite, suivez les instructions d’installation ci-dessous :

```shell
pip install --no-cache-dir package_name.whl 
```

## Traitement des informations statistiques sensibles

Veuillez respecter les politiques de votre organisation concernant le traitement des informations statistiques sensibles. Les fichiers de sortie peuvent nécessiter un cryptage et doivent être stockés dans un emplacement sécurisé. Le consommateur du package est responsable de s'assurer que les données sensibles sont traitées dans un environnement sécurisé.

## Documentation

Pour plus de détails sur le processeur Banff, veuillez consulter notre [guide d'utilisation](./docs/en/processor-user-guide.md).

Pour les utilisateurs familiarisés avec la version SAS de Banff, notre [guide de migration sera utile](./docs/en/(./docs/en/usage.md).md).

## Tests

Dans notre référentiel de code source, nous avons des tests d'intégration et des tests unitaires qui ont été développés et exécutés avec le package [pytest](https://pypi.org/project/pytest/).

## Exemple de code

Des exemples ont été inclus pour le processeur Banff et l'outil de conversion des métadonnées qui peuvent être téléchargés et exécutés. Des exemples peuvent être trouvés [ici](./examples).

## Fournir des commentaires

Vos commentaires sont toujours les bienvenus. N'hésitez pas à nous soumettre un problème si vous trouvez un bug, si vous avez une suggestion ou des questions.

[Problèmes](https://github.com/StatCan/gensol-banff-processor/issues)

## Plus d'informations

- Banff a été présenté à la conférence de la Commission économique des Nations Unies pour l'Europe (UNECE) en octobre 2024. La présentation est disponible [ici](https://unece.org/statistics/documents/2024/10/working-documents/paper-presentation-building-new-banff-open-source)
- Le Banff utilise souvent la terminologie du [Modèle générique d'édition de données statistiques(GSDEM)](https://unece.org/fileadmin/DAM/stats/documents/ece/ces/ge.58/2020/mtg1/SDE2020_T4_GSDEM_Kilchmann_Presentation.pdf). Les utilisateurs sont encouragés à se référer au GSDEM pour la terminologie commune concernant les concepts d'édition de données statistiques.
