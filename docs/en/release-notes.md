# Banff Processor release notes

## 2025-January-24 (Version `2.0.1`)

* Documentation: 
    * Various minor updates
    * French version of metadata-tables.md has been added
* Dependencies: 
    * Duckdb and Pyarrow versions are now bound below 2 and 19, respectively, as a result of compatibility issues with pyarrow version 19 and the available versions of pandas and duckdb

## 2025-January-13 (Version `2.0.0`)

The initial production release of the Python version of the Banff Processor.
* Compatible with banff v3.1
* For a detailed description of new features and differences between the SAS based version, please see our [migration guide](./migrating-from-sas-python.md)