# Banff Processor

The Banff Processor is part of the Banff project. It is a tool that can be installed in addition to the Banff Procedure package. This tool is used to implement an imputation strategy, which is essentially a sequence of processing steps. A processing step can be a standard Banff Procedure, a user-defined process (plugin) or a process block (another sequence of processing steps). 

Imputation strategies are defined using XML files, an Excel template has been provided along with a utility to convert metadata created with the template to the XML files required by the processor. The output of a processor job is the imputed file along with a log and various status and optional diagnostic files.


## User Documentation

- [User Guide](./processor-user-guide.md) - *Detailed information on using the Python based Banff processor*
- [Migration Guide](./migrating-from-sas-python.md) - *Detailed information on the differences between the Python and SAS-based processor*
- [Process Blocks and Process Controls](./process-blocks-and-controls.md) - *An Introduction to some important new features*
- [Metadata Tables](./metadata-tables.md) - *Detailed information on the expected format and contents of processor metadata*
- [Release Notes](./release-notes.md) - *Summary of changes*
