"""RoundData Banff Procedure plugin.

Note that this plugin is based on a user-definded program used in IBSP.
"""

import banffprocessor.procedures.factory
import banffprocessor.processor_logger as plg
import duckdb
from banffprocessor.processor_data import ProcessorData


class RoundData:
    """Rounds a list of variables to a specified number of decimals.

    The RoundData class implements the ProcedureInterface protocol class, an interface developed to
    allow users to write plugin procedures for the Banff Processor.

    User variable `round_specs` must be defined in the Banff Processor metadata.
    Round_specs: is used to specify the variables to round and to how many decimal places.
    For example "REVENUE 2, NUMBEROFEMPLOYEES 0" will indicate that variable revenue will be rounded
    to 2 decimals and variable number of employees will be rounded with no decimals.
    """

    @classmethod
    def execute(cls, processor_data: ProcessorData) -> int:
        """Execute of this procedure.

        The Banff Processor will execute this method when a RoundData process is encountered in the jobs metadata.

        :param ProcessorData: An object defined in the banffprocessor package which provides access to
            Banff Processor data and metadata
        :type processor_data: :class:`banffprocessor.processor_data.ProcessorData`

        :return: Returns 0 if successful, an exception if an error occurred.
        :rtype: int
        """
        # Creating a logger for this step
        log_lcl = plg.get_processor_child_logger("round_data")
        temp_table = "tmpdata"

        try:
            # Converting the roundspecs string into a list
            round_specs = str(processor_data.current_uservars["round_specs"])
            round_specs = round_specs.split(",")

            variable_list = []
            round_list = []
            for roundspec in round_specs:
                roundspec_list = roundspec.split()
                variable_list.append(roundspec_list[0])
                round_list.append(roundspec_list[1])

            # Getting a reference to the input data and loading it into duckdb
            indata = processor_data.indata # noqa: F841
            duckdb.sql(f"CREATE TABLE {temp_table} AS SELECT {processor_data.input_params.unit_id}, {','.join(variable_list)} from indata")

            # Looping through the list of variables to round and rounding them to the specified number of decimals
            for roundspec in round_specs:
                roundspec_list = roundspec.split()
                msg = f"Variable {roundspec_list[0]} will be rounded to {roundspec_list[1]} decimal places"
                log_lcl.info(msg)
                duckdb.sql(f"UPDATE {temp_table} SET {roundspec_list[0]} = Round({roundspec_list[0]},{roundspec_list[1]})")

            processor_data.outdata = duckdb.sql(f"SELECT {processor_data.input_params.unit_id}, {','.join(variable_list)} from {temp_table}").arrow()

            return 0

        except Exception:
            # If an error occurs, print the error to the log and return a non-zero return code
            msg = "An error occured during execution of this procedure."
            log_lcl.exception(msg)
            return 1

        finally:
            duckdb.sql(f"DROP TABLE {temp_table}")

def register(factory: banffprocessor.procedures.factory) -> None:
    """Register this procedure in the Banff processor factory.

    All Banff Processor plugins must implement this function.

    :param factory: factory object to register with
    :type processor_data: :class:banffprocessor.procedures.factory
    """
    factory.register("rounddata", RoundData)
