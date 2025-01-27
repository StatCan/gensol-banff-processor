# Banff Processor Version 1 Migration Guide

## Foreword

This document is intended for users of the SAS based version of the Banff Processor and serves as a supplement to the main user guide to help with the transition from SAS (Banff Processor Version 1) to Python (Banff Processor Version 2). 

## Migrating from SAS to Python

The SAS version of the Banff Processor dates back to 2008, it has been used at Statistics Canada for many years. The Python version is similar to the SAS version in many ways and effort has been made to make the metadata backwards compatible where possible. This guide highlights some of the main differences to help users migrate to the new version.

In general, XML metadata files from version 1 is compatible with version 2, with the following exceptions:

- SAS-based custom programs (or user-defined programs) will not work; they must be replaced with plugins. Guidelines for developing plugins are available in the user guide.
- Syntax in expressions must be reviewed; SAS specific expressions must be converted to SQL-Lite syntax.
- The SAS-based processor included some default behaviour that has been removed to increase modularity and transparency. The past behaviour can be replicated with process controls; see the section on Process Controls in the user guide for details.

### New Features

- Process Blocks: Process Blocks allow users to call a job within a job. In the SAS Processor, the jobs table could contain multiple jobs, but now they can be chained together to create a master job. This is done by using the process called job and specifying the job id in the spec id column.
- Process Controls: Process Controls allow modifications to be made to the inputs of a processing step without the risk of modifying the main working datasets. This was typically done in the SAS processor with user-defined processes, or the input modifications were hardcoded in the processor itself.
- The Banff Processor now supports variable lengths up to 64 characters. A variable must still begin with a character or underscore and consist of only alphabetic characters, digits, and underscores (spaces with variable names are not supported).

## Behaviour Changes

1. A key difference is that the SAS Banff Processor was a code generator. The processor created a SAS program and then the program was executed. There was an option to save the generated program, which could be run and used for debugging purposes. This is no longer the case with the Python processor, the process is executed dynamically in one pass.

2. In the SAS Processor, the SAS work library was used to store and access temporary datasets. In Python there are a few alternatives. Generally, data is accessed in user-defined processes (plugins) through the ProcessorData object, however, plugin developers can choose to store diagnostic files in another location such as a duckdb database or an appropriate folder. Using the tempfile library is an option, but it saves data in the user’s profile by default which may not be appropriate in certain situations. 

3. The processor no longer automatically deletes records found on the reject file from the input data of an imputation step. If this behaviour is desired, the `exclude_rejected` [process control](./processor-user-guide.md#process-controls) can be used. Note that the rejected data can be accessed in a user defined process with `processor_data.get_output_dataset("outreject")`.

4. When calling the ErrorLoc procedure, outlier status is no longer taken into consideration, only values flagged as FTI in the input status file. If this behaviour is desired, a user-defined process (plugin) can be created.  The medium-term plan would be to replace this functionality with a process control/filter.

## Inputs

### SAS Macro parameters

SAS Macro variables are now Python function parameters. With the new processor, these parameters can be specified in a JSON file. Alternatively, inputs can be specified directly when creating a `Processor` object.

Parameter names have changed to respect Python naming conventions and improved to be more consistent and descriptive. Some have been replaced by more generic options or are no longer applicable. Also note that parameter names are now **case sensitive**.

|SAS|Python|Notes|
|--|--|--|
|jobid|job_id||
|id|unit_id|This changed was required as id is a python function and not recommended to be used as a variable name.|
|dataLib|input_folder|In SAS, dataLib was a libref, in Python a file folder is specified. However, datasets can also be specified directly when creating a Processor object. If no dataset is specified, the processor will look in the input folder for the specified file name associated with input file.|
|curFile|indata_filename||
|outdataLib|output_folder||
|auxFile|auxdata_filename||
||instatus_filename|This is a new optional parameter in the Python Processor which allows initial status values to be specified.|
|histFile|histdata_filename||
|histStatus|histstatus_filename||
|custProgFref|user_plugins_folder||
|flatfileFref||Dropped from the Python Processor as this option was rarely used.|
|seed|seed||
|logType|log_level|The log_level parameter provides similar functionality as logType.|	
|editstatsOutputType||Replaced by process_output_type.|
|estimatorOutputType||Replaced by process_output_type.|
|massImputOutputType||Replaced by process_output_type.|
|randnumvar|randnumvar||
|genCode/fgenprog||No longer applicable, a program code is no longer generated and executed.|
|editGroupFilter||Replaced by the EDIT_GROUP_FILTER process control|
|tempLib||No longer applicable|	
|bpOptions||No longer applicable, these options were TIME, KEEPTEMP and NOBYGRPSTATS.|
||save_format|This is a new option in the Python Processor, the SAS Processor produced SAS datasets. Parquet is currently the recommended save format (.parq), CSV is provided for testing and debugging purposes.|

## Input files

### Input data files

In the SAS Processor, input data files were SAS datasets. There were essentially two data types: character (fixed width strings) and numeric (64-bit floating point numbers). In the Python Processor, parquet files are the recommended file format. These files are read in and mainly stored as arrow tables, though, in some cases, data is converted to other formats such as pandas data frames or duckdb tables. There are many different types, we generally recommend str (variable length strings) and float64 (64-bit floating point numbers), although various types can be used (float32, float16, int8, int16, ...). Variable types should be verified and adjusted as necessary. The main reason that CSV files are not recommended is due to the lack of metadata to ensure that types are set correctly when reading and writing files.  

### Metadata Files

- The structure of the metadata files in the Python Processor are essentially the same as the  SAS based version, any new elements are optional. However, the contents of the metadata may need to be adjusted. The expressions will likely need to be updated to reflect the new syntax. 

- Maximum lengths for most metadata columns have been increased. For example, previously, many ID fields had a limit of 30 characters, this limit has been increased to 100 characters.

- Though the metadata files still except values of Yes/No or Y/N, They are stored in the processor as Boolean values and will therefore be converted to True/False values.

- The Banff Processor still has an Excel template to help facilitate the creation of XML files as expected by the Banff Processor, however, the Excel Macro has been removed from the template and the banffprocessor package now includes a utility to convert the Excel workbook to XML. This utility can be called from the command line or from within a Python program. The command line utility is called `banffconvert` the utility is defined in `banffprocessor.util.metadata_excel_to_xml`

|Metadata file|Notes|
|--|--|
|JOBS|Jobs has a new, optional element called controlid. This new column is used to link specifications in the process controls metadata. Also note that SEQNO can now have decimals, previously SEQNO could only be an integer.|
|USERVARS|The structure has not changed.|
|EDITS|The structure has not changed. The syntax for edits has not changed.|
|EDITGROUPS|No changes.|
|VERIFYEDITSPECS|No changes.|
|OUTLIERSPECS|No changes.|
|ERRORLOCSPECS|No changes.|
|DONORSPECS|No changes.|
|ESTIMATORSPECS|No changes.|
|PRORATESPECS|No changes.|
|MASSIMPUTATIONSPECS|No changes.|
|ALGORITHMS|User-defined algorithms can no longer override the algorithms of built-in estimators, a new name needs to be chosen.|
|ESTIMATORS|No changes.|
|EXPRESSIONS|The structure has not changed. However, expressions are now based on SQLite as implemented in [duckdb](https://duckdb.org/docs/sql/expressions/overview). An example difference would be that string constants must be enclosed in single quotes as opposed to double quotes; `P53_05_1="1"` would need to be changed to  `P53_05_1='1'`.|
|VARLISTS|No changes.|
|WEIGHTS|No changes.|
|PROCESSCONTROLS|This is a new metadata file that is used to create process control specfications.|
|PROCESSOUTPUTS|This is a new metadata file that is used to control what outputs are kept. It is used when process_output_type='Custom'|

### User-defined Processes (UDPs)

In the Python Processor user-defined processes are commonly referred to as plugins. SAS based UDPs were SAS program files that were executed via an include statement, user parameters defined in metadata were available in the program as global SAS macro variables. SAS UDPs will need to be reviewed and written as plugins. Plugins are Python classes that implement the protocol defined in `banffprocessor.procedures.procedure_interface`, user parameters defined in metadata can be accessed through the ProcessorData object. Note that in some cases, tasks previous handled by UDPs will no longer be required or can be replaced by Process Controls. Process Controls are meant to reduce the need for UDPs that perform data management tasks.

|SAS|Python|Notes|
|--|--|--|
|parmKeyVar, parmByList, parmSeqno, ...|processor_data.input_params.unit_id,  processor_data.by_varlist, processor_data.current_job_step.seqno, ... |In the SAS Processor, SAS global macro variables were used to access input paramters, now input parameters are available through processor_data object attributes such as input_params and current_job_step|
|work.jobs| processor_data.dbconn.sql("select * from Banff.JOBS").to_arrow_table()|Instead of accessing metadata tables as SAS datasets in the SAS work library, metadata tables are accessible in a duckdb database through processor_data.dbconn.|
|work.statusall|status_table = processor_data.get_dataset("status_file", table_format="arrow")|Instead of accessing data tables as SAS datasets in the SAS work library, datasets are accessible through the get_dataset function of processor_data. The dataset can be returned in arrow or pandas format. The set_dataset function can be used to save an output dataset.|

## Output files

The SAS Processor was outputting an accumulative file with the suffix all. This suffix has been dropped.

|SAS|Python|Notes|
|--|--|--|
|imputedfile|imputed_file|This output remains the same.|
|statusall|status_file|The columns on the status file have been reduced. The standard columns are the unit ID variable along with FIELDID, STATUS, VALUE, JOBID and SEQNO. VALUE is a new column, editgroupid, outlierstatus and by-variables have been removed.|
|cumulatifstatusall|status_log|Like the status file, the columns on this output have been standardized.|
||time_store|This is a new dataset which stores the start time, end time and duration of each processing step along with the accumulative execution time.|
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
||outreject|The outreject file is the last outreject dataset generated by either Prorate or ErrorLoc. It was only a working dataset in the SAS version called `rejected`, in the Python version, it is included as an output data set.|
|rejectedall|outreject_all|The rejected all file is a special case where the `all` suffix was retained. This was because Prorate and ErrorLoc process this dataset slightly different. See the user guide for more information.|
|varsroleall|outvars_role||

## Conclusion

For more information on how to use Banff and the Banff Processor, please consult the main user guides. Hopefully this information helps with the transition from version 1 to version 2.
