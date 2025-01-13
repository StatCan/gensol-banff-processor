"""AddExcludedData Banff Procedure for use with ExcludeData.

Note that this plugin is based on a user-definded program used in IBSP.
A Proces Control is recommended to replace this plugin.
"""

from pathlib import Path

import banffprocessor.procedures.factory
import banffprocessor.processor_logger as plg
import duckdb
import pyarrow as pa
from banffprocessor.processor_data import ProcessorData


class AddExcludedData:
    """The AddExcludedData is a plugin procedure for the Bannf Processor.

    AddExcludedData implements the ProcedureInterface protocol class, an interface developed to
    allow users to write plugin procedures for the Banff Processor. This plugin is used to add back excluded
    records to the imputed file (indata). User variable `reference_id` must be defined the Banff Processor metadata.

    1) reference_id is used to find the excluded data that was excluded by an ExcludeData step.

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
        """Add back data that was excluded previously with the ExcludeData Procedure.

        The Banff Processor executes this method when an AddExcludedData step is encountered in the jobs metadata.

        :param processor_data: An object defined in the banffprocessor package which provides access to
            Banff Processor data and metadata
        :type processor_data: :class:`banffprocessor.processor_data.ProcessorData`

        :return: Returns 0 if successful, 1 if an error occured during the process
        :rtype: int
        """
        # Creating a logger for this step
        log_lcl = plg.get_processor_child_logger("add_excluded_data")

        # Setting names for temporary duckdb tables
        temp_table_excluded = "excludeddata"
        temp_table_kept = "keptdata"

        try:
            # Reading user-defined paramaters variable reference ID
            # Reference ID is used to associcate this step with an ExcludeData step
            reference_id = processor_data.current_uservars["reference_id"]
            filename = Path(processor_data.input_params.output_folder) / Path(f"excluded_data_{reference_id}.parq")

            # Obtaining a reference to the input micro data and concatenting the parquet file created
            # by the corresponding ExcludeData step into it
            indata = processor_data.get_dataset("indata")
            duckdb.sql(f"CREATE TABLE {temp_table_excluded} AS SELECT * FROM read_parquet('{filename}');")
            duckdb.sql(f"CREATE TABLE {temp_table_kept} AS SELECT * from indata UNION SELECT * from {temp_table_excluded};")

            # Using outdata to update imputed_file will not work here as outdata is just a
            # superset of indata and update_imputed_file will only update existing records
            # Instead, overwrite indata directly
            # Make sure if you are doing this that you set dataset_updated_inplace to True
            if isinstance(indata, pa.Table):
                processor_data.indata = duckdb.sql(f"SELECT * from {temp_table_kept};").arrow()
            else:
                processor_data.indata = duckdb.sql(f"SELECT * from {temp_table_kept};").to_df()

            # Cleaning up the temporary file created by the ExcludeData step now that the data has been added back
            # This could be kept for debugging purposes (a potential enchancement)
            Path(filename).unlink()
            msg = f"Excluded data has been added back and the following file has been removed: {filename}"
            log_lcl.info(msg)

            return 0

        except Exception:
            # If an error occurs, print the error to the log and return a non-zero return code
            msg = "An error occured during execution of this procedure."
            log_lcl.exception(msg)
            return 1

        finally:
            duckdb.sql(f"DROP TABLE IF EXISTS {temp_table_excluded}")
            duckdb.sql(f"DROP TABLE IF EXISTS {temp_table_kept}")

def register(factory: banffprocessor.procedures.factory) -> None:
    """Register this procedure in the Banff processor factory.

    All Banff Processor plugins must implement this function.

    :param factory: factory object to register with
    :type processor_data: :class:banffprocessor.procedures.factory
    """
    factory.register("addexcludeddata", AddExcludedData)
