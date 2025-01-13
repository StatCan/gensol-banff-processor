# Banff Processor User Guide

## Introduction

The Banff Processor is a Python package used to execute a Statistical Data Editing (SDE) process, also commonly referred to as Edit and Imputation (E&I). A specific SDE process typically consists of numerous individual process steps, each executing a SDE function such as error localization, outlier detection, or imputation. The process flow describes which process steps to perform and the sequence in which they are executed. Given a set of input metadata tables that describe the SDE process flow, including each individual step, the Banff processor executes each process step in sequence, managing all intermediate data management. The advantage of the Banff Processor's metadata-driven system is that the design and modification of the SDE process is managed from metadata tables instead of source code.

Other notes about the Banff Processor:

- Simplicity: Once the metadata tables are created, the processor can be executed from a single line of code
- Efficiency: Designed for production-level SDE processes
- Modularity: Within a process step, users may call the built-in Banff procedures, or [user defined Procedures](#user-defined-procedures)
- Flexibility: [Process Controls](#process-controls) and [Process Blocks](#process-blocks) allow users to specify complex process flows
- Informative: The Processor produces diagnostics from each step, and for the overall process
- Transparency: Source code is available and freely shared

The user guide often uses terminology from the [Generic Statistical Data Editing Model (GSDEM)](https://statswiki.unece.org/spaces/sde/pages/117771706/GSDEM). Users are encouraged to reference the GSDEM for common terminology regarding SDE concepts.

## Table of Contents

- [Input Metadata Files](#input-metadata-files)
- [Metadata Generation Tool](#metadata-generation-tool)
- [Input Parameters](#banff-processor-input-parameters)
- [Executing the processor as a command line utility](#executing-the-processor-as-a-command-line-utility)
- [Executing the processor from within a python process ](#executing-the-processor-from-within-a-python-process)
- [User Defined Procedures](#user-defined-procedures)
- [Process Controls](#process-controls)
- [Process Blocks](#process-blocks)
- [Output](#output)

## Input Metadata Files

The Banff Processor is driven by metadata tables describing both the overall process flow, as well as the parameters required for individual process steps. The primary metadata table is called JOBS, which specifies the overall process flow, specifically the built-in Banff procedures and/or user-defined programs (plugins) to execute and their relative sequencing. The JOBS table can contain more than one job (i.e., process flow), specified by the `jobid` (job identifier), though only one job can be executed at a time by the Banff Processor. Each job will include one row per process step; the key columns are:

- `jobid`: Job identifier.
- `seqno`: Sequence number of the individual process steps.
- `process`: Name of either the built-in procedure or user-defined program to execute at each process step.
- `specid`: Specification identifier, linking to other metadata tables containing parameters specific to the declared `process`.

Additional columns on the JOBS table include an optional process control identifier (`controlid`) as well as parameters that are common to multiple procedures (`editgroupid`,`byid`,`acceptnegative`).

Overall, the Banff Processor uses 18 metadata tables, which can be classified as follows:

- Tables describing the overall process flow: `JOBS` `PROCESSCONTROLS`
- Process step parameters for built-in Banff procedures: `VERIFYEDITSPECS` `OUTLIERSPECS` `ERRORLOCSPECS` `DONORSPECS` `ESTIMATORSPECS` `ESTIMATORS` `ALGORITHMS` `PRORATESPECS` `MASSIMPUTATIONSPECS`
- Process step parameters for [User Defined Procedures](#user-defined-procedures): `USERVARS`
- Tables used to define edits: `EDITS` `EDITGROUPS`
- Parameters used by multiple procedures: `VARLISTS` `WEIGHTS` `EXPRESSIONS`
- Data management: `PROCESSOUTPUTS`

Only the JOBS table is mandatory, though other tables are required depending on which procedures or options are used. A full description of all metadata tables is included in this document: [Metadata Tables](metadata-tables.md)

### Formatting

The metadata tables must be saved in `.xml` format. Users may create the `.xml` files on their own, or use the [Banff Processor Template](../../banffprocessor_template.xlsx) to create and save the metadata, and the [Metadata Generation Tool](#metadata-generation-tool) to convert the template file into `.xml` tables. By default, the Processor will look for the XML files in the same location as your `.json` input file, either directly in the same folder or in a `\metadata` subfolder. Alternatively, you may provide a specific location by setting the `metadata_folder` parameter in your input JSON file.

### Example (JOBS table)

The following table defines a single job, "Main", which includes four process steps.

| jobid | seqno | controlid | process       | specid       | edigroupid | byid    | acceptnegative |
| ----- | ----- | --------- | ------------- | ------------ | ---------- | ------- | -------------- |
| Main  | 1     |           | ERRORLOC      | errloc_specs | edits_1    |         | Y              |
| Main  | 2     |           | DETERMINISTIC |              | edits_1    |         | Y              |
| Main  | 10    |           | DONORIMP      | donor_specs  | edits_1    | by_list | Y              |
| Main  | 99    |           | PRORATE       | pro_specs    | edits_2    |         | Y              |

* Only the ordering of the sequence numbers (`seqno`) are important; they do not need to be sequential integers.
* This job includes four process steps, run sequentially, consisting of four built-in Banff procedures: `errorloc`, `deterministic`, `donorimp`, and `prorate`.
* The parameters `editgroupid`, `byid` and `acceptnegative`, which are common to many of the built-in Banff procedures, are included in the JOBS table.
* Most procedures include mandatory and/or optional parameters that define exactly how the procedure should be executed. These are contained in additional metadata tables, and linked to specific process steps via the `specid` column. Procedures that do not have any additional parameters (beyond those included in the JOBS table) do not require a `specid`.
* The `controlid` column is optional, and can be used to specify [Process Controls](#process-controls).

Additional examples can be found [here](../../examples).

## Metadata Generation Tool

Metadata stored in the [Banff Processor Template](../../banffprocessor_template.xlsx) must be converted to XML files before running the processor. A conversion tool is provided for this purpose. With the banffprocessor package installed in your python environment, the conversion tool can be run with the following command:
<!--CLI documentation: (not sure how to document BOTH long and short flag if they have a value)-->
<!--banffconvert INPUT-FILE [--outdir=OUTPUT-FOLDER, -o OUTPUT-FOLDER]-->

```shell
banffconvert "\path\to\your\excel_metadata.xlsx" -o "\my\output\directory" -l fr
```
or:
```shell
banffconvert "\path\to\your\excel_metadata.xlsx" --outdir="\my\output\directory" --lang en
```

Alternatively to run as a module:
```shell
python -m banffprocessor.util.metadata_excel_to_xml "\path\to\your\excel_metadata.xlsx" -o "\my\output\directory"
```
* __NOTE__: The '-o'/'--outdir' parameter is optional. If it is not provided the conversion tool will save XML files to the same directory as the input file.
* __NOTE__: The '-l'/'--lang' parameter is optional. Valid values include en and fr, if not specified, the default is set to en.

Finally, the tool can be included and ran directly in a python script:

```python
import banffprocessor.util.metadata_excel_to_xml as e2x

e2x.convert_excel_to_xml("\\path\\to\\your\\excel_metadata.xlsx", "\\my\\output\\directory")
```

## Banff Processor Input Parameters

Input parameters are specified in a `.json` file or a `ProcessorInput` object, either of which are passed to the processor and used to specify your job's parameters. These are the parameters that are currently available:

|Name|Purpose|Required?|
|--|--|--|
|job_id|The job id from your `jobs.xml` you wish to run.|Y|
|unit_id|The unit id variable is the unique identifier on micro data files for the job|Y|
|indata_filename|The filename or full filepath of your input/current data file|Y (unless running only *VerifyEdits*)|
|auxdata_filename|The filename or full filepath of your auxiliary data file|N|
|histdata_filename|The filename or full filepath of your historic data file|N|
|histstatus_filename|The filename or full filepath of your historic status data file|N|
|instatus_filename|The filename or full filepath of a status file to use as input to the first proc in your job requiring a status file. [^1]|N|
|user_plugins_folder|The optional location of the folder containing your custom python procedure plugins. *See below for a description of how to create your own plugins*|N|
|metadata_folder|The optional path to a folder where your XML metadata can be found|N|
|output_folder|The optional path to a folder where your output files will be saved|N|
|process_output_type|Controls the output datasets retained by each process. Options include `all`, `minimal` and `custom`. When `all` is specified all outputs are retained. If `minimal` is specified, only the imputed_file, status_file and status_log are retained. When the value is 'custom', the processor looks at the `ProcessOutputs` metadata to determine what to keep. |N|
|seed|The seed value to use for consistent results when using the same input data and parameters|N|
|no_by_stats| If specified, determines if no_by_stats is set to True when calling standard procedures. |N|
|randnumvar|Specify a random number variable to be used when having to make a choice during error localization or donor imputation. This parameter is optional and is only used by ErrorLoc and DonorImputation simultaneously (it cannot be used in one and not the other). Please see the Banff User Guide document for more details on the use of the `randnumvar` option in the ErrorLoc and DonorImputation procedures.<br><br>This option can be helpful when one needs to get the same error localization or imputation results from one run to the next.|N|
|save_format|Optional list of file extensions used to determine the format to save output files in. One or more may be provided. Currently supports CSV and Parquet extensions.|N|
|log_level|Configures whether or not to create a log file and what level of messages it should contain. Value should be 0, 1 (default) or 2. See [Output](#output).|N|

[^1]: If no `JOBID` or `SEQNO` column is found in the file, they are added and their values are initialized to the input parameter `job_id` and 0 respectively. If they are present, any records with a missing `JOBID` or `SEQNO` or any records with a JOBID that is also found in your current Jobs metadata will have the values of both `JOBID` and `SEQNO` changed to NaN.

Example JSON input file:

```json
{
    "job_id": "j1",
    "unit_id": "ident",
    "indata_filename": "indata.parq",
    "auxdata_filename": "C:\\full\\filepath\\to\\auxdata.parq",
    "histdata_filename": "histdata.parq",
    "histstatus_filename": "histstatus.parq",
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

Example building a `ProcessorInput` object inline:

```python
from banffprocessor.processor import Processor
from banffprocessor.processor_input import ProcessorInput
from pathlib import Path

# Supplying parameters directly, instead of an input file
input_params = ProcessorInput(job_id="j1", 
                              unit_id="ident",
                              # Gets the path to the folder containing this file
                              input_folder=Path(__file__).parent,
                              indata_filename="indata.parq",
                              histdata_filename="C:\\full\\filepath\\to\\histdata.parq",
                              seed=1234, 
                              save_format=[".parq", ".csv"],
                              log_level=2)

# Normal method with a JSON file
#my_bp = Processor("C:\\path\\to\\my\\processor_input.json")
# Method when providing parameters inline
my_bp = Processor(input_params)
```

Notes: 
* All folder locations may be given as absolute filepaths or relative to the input folder (either the location of the input .json file or the supplied input_folder parameter if creating inputs inline as demonstrated above).
  * This input_folder location is also used as the default location for other files required by the processor should no value be provided for them, such as metadata, input data files and user-defined procedures
* File paths must have any backslashes `\` escaped by replacing them with a double-backslash `\\`. For example, `C:\this\is\a\filepath` would become `C:\\this\\is\\a\\filepath`
* Fields that are not required to run the procedures outlined in your jobs file can be omitted or left empty
* The `CSV` format has been included for testing purposes and is not intended for production, parquet is currently the recommended format for production for reasons related to accuracy, performance and efficiency
  

## Executing the processor as a command line utility
With the banffprocessor package installed in your python environment, the processor can be run with the following command:
```shell
banffprocessor "\path\to\your\processor_input.json" -l fr
```
Alternatively to run as a module:
```shell
python -m banffprocessor.processor "\path\to\your\processor_input.json" --lang fr
```

* __NOTE__: The '-l'/'--lang' parameter is optional. Valid values include en and fr, if not specified, the default is set to en.

### Executing the processor from within a python script
```python
import banffprocessor

# Optional: Set the language to fr so that log and console messages on written in French.
banffprocessor.set_language(banffprocessor.SupportedLanguage.fr)

bp = banffprocessor.Processor.from_file("path\\to\\my\\input_file.json")
bp.execute()
bp.save_outputs()
```

Alternatively, you may load your input data files programmatically as Pandas DataFrames:
```python
from banffprocessor.processor import Processor
import pandas as pd

indata = pd.DataFrame()
indata_aux = pd.DataFrame()
instatus = pd.DataFrame()
...
# Load your dataframes with data
...
bp = Processor.from_file(input_filepath="path\\to\\my\\input_file.json", indata=indata, instatus=instatus)
bp.execute()
bp.save_outputs()
```

## User-Defined Procedures
In addition to the standard Banff Procedures automatically integrated into the processor, you may also include your own `.py` files implementing custom procedures. By default the Processor will look for python files placed in a `\plugins` subfolder in the same location as your input JSON file. Alternatively you may provide a specific location to load plugins from in the `user_plugins_folder` parameter of your input JSON file. You may provide as many plugin files as needed for your job, and each plugin file may contain as many procedure classes as you wish so long as each class is registered in a `register()` method.

Your plugin must define a class that implements the `ProcedureInterface` protocol which is found in the package's source files at 
`\src\banffprocessor\procedures\procedure_interface.py`. Your implementing class must have the exact same attribute names and function signatures as the interface does. Here is an example of a plugin that implements the protocol:
```python
class MyProcClass:
    
    @classmethod
    def execute(cls, processor_data) -> int:
        # These give you indata as a pyarrow Table
        #indata = processor_data.indata
        #indata = processor_data.get_dataset("indata", ds_format="pyarrow")
        # This gives you indata as a Pandas DataFrame
        indata = processor_data.get_dataset("indata", ds_format="pandas")
        
        # Get the uservar var1 from the metadata collection, by default a string
        my_var1 = processor_data.current_uservars["var1"]   
        # If our uservar is supposed to be numeric we would need to cast it
        #my_var1 = int(processor_data.current_uservars["var1"])
        
        # Create an outdata DataFrame containing the indata record(s) with ident value R01
        outdata = pd.DataFrame(indata.loc[indata['ident'] == 'R01'])

        # We are expecting to have at least one record found
        # If we don't, return 1 to indicate there was an error and the job should terminate
        if(outdata.empty):
            return 1

        # Set the v1 field in the retrieved record(s) to contain uservar value
        outdata['v1'] = my_var1

        # In order for the processor to update our imputed_file we need to set the outdata file  
        processor_data.outdata = outdata
        
        # If we made it here return 0 to indicate there were no errors
        return 0

# Registers all plugin classes to the factory
# "myproc" is the same name you will provide in your Jobs file entries as 
# the process name, using any capitalization you want (i.e. mYpRoC, MyProc, myProc etc.)
def register(factory) -> None:
    factory.register("myproc", MyProcClass)
    # You may provide multiple names for your proc, if you like
    #factory.register(["myproc", "also_myproc"], MyProcClass)
```

* When your `execute()` is complete, the processor automatically updates the *status_file* and/or *imputed_file* with the contents of the corresponding *outstatus*/*outdata* datasets, if you have set one.
    * This operation is unable to add or remove data from your *imputed_file*, it can only update existing records. If you have a need to add or remove data from *imputed_file* you must do so in your plugin and set `processor_data.indata` to point to your updated data. This will log a warning in your log file, but it can be ignored if this was intended.

* Additionally, the processor automatically appends any other datasets you output from a custom plugin to a single "cumulative" version if the process_output_type is set to "All" or "Custom" and the dataset name is specified in a ProcessOutput metadata entry for that custom plugin

* The `execute()` method is marked as a classmethod, which means it is first argument `cls` is a reference to `MyProcClass`. It also has a second argument `processor_data` which is an object of type `ProcessorData` (the definition of which can be found in `src\banffprocessor\processor_data.py`). This object includes input files, output files (from previously ran procedures and the current procedure), metadata and parameters from your input JSON file.
    * Your `execute()` method should also return an `int` representing the return code of the plugin. Any non-0 number indicates that the plugin did not complete successfully and that the processor should stop processing subsequent steps in the imputation stategy, alternately an exception can be raised.

* Finally your plugin's module must implement a `register()` function, outside of any class definitions in your plugin file. This function has one parameter `factory`. The function must call the `register()` function of the factory object, providing the name of your procedure as it will appear in your metadata and the name of the class that implements it. Though one plugin per file is recommended, if you have multiple classes in the same file that implement the Banff Procedure Interface, you can register all of them using the same register function. Just include a `factory.register(...)` call for each plugin procedure you would like to register.
    * __NOTE__: The name registered to the factory is the same name that you will provide in your Jobs entries as the name of the `process`. Process names are not case sensitive.

For an example of a job that includes a user-defined procedure see `banffprocessor\banff-processor\tests\integration_tests\udp_test` with the plugin located in `\plugins\my_plugin.py`.

## Process Controls

__Note__: Process Controls are a new feature introduced with version 2.0.0 of the Python processor. 

Process controls are processes that run before an imputation step. An example is a filter applied to the input data or status file. This allows users to define process controls that enable the processor to be more generic, reduce the number of steps in an imputation strategy and improve the information provided to subsequent processes (SEVANI).

This feature requires the use of a new field in the Jobs metadata file, `controlid`. This field references an entry (or entries) in a new metadata file, *processcontrols.xml* (produced from the PROCESSCONTROLS worksheet in the excel template):

|controlid|targetfile|parameter|value|
|--|--|--|--|
|Identifies the control or set of controls to apply to the Jobs steps with the same controlid|The [dataset name](#available-table-names) to apply the control to (names should be written in the same case as they appear in the table)|The desired control type|Determined by the [control type](#control-types)|
|_control1_|_indata_|_row_filter_|_strat > 15 and (rec_id not in (SELECT * FROM instatus WHERE status != 'FTI'))_|
|_control1_|_instatus_|_column_filter_|_IDENT, AREA, V1_|
|_control1_|_indata_|_exclude_rejected_|_True_|
|_control1_|_N/A_|_edit_group_filter_|_N/A_|

All process controls with the specified `controlid` are applied to their respective `targetfile`s for the single job step on which they are declared. Upon completion of the job step the affected `targetfile`s are returned to their original state and the job continues. However, if the job step begins the execution of a new process block, the `targetfile` will remain in the state created by the process control(s) applied for the duration of the process block (and any sub-blocks within).

One controlid may be used as many times as needed per-`targetfile`. If a controlid is repeated for the same `targetfile` AND `parameter` then the `value` for those controls is combined into one. This is intended to allow more modularity in control sets as individual parts of multi-part conditions can be interchanged as desired without affecting the other parts.

### Control Types:
- ROW_FILTER 
    - Filters `targetfile` using an SQL WHERE clause
    - `value` - The SQL condition which can include column names and/or table names (exactly as shown in [available table names](#available-table-names))
    - If `controlid`, `targetfile` and `parameter` are repeated for more than one entry, the conditions in their `value` fields are joined by `AND`
- COLUMN_FILTER (can apply multiple for one ID, column name lists are combined into one)
    - Filters `targetfile`'s to remove columns that don't appear in the list in the `value` field
    - `value` - A comma-separated list of column names to KEEP in `targetfile`
    - If `controlid`, `targetfile` and `parameter` are repeated for more than one entry, the column lists in their `value` fields are combined
- EXCLUDE_REJECTED
    - Filters `targetfile` by removing any entries with a `unit_id` that appears in the `outreject` table
    - `value` - The text 'True' or 'False', indicating if the control should be applied or not
    - For one `controlid`, only one EXCLUDE_REJECTED control may be used per-`targetfile`
    - __NOTE__ Errorloc and Prorate each produce slightly `outreject` files.
        - Errorloc: `outreject`, produced by the current errorloc call, overwrites any existing `outreject` file. The contents of `outreject` are also appended to `outreject_all`.
        - Prorate: The contents of the `outreject` dataset produced by the current prorate call are appended to `outreject_all` and also appended to the existing `outreject` dataset (or just set as the `outreject` table if one does not yet exist).
- EDIT_GROUP_FILTER
    - Filters `instatus` by removing any entries with an `editgroupid` matching the current job step OR any entries that were produced by an Outlier step with a status value of `FTI` or `FTE`
    - `value` and `targetfile` fields should not be given for this control type
    - Replaces existing SAS functionality where this filter was automatically applied prior to executing a `DonorImputation` or `Deterministic` proc

* __NOTE__: Column names from your original input files should be referenced in their original case, those that are created or added by the Processor should be in ALL-CAPS.

### Available Table Names:

|Table Name|Notes|
|--|--|
|status_log|Contains all produced `outstatus` files appended in order|
|indata|The input data to the current job step. Alias: imputed_file|
|instatus|The input status data to the current job step. Alias: status_file|
|time_store|Information regarding the runtime and exection of each step in a job|
|outreject and outreject_all|Produced by Errorloc and Prorate|
|outedit_applic|Can be produced by Editstats|
|outedit_status|Can be produced by Editstats|
|outedits_reduced|Can be produced by Editstats|
|outglobal_status|Can be produced by Editstats|
|outk_edits_status|Can be produced by Editstats|
|outvars_role|Can be produced by Editstats|
|outacceptable|Can be produced by Estimator|
|outest_ef|Can be produced by Estimator|
|outest_lr|Can be produced by Estimator|
|outest_parm|Can be produced by Estimator|
|outrand_err|Can be produced by Estimator|
|outmatching_fields|Produced by DonorImputation|
|outdonormap|Produced by DonorImputation and MassImputation|
|outlier_status|Can be produced by Outlier|

- Optional datasets are only available during execution and saved to disk if the input parameter process_output_type is set to "All" (2) or the dataset's name is specified in a ProcessOutput metadata table entry for the process producing it and process_output_type is set to "Custom" (3)
- Either the table name or its alias may be used, both refer to the same table and data
- The indata and instatus files are always available
    - If instatus is the first step in a job that doesn't provide an instatus file to start with, it is not available to be used in a filter for the first step, though it is available in subsequent steps
- Any procedure-specific file is not available to reference until a job step for that procedure has run in a preceding step, and only if the file referenced is produced according to the `process_output_type`
- All files will have the columns SEQNO and JOBID added. These can be filtered to obtain data from a specific job step.

## Process Blocks

__Note__: Process Blocks are a new feature introduced in version 2.0.0 of the Python processor. 

A job in the Banff Processor is a collection of Jobs metadata table entries, all joined by a common job identifier (jobid) and processed sequentially according to the sequence number (seqno). Only a single job is specified when executing the processor, which is done by specifying the `job_id` input parameter. A Process Block is essentially a job called from within a job. Process Blocks organize jobs into sub-jobs with the following goals: 

- to allow a process control to be associated with multiple job steps.
- to allow the reuse of a sequence of steps that are repeated with different inputs.
- to allow users to design and implement imputation strategies using a modular approach. This means that smaller jobs can be developed and tested in isolation rather than has one large job. 

Process blocks are used by setting the *process* field of a Jobs metadata table entry to `job` (rather than a traditional Banff procedure such as `prorate` or `donorimputation`) and setting the *specid* field to be the `jobid` of the process block that is to be run.

Process blocks can call other process blocks, providing further flexiblity. When preparing to execute the Banff `Processor`, the Jobs metadata is validated using the `job_id` input parameter as the root of the overall job structure. This validation ensures that no cycles (infinite loops) exist when the job has nested process blocks. If one is found, an error will be printed to the console and/or log file and issue will need to be corrected in order to succesfully execute the job.

|jobid|seqno|controlid|process|specid|editgroupid|byid|acceptnegative|
|--|--|--|--|--|--|--|--|
|main_job|1|*n/a*|job|sub_job|*n/a*|*n/a*|*n/a*|
|main_job|2|*n/a*|outlier|outlier_spec1|*n/a*|*n/a*|*n/a*|
|main_job|3|*n/a*|job|sub_job|*n/a*|*n/a*|*n/a*|
|sub_job|1|*n/a*|prorate|prorate_spec1|*n/a*|*n/a*|*n/a*|
|sub_job|2|*n/a*|donorimp|donorimp_spec1|*n/a*|*n/a*|*n/a*|

For example, the Jobs table above would result in the execution of:
1. prorate (sub_job, 1)
2. donorimp (sub_job, 2)
3. outlier (main_job, 2)
4. prorate (sub_job, 1)
5. donorimp (sub_job, 2)

A working example of a job with a Process Block can be found [here](../../examples/example4?ref_type=heads).


## Output

### Saving Ouputs

If running from within a python script, output datasets can be saved to disk by calling the `save_outputs()` function of the `banffprocessor` object containing the results from a call to `execute()`. If running from command line `save_outputs()` will be called automatically once the processor has finished a job.

During operation, if no `output_folder` parameter is provided, the processor will create an `out` folder in the same location as your input JSON parameter file to save the Banff log as well as the output status and data files that are created during and after the execution of each Banff proc. The status and data files will be saved in the format determined by:

1. The `saveFormat` parameter in your input JSON file
2. If no value provided for 1., uses the same format as the file in `indata_filename`
3. If neither 1. or 2. are provided, defaults to `.parq` format

### Output files/datasets

The output files from each procedure can be retained and saved. The Processor will automatically add the columns `JOBID` and `SEQNO` to the outputs. When an output with the same name is generated and retained, the processor will append these output datasets together and the datasets will need to be filtered by `JOBID` and `SEQNO` to limit the data to a specified processing step.

**Minimal Outputs**
|Data File|Description|
|--|--|
|imputed_file|This data file contains the final imputed current data.|
|status_file|This data file contains the final imputed data statuses.|
|status_log|This data file contains the history of how the statuses changed during the imputation strategy.|
|outreject|This data file is generated by the ErrorLoc and Prorate procedures. It contains the identification of respondents that could not be processed and the reason why.|
|time_store|This data file stores the start time, end time and duration of each processing step along with the cumulative execution time.|

**Optional Outputs**
|Data File|Related Procedure|Description|
|--|--|--|
|outlier_status|Outlier|It contains the final status file including the additional variables from the `outlier_stats` option (which is always in effect in the Banff Processor).|
|outmatching_fields|Donor Imputation|It contains the status of the matching fields from the `outmatching_fields` option (which is always in effect in the Banff Processor).|
|outdonormap|DonorImputation|It contains the identifiers of recipients that have been imputed along with their donor identifier and the number of donors tried before the recipient passed the post-imputation edits.|
|outedits_reduced|EditStats|This data file contains the minimal set of edits.|
|outedit_status|EditStats|This data file contains the counts of records that passed, missed and failed for each edit.|
|outk_edits_status|EditStats|This data file contains the distribution of records that passed, missed and failed K edits.|
outglobal_status|EditStats|This data file contains the overall counts of records that passed, missed and failed.|
outedit_applic|EditStats|This data file contains the counts of edit applications of status pass, miss or fail that involve each field.|
outvars_role|EditStats|This data file contains the counts of records of status pass, miss or fail for which field j contributed to the overall record status.|
|outrand_err|Estimator|This dataset contains the random error report if at least one of the estimator specifications has the `RANDOMERROR` variable in the ESTIMATOR metadata table set to `Y`.|
|outest_ef|Estimator|This dataset contains the report on the calculation of averages for estimator functions if at least one of the estimator specifications uses an estimator function (type EF).|
|outest_parm|Estimator|This dataset contains the report on imputation statistics by estimator.|
|outest_lr|Estimator|This dataset contains the report on the calculation of « beta » coefficients for linear regression estimators if at least one of the estimator specifications uses a linear regression (type LR).|
|outacceptable|Estimator|This data file contains the report on acceptable observations retained to calculate the parameters for each estimator given in the specifications. This file can be large and can slow down execution.|

**Notes**
- Refer to the Banff Procedure User Guide for a full description of a file generated by a Banff Procedure.
- Optional output files will be retained if process_output_type = `all` or if process_output_type = `custom` and the dataset name is specified in the ProcessOutputs metadata for the given process.
- Plugins may output additional optional output files.

### The Log

The Python processor can generate an execution log which provides valuable information about the imputation process which is useful for debugging and analytical purposes. The level of information logged can be configured via the `log_level` parameter of your input JSON file. 

- If 0, no log file is produced at all, only warnings, errors and a summarization of each procedure is written to the console after it is performed. This summary is always printed, even at levels 1 and 2. 

- If 1 (the default value if `log_level` is not set), the log file contains INFO-level messages, which is primarily the output from the execution of each proc from the Banff package, as well as warnings and errors. 

- Finally, if 2, the log file contains all messages from 1 as well as any DEBUG-level messages, such as more granular information about produced and processed datasets.

The processor keeps a maximum of 6 log files at once. The most recent job is always logged to `banffprocessor.log` and when a new job is run, a number is appended to the old log file and a new log is created for the new job. The numbering goes from newest to oldest (i.e. `banffprocessor.log` is the log for the most recent job, `banffprocessor.log.1` is from the next most recent and `banffprocessor.log.5` is from the oldest job).

### Process Block Output

When a new process block is to be run, a special folder is created in the output folder for the calling block. This new output folder is named after the new block's parameters and upon completion of the block will contain all of the files created by the child block. No new log file is created, however. All log outputs for child blocks can be found in the main log file found in the root input folder.
