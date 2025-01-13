"""ExcludeData Banff Procedure for use with AddExcludedData.

Note that this Procedure is based on a user-definded program used in IBSP.
A Proces Control is recommended to replace this plugin.
"""

from pathlib import Path

import banffprocessor.procedures.factory
import banffprocessor.processor_logger as plg
import duckdb
import pyarrow as pa
from banffprocessor.processor_data import ProcessorData


class ExcludeData:
    """Excludes data from the Banff Processor, storing it in a file to be added back later.

    The ExcludeData class implements the ProcedureInterface protocol class, an interface developed to
    allow users to write plugin procedures for the Banff Processor. This plugin is used to exclude
    records from the imputed file (indata) based on a where statement. Two user variables must be
    defined in the Banff Processor `metadata`, `exclude_where_stmt` and `reference_id`.

    1) exclude_where_stmt is the where expression used to determine what data is excluded.
        The syntax must be compatible with duckdb.
    2) reference_id is used to identify the excluded data when it is time to add it back to the imputed file.

    Please note that this plugin was created as an example only and it is by no means a final version for production.
    In the future this type of user-defined procedure will be converted to a process control.
    """

    # These attributes determine if the Banff Processor should update the status file and/or the imputed file
    status_update_required = False
    # imputed_file_update_required updates existing records in imputed_file
    # Since we are adding records we cannot use the standard update process
    imputed_file_update_required = False
    # So we instead set a value for processor_data.indata and therefore use this flag instead
    dataset_updated_inplace = True

    @classmethod
    def execute(cls, processor_data: ProcessorData) -> int:
        """Exclude Data from a Banff Processor working dataset.

        The Banff Processor executes this method when an ExcludeData step is encountered in the jobs metadata. Only
        rows can be excluded. The Exclude data is stored in the output folder in a parquet file until added back by the
        AddExcludedData Procedure.

        :param ProcessorData: An object defined in the banffprocessor package which provides access to
            Banff Processor data and metadata
        :type processor_data: :class:`banffprocessor.processor_data.ProcessorData`

        :return: Returns 0 if successful, 1 if can error occured during the process
        :rtype: int
        """
        # Creating a logger for this step
        log_lcl = plg.get_processor_child_logger("exclude_data")

        # Setting names for temporary duckdb tables
        temp_table_excluded = "excludeddata"
        temp_table_kept = "keptdata"

        try:
            # Reading in user variables defined in the metadata for this step

            reference_id = processor_data.current_uservars["reference_id"]
            if "exclude_where_stmt" in processor_data.current_uservars:
                exclude_where_stmt = processor_data.current_uservars["exclude_where_stmt"]
            else:
                where_components = ["NOT (", processor_data.current_uservars["KEEPCONDITION"], ")"]
                exclude_where_stmt = " ".join(where_components)

            # We will save the excluded data as a parquet file in the output directory
            filename = Path(processor_data.input_params.output_folder) / Path(f"excluded_data_{reference_id}.parq")
            msg = f"Excluded data will be saved as {filename}"
            log_lcl.info(msg)

            # Getting a reference to the input data and loading it into duckdb
            indata = processor_data.get_dataset("indata")
            duckdb.sql(f"CREATE TABLE {temp_table_kept} AS SELECT * from indata")

            # Splitting the data based on the exclude where statement
            duckdb.sql(f"CREATE TABLE {temp_table_excluded} AS SELECT * from {temp_table_kept} where {exclude_where_stmt}")
            duckdb.sql(f"DELETE FROM {temp_table_kept} where {exclude_where_stmt}")

            # Using outdata to update imputed_file will not work here as outdata is just a
            # subset of indata and update_imputed_file will only update existing records

            # Instead, overwrite indata directly. Since we keep a copy of the excluded data
            # we will not lose anything if the data is needed later, it just needs to be added
            # back in a seperate step, like in these test plugins
            # Make sure if you are doing this that you set dataset_updated_inplace to True
            if isinstance(indata, pa.Table):
                processor_data.indata = duckdb.sql(f"SELECT * from {temp_table_kept}").arrow()
            else:
                processor_data.indata = duckdb.sql(f"SELECT * from {temp_table_kept}").to_df()

            # Saving the excluded data to disk
            duckdb.sql(f"COPY (SELECT * FROM {temp_table_excluded}) TO '{filename}' (FORMAT PARQUET);")

            return 0

        except Exception:
            # If an error occurs, print the error to the log and return a non-zero return code
            msg = "An error occured during execution of this procedure."
            log_lcl.exception(msg)
            return 1

        finally:
            # Cleaning up temporary tables, regardless of whether or not an exception occurred.
            duckdb.sql(f"DROP TABLE IF EXISTS {temp_table_excluded}")
            duckdb.sql(f"DROP TABLE IF EXISTS {temp_table_kept}")

def register(factory: banffprocessor.procedures.factory) -> None:
    """Register this procedure in the Banff processor factory.

    All Banff Processor plugins must implement this function.

    :param factory: factory object to register with
    :type processor_data: :class:banffprocessor.procedures.factory
    """
    factory.register("excludedata", ExcludeData)
