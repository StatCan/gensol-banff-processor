"""ModifyVariable Banff Procedure plugin.

Note that this plugin is based on a user-definded program used in IBSP.
"""

import banffprocessor.procedures.factory
import banffprocessor.processor_logger as plg
import duckdb
from banffprocessor.processor_data import ProcessorData


class ModifyVaraible:
    """ModifyVariable Banff Procedure plugin.

    The ModifyVariable class implements the ProcedureInterface protocol class, an interface developed to
    allow users to write plugin procedures for the Banff Processor. This plugin is typically used to modify
    records from the imputed file (indata) based on a where statement. A supplied formula is used to
    modify data in the named variable. Four user variables must be
    defined in the Banff Processor `metadata`, `where_stmt` , `reference_id`, `variable`, `formula`.

    1) where_stmt is the where expression used to determine what data is modified.
        The syntax must be compatible with duckdb.
    2) reference_id is used to identify the excluded data when it is time to add it back to the imputed file.
    3) formula is the code to modify the variable.  Must be valid duckdb syntax.
    4) variable is the variable to modify.
    5) workingFileName is the table to be modified, defaults to imputed_file (indata). When the imputed_file is modified,
       the status file is also moduled. The 'IMV' will be the status flag for values changed.
    """

    @classmethod
    def execute(cls, processor_data: ProcessorData) -> int:
        """Modify a variable on a banff processor dataset.

        The Banff Processor will execute this method when a ModifyVaraible process is encountered in the jobs metadata.
        If the Imputed File (inData) is modified, outdata and outstatus will be created, the status will be 'IMV'
        for cases where a value was changed.

        :param ProcessorData: An object defined in the banffprocessor package which provides access to
            Banff Processor data and metadata
        :type processor_data: :class:`banffprocessor.processor_data.ProcessorData`

        :return: Returns 0 if successful, 1 if can error occured during the process
        :rtype: int
        """
        # Creating a logger for this step
        log_lcl = plg.get_processor_child_logger("modify_variable")

        temp_table_modified = "tmpdata"
        temp_table_status = "tmpstatus"
        temp_table_original = "tmporiginal"

        try:
            # Reading in user variables defined in the metadata for this step
            variable = processor_data.current_uservars["variable"]
            formula = processor_data.current_uservars["formula"]

            # the where_stmt is optional
            if "where_stmt" in processor_data.current_uservars:
                where_stmt = processor_data.current_uservars["where_stmt"]
                where_clause = f"WHERE {where_stmt}"
            else:
                where_clause = ""

            if "workingFileName" in processor_data.current_uservars:
                working_filename = processor_data.current_uservars["workingFileName"].casefold()
            else:
                # default to imputedfile
                working_filename = "imputed_file"

            working_data = processor_data.get_dataset(working_filename, create_if_not_exist=False)

            # check to ensure dataframe was loaded.
            if working_data is None:
                msg = "Error: workingFileName is not a valid table"
                raise ValueError(msg)

            # make a copy of the file to be updated.
            # this was the only way I could get this to work
            duckdb.sql(f"CREATE TABLE {temp_table_modified} AS SELECT * from working_data;")

            if working_filename == "imputed_file":
                # We need the original value to detect what changed in order to update the status file
                duckdb.sql(f"CREATE TABLE {temp_table_original} AS SELECT {variable}, {processor_data.input_params.unit_id} from {temp_table_modified}")

            # Modify the table by applying the formula
            duckdb.sql(f"UPDATE {temp_table_modified} SET {variable} = {formula} {where_clause};")

            if working_filename == "imputed_file":
                duckdb.sql(
                    f"""
                           CREATE TABLE {temp_table_status} as
                           SELECT {temp_table_modified}.{processor_data.input_params.unit_id},
                                '{variable}' as FIELDID,
                                'IMV' as STATUS,
                                {temp_table_modified}.{variable} as VALUE
                           from {temp_table_modified}
                           join {temp_table_original}
                           on ({temp_table_modified}.{processor_data.input_params.unit_id} = {temp_table_original}.{processor_data.input_params.unit_id})
                           where {temp_table_modified}.{variable} != {temp_table_original}.{variable}
                           """,
                )

                processor_data.outstatus = duckdb.sql(f"SELECT * from {temp_table_status};").arrow()

                sql_stmt = f"""
                    SELECT {processor_data.input_params.unit_id}, {variable}
                    from {temp_table_modified}
                    WHERE {processor_data.input_params.unit_id} in (
                    SELECT {processor_data.input_params.unit_id} FROM {temp_table_status}
                    )
                    """
                processor_data.outdata = duckdb.sql(sql_stmt).arrow()

            elif working_filename in ("status_all", "instatus"):
                duckdb.sql(f"ALTER TABLE {temp_table_modified} DROP SEQNO")
                duckdb.sql(f"ALTER TABLE {temp_table_modified} DROP JOBID")
                processor_data.outstatus = duckdb.sql(f"SELECT * from {temp_table_modified};").arrow()

            else:
                processor_data.set_dataset(working_filename, duckdb.sql(f"SELECT * from {temp_table_modified};").arrow())

            return 0

        except Exception:
           # If an error occurs, print the error to the log and return a non-zero return code
            msg = "An error occured during execution of this procedure."
            log_lcl.exception(msg)
            return 1

        finally:
            duckdb.sql(f"DROP TABLE IF EXISTS {temp_table_modified}")
            duckdb.sql(f"DROP TABLE IF EXISTS {temp_table_original}")
            duckdb.sql(f"DROP TABLE IF EXISTS {temp_table_status}")

def register(factory: banffprocessor.procedures.factory) -> None:
    """Register this procedure in the Banff processor factory.

    All Banff Processor plugins must implement this function.

    :param factory: factory object to register with
    :type processor_data: :class:banffprocessor.procedures.factory
    """
    factory.register("modifyvariable", ModifyVaraible)
