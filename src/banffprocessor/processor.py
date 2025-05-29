import argparse
import sys
from argparse import RawTextHelpFormatter
from datetime import datetime, timedelta
from pathlib import Path

import banff
import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

import banffprocessor as bpp
import banffprocessor.procedures.banff_procedures.job_proc as jp
import banffprocessor.processor_logger as plg
from banffprocessor.exceptions import MetadataConstraintError, ProcedureReturnCodeError, ProcessorInputParameterError, UserDefinedPluginError
from banffprocessor.metadata.metaobjects import MetaObjects
from banffprocessor.nls import _
from banffprocessor.procedures import banff_procedures, factory, loader
from banffprocessor.procedures.banff_procedures.editstats import EditStats
from banffprocessor.procedures.banff_procedures.verifyedits import VerifyEdits
from banffprocessor.processor_data import ProcessorData
from banffprocessor.processor_input import ProcessorInput
from banffprocessor.util.dataset import add_single_value_column, copy_table, table_empty

# Setup local log for processor module specifically
log_lcl = plg.setup_processor_logger()

class Processor:
    """Main class for the Banff processor.

    :attribute processor_data: Contains all the datasets and parameters required to run
        a Banff Processor job
    :type processor_data: :class:`src.banffprocessor.processor_data.ProcessorData`
    :attribute is_child_block: Is the job running in this processor instance a child of another
        currently running processor instance executing the parent block?
    :type is_child_block: bool
    """

    processor_data : ProcessorData
    is_child_block: bool

    @property
    def dbconn(self) -> duckdb.DuckDBPyConnection | None:
        """The currently connected database used to store some processor data.

        :return: The duckdbpyconnection currently being used to store data.
        :rtype: duckdb.DuckDBPyConnection | None
        """
        return self._dbconn

    def __init__(self, input_params: ProcessorInput | None = None, initial_data: ProcessorData | None = None,
                 dbconn: duckdb.DuckDBPyConnection | None = None, indata: pa.Table | pd.DataFrame | None = None,
                 indata_aux: pa.Table | pd.DataFrame | None = None, indata_hist: pa.Table | pd.DataFrame | None = None,
                 instatus: pa.Table | pd.DataFrame | None = None, instatus_hist: pa.Table | pd.DataFrame | None = None) -> None:
        """Construct an instance of the Processor.

        :param input_params: The job's input parameters. This may instead be provided as a member
            of `initial_data`, but one must be provided. Defaults to None
        :type input_params: :class:`src.banffprocessor.processor_input.ProcessorInput` | None, optional
        :param initial_data: Initializes a new Processor object with data from an existing Processor, defaults to None
        :type initial_data: :class:`src.banffprocessor.processor_data.ProcessorData` | None, optional
        :param indata: The indata dataset, defaults to None
        :type indata: :class:`pyarrow.Table` | :class:`pandas.DataFrame` | None, optional
        :param indata_aux: The indata_aux dataset, defaults to None
        :type indata_aux: :class:`pyarrow.Table` | :class:`pandas.DataFrame` | None, optional
        :param indata_hist: The indata_hist dataset, defaults to None
        :type indata_hist: :class:`pyarrow.Table` | :class:`pandas.DataFrame` | None, optional
        :param instatus: The instatus dataset, defaults to None
        :type instatus: :class:`pyarrow.Table` | :class:`pandas.DataFrame` | None, optional
        :param instatus_hist: The instatus_hist dataset, defaults to None
        :type instatus_hist: :class:`pyarrow.Table` | :class:`pandas.DataFrame` | None, optional
        :param dbconn: A DuckDBPyConnection to use for storing required data and metadata.
            If not provided an in-memory DB will be instantiated, defaults to None
        :type dbconn: :class:`duckdb.DuckDBPyConnection` | None, optional
        :raises ProcessorInputParameterError: If the `input_params` contains an
            `output_folder` or `metadata_folder` parameter but the directory
            cannot be found
        :raises ValueError: If one of `input_params` or `initial_data` are not provided.
        """
        self.is_child_block = False

        if(initial_data):
            self.processor_data = initial_data
            self._dbconn = self.processor_data.dbconn
            self._is_private_connection = False
            self.is_child_block = True
        elif(not input_params):
            msg = _("Input parameters must be provided either via the input_params parameter "
                    "or as part of the input_params property of the initial_data ProcessorData object.")
            log_lcl.exception(msg)
            raise ValueError(msg)
        else:
            self._dbconn = dbconn
            if self._dbconn is None:
                self._dbconn = duckdb.connect(database=":memory:")
                self._is_private_connection = True
            else:
                self._is_private_connection = False

            self.processor_data = ProcessorData(input_params=input_params, dbconn=self._dbconn)

            # Make sure DuckDB includes user input folder so DuckDB can see any tables the
            # user might reference relative to the correct location
            self.dbconn.sql(f"SET file_search_path = '{self.processor_data.input_params.input_folder}';")
            log_lcl.debug(_("Set DuckDB connection file_search_path to input folder: {}").format(self.processor_data.input_params.input_folder))

        plg.add_file_handlers(log_directory=self.processor_data.input_params.output_folder,
                              trace_level=self.processor_data.input_params.log_level)

        # The remaining setup below is only necessary if an initial ProcessorData object is not provided
        if(initial_data):
            return

        # Load the metadata files from the selected location
        self.processor_data.metaobjects = MetaObjects(self.processor_data.input_params.metadata_folder,
                                                      job_id=self.processor_data.input_params.job_id,
                                                      dbconn=self._dbconn)

        # Load Banff and User-defined plugins
        self._load_plugins()

        for proc_name in self.processor_data.metaobjects.job_proc_names:
            proc_cls = factory.get_procedure(proc_name)
            if(proc_cls not in [VerifyEdits, EditStats, jp.JobProc] and proc_name in banff_procedures.__all__):
                msg = "At least one of the procedures referenced in your job require {} "
                msg += "but one was not provided in your input parameters."
                # If we are here, we need unit_id and imputed_file
                if(not self.processor_data.input_params.unit_id):
                    msg = _(msg).format("a unit_id")
                    log_lcl.exception(msg)
                    raise ProcessorInputParameterError(msg)
                if(not indata and not self.processor_data.input_params.indata_filename):
                    msg = _(msg).format("an indata file")
                    log_lcl.exception(msg)
                    raise ProcessorInputParameterError(msg)

        # Input datasets
        dataset_name = "imputed_file"
        if(indata is not None):
            self.processor_data.set_dataset(dataset_name, indata)
        elif(self.processor_data.input_params.indata_filename):
            self.processor_data.set_dataset_from_file(dataset_name, self.processor_data.input_params.indata_filename)

        dataset_name = "indata_aux"
        if(indata_aux is not None):
            self.processor_data.set_dataset(dataset_name, indata_aux)

        dataset_name = "indata_hist"
        if(indata_hist is not None):
            self.processor_data.set_dataset(dataset_name, indata_hist)

        dataset_name = "instatus_hist"
        if(instatus_hist is not None):
            self.processor_data.set_dataset(dataset_name, instatus_hist)

        dataset_name = "status_file"
        if(instatus is not None):
            self.processor_data.set_dataset(dataset_name, instatus)
        elif(self.processor_data.input_params.instatus_filename):
            self.processor_data.set_dataset_from_file(dataset_name, self.processor_data.input_params.instatus_filename)
        # Special setup required for regular instatus file
        self._prepare_status_file()

    def __del__(self) -> None:
        """Ensure memory is released and the database connection is closed."""
        del self.processor_data
        if self._is_private_connection:
            self._dbconn.close()

    @classmethod
    def from_file(cls, input_filepath: str | Path, indata: pa.Table | pd.DataFrame | None = None,
                 indata_aux: pa.Table | pd.DataFrame | None = None, indata_hist: pa.Table | pd.DataFrame | None = None,
                 instatus: pa.Table | pd.DataFrame | None = None, instatus_hist: pa.Table | pd.DataFrame | None = None,
                 dbconn: duckdb.DuckDBPyConnection | None = None) -> "Processor":
        """Initialize a :class:`src.banffprocessor.processor.Processor` object from a JSON file.

        :param input_filepath: The full path to the JSON file containing the input parameters
            required to run the processor. The containing folder will be used as the
            default location for required and optional files for the operation of the
            processor. If a value is provided for an alternate filepath/folder parameter in
            this file, that will be used instead of the containing folder.
        :type input_filepath: str | pathlib.Path
        :param indata: The indata dataset, defaults to None
        :type indata: :class:`pyarrow.Table` | :class:`pandas.DataFrame` | None, optional
        :param indata_aux: The indata_aux dataset, defaults to None
        :type indata_aux: :class:`pyarrow.Table` | :class:`pandas.DataFrame` | None, optional
        :param indata_hist: The indata_hist dataset, defaults to None
        :type indata_hist: :class:`pyarrow.Table` | :class:`pandas.DataFrame` | None, optional
        :param instatus: The instatus dataset, defaults to None
        :type instatus: :class:`pyarrow.Table` | :class:`pandas.DataFrame` | None, optional
        :param instatus_hist: The instatus_hist dataset, defaults to None
        :type instatus_hist: :class:`pyarrow.Table` | :class:`pandas.DataFrame` | None, optional
        :param dbconn: A DuckDBPyConnection to use for storing required data and metadata.
            If not provided an in-memory DB will be instantiated, defaults to None
        :type dbconn: :class:`duckdb.DuckDBPyConnection` | None, optional
        :return: The :class:`src.banffprocessor.processor.Processor` object created using
            the specified parameters
        :rtype: :class:`src.banffprocessor.processor.Processor`
        """
        return cls(input_params=ProcessorInput.from_file(input_filepath), indata=indata,
                   indata_aux=indata_aux, indata_hist=indata_hist, instatus=instatus,
                   instatus_hist=instatus_hist, dbconn=dbconn)

    def _load_plugins(self) -> None:
        """Load all built-in banff procedures from their procedure classes in the project.

        Also loads all available user plugins from the user's input or plugin folder.

        :raises ProcessorInputParameterError: If the `processor_data` attribute's
            `input_params` contains a `plugin_folder` parameter but the directory
            cannot be found
        """
        # Go through all the banff_procedures modules available
        for mod_name in banff_procedures.__all__:
            # Get the module, check if has a register method, indicating it
            # has plugins within, and if so, call the registration method
            module = sys.modules["banffprocessor.procedures.banff_procedures." + mod_name]
            if(hasattr(module, "register")):
                module.register(factory)

        if(not self.processor_data.input_params.user_plugins_folder):
            msg = _("No explicit user plugins folder was set and no \\plugins "
                    "subfolder was found in the input folder. No plugins were loaded.")
            log_lcl.info(msg)
            # If there is no plugins folder we can just return as the user likely didn't
            # intend to include any plugins
            return

        # Load all user plugins from the plugin_folder
        loader.load_plugins(self.processor_data.input_params.user_plugins_folder)

    def _prepare_status_file(self) -> None:
        """Process the initial status_file file as loaded from an instatus file.

        Ensures the correct configuration of JOBID and SEQNO columns and copies
        final results to status_log.
        """
        # Only necessary for instatus/status_file, others don't need preparation
        status_file_obj = self.processor_data.get_dataset("status_file", create_if_not_exist=True, ds_format="object")
        status_file_ds = status_file_obj.ds

        if(status_file_ds is not None and not table_empty(status_file_ds)):
            job_id_label = None
            seqno_label = None

            # Create a table schema to ensure the jobid and seqno columns are correctly formatted
            new_schema = status_file_ds.schema
            for col in status_file_ds.column_names:
                if(col.upper() in ["JOBID", "JOB_ID"]):
                    job_id_label = col

                    # Make sure that the jobid column is the correct dtype
                    col_index = status_file_ds.column_names.index(col)
                    field = status_file_ds.field(col_index)
                    if(field.type != pa.string()):
                        new_schema = new_schema.set(col_index, pa.field(col, pa.string()))
                elif(col.upper() == "SEQNO"):
                    seqno_label = col

                    # Make sure that the seqno column is the correct dtype
                    col_index = status_file_ds.column_names.index(col)
                    field = status_file_ds.field(col_index)
                    if(field.type != pa.float32()):
                        new_schema = new_schema.set(col_index, pa.field(col, pa.float32()))

            # Set the new schema with the updated seqno dtype if necessary
            if(new_schema is not status_file_ds.schema):
                status_file_ds = status_file_ds.cast(new_schema)

            # If the user hasn't included jobid and seqno, add them now with empty values
            # Only jobid is expected but they are usually added as a pair
            if(job_id_label is None):
                job_id_label = "JOBID"
                if(seqno_label is None):
                    seqno_label = "SEQNO"
                status_file_ds = add_single_value_column(status_file_ds,
                                                        job_id_label,
                                                        self.processor_data.input_params.job_id,
                                                        pa.string())
                # Hypothetically possible for SEQNO to exist with no JOBID col
                status_file_ds = add_single_value_column(status_file_ds, seqno_label, 0, pa.float32())
            else:
                if(seqno_label is None):
                    seqno_label = "SEQNO"
                    status_file_ds = add_single_value_column(status_file_ds, seqno_label, 0, pa.float32())

                new_job_id_col = []
                new_seqno_col = []
                change_flag = False

                # Build new columns with unwanted values replaced with None
                for i in range(len(status_file_ds)):
                    job_id_val = status_file_ds[job_id_label][i].as_py()
                    seqno_val = status_file_ds[seqno_label][i].as_py()

                    # If EITHER of JOBID or SEQNO are blank, treat both as blank regardless of the JOBID value
                    # Also, for any JOBID/SEQNO pairs in which the JOBID is the same as the current
                    # job_id input parameter, replace the values with null/empty to reduce
                    # confusion of status records from previous job runs being included as if
                    # they were results from the current job run
                    if(job_id_val == self.processor_data.input_params.job_id or
                       job_id_val is None or job_id_val.isspace() or seqno_val is None):
                        new_job_id_col.append(None)
                        new_seqno_col.append(None)
                        change_flag = True
                    else:
                        new_job_id_col.append(job_id_val)
                        new_seqno_col.append(seqno_val)

                if(change_flag):
                    col_index = status_file_ds.column_names.index(job_id_label)
                    field = status_file_ds.field(col_index)
                    status_file_ds = status_file_ds.set_column(col_index, field, pa.array(new_job_id_col, pa.string()))
                    col_index = status_file_ds.column_names.index(seqno_label)
                    field = status_file_ds.field(col_index)
                    status_file_ds = status_file_ds.set_column(col_index, field, pa.array(new_seqno_col, pa.float32()))

                #TODO: Implement support for process blocks
                # Technically a user could have job_ids in their jobs file
                # that differ from the input parameter job_id. However with the
                # addition of process blocks it is somewhat difficult to parse
                # which exact job_ids are relevant to the current job and which
                # are extraneous.

                msg = _("The current job_id value {} may have been found on the instatus file. "
                        "If it was, the SEQNO and JOBID values for those records, and any with "
                        "a missing JOBID, have been replaced with empty values.").format(self.processor_data.input_params.job_id)
                log_lcl.info(msg)

            # We also want a copy of instatus in status_log
            self.processor_data.set_dataset("status_log", copy_table(status_file_ds))
            status_file_obj.ds = status_file_ds

    def execute(self) -> None:
        """Execute the Banff Processor.

        Iterates over the :class:`banffprocessor.metadata.Jobs` entries in
        the `processor_data` `metaobjects` collection and performs the respective
        Banff or user defined procedures.

        :raises ProcedureReturnCodeError: If the return code returned by a Banff
            or user defined procedure is non-zero
        """
        # alias for easier use
        bd = self.processor_data

        # Get the job steps we are running
        steps_to_run = bd.metaobjects.get_job_steps(bd.input_params.job_id)

        if(not self.is_child_block):
            msg = self._get_execution_header()
            write_to_console(msg)
            log_lcl.info(msg)

        for job_step in steps_to_run:
            # Increment our overall step count
            bd.curr_step_count += 1

            # Get the time before execution
            # Note that perf_counter is the preferred option but we are want to print the full datetime stamp
            # to match the previous version of the processor. This is why we use time or datetime instead.
            start_time = datetime.now() # noqa: DTZ005

            # Run protocols
            curr_proc = factory.get_procedure(job_step.process)
            is_built_in = job_step.process in banff_procedures.__all__ or job_step.process == "job"

            # grab our by_varlist if not done yet and we don't already have it for the same byid
            # Compare the byid in the new job_step against the previous
            if(bd.current_job_step is None or job_step.byid != bd.current_job_step.byid):
                bd.by_varlist = bd.metaobjects.get_varlist_fieldids(job_step.byid)
                if(job_step.byid and not job_step.byid.isspace() and not bd.by_varlist):
                    msg = _("Error in byid field of job_id {} and seqno {}. Byid was set but "
                            "does not refer to any varlists found in the varlist metadata.",
                            ).format(job_step.jobid, job_step.seqno)
                    log_lcl.exception(msg)
                    raise MetadataConstraintError(msg)

            bd.current_uservars = None
            if(job_step.specid):
                bd.current_uservars = bd.metaobjects.get_user_vars_dict(job_step.specid, job_step.process)
            # set this after fetching the new by_varlist to ensure we don't overwrite
            # the reference to the previous job step (which is in current_job_step)
            bd.current_job_step = job_step

            # NOTE: If DonorImputation and MassImputation are both run in a single job, but the
            # ProcessOutputs metadata only includes (donorimp, outdonormap), the final outdonormap
            # file will only contain outputs from DonorImputation, NOT MassImputation
            if(bd.input_params.output_custom):
                bd.custom_outputs = bd.metaobjects.get_process_outputs(job_step.process)
            else:
                # If output setting is minimal or all, we don't need to specify any custom outputs
                bd.custom_outputs = []

            # Clear unwanted columns from status_file every new step
            bd.clean_status_file()

            # Print the header string
            log_lcl.info(self._get_step_header())

            # Perform process filters
            bd.apply_process_controls()

            # Note: we only check modifications made to indata (imputed_file) and instatus (status_file)
            # If other data is changed, it will go undetected.
            if(not is_built_in):
                # Retain a temporary reference to the current tables
                #NOTE: this is intentionally set after the process controls are applied therefore
                # these would be references to the filtered version, if one exists.
                indata_pre_execute = bd.get_dataset("imputed_file", create_if_not_exist=True)
                instatus_pre_execute = bd.get_dataset("status_file", create_if_not_exist=True)

            pre_execute_datasets = set(bd.datasets.keys())

            # Execute and get the return code
            #TODO: wrap in try...except and attach the current job info to the message.
            # This way we can avoid having to repeat that info in every error message
            # the procs throw and just have it once here.
            rc = curr_proc.execute(bd)
            log_lcl.info("%s return code: %s", job_step.process, rc)
            if(rc != 0):
                msg = _("Non-zero return code: {} returned by {} in job {} at seqno {}").format(
                    rc, job_step.process, job_step.jobid, job_step.seqno)
                log_lcl.exception(msg)
                raise ProcedureReturnCodeError(msg)

            # Get the current datasets, don't create if they don't exist as we want
            # to know if they're None.
            # NOTE: We want to get the filtered version if it exists since that's what
            # was passed in and we want to compare what should be the same dataset reference
            curr_imputed = bd.get_dataset("imputed_file")
            curr_status_file = bd.get_dataset("status_file")

            # If a UDP was run, we want to check if indata or instatus were updated directly
            # If these references don't match the user must have created a new table and
            # updated the reference, so warn or kill the program
            if(not is_built_in and (indata_pre_execute is not curr_imputed or
                                    instatus_pre_execute is not curr_status_file)):
                # If no process filter: accept the updates but warn the user, just in case
                msg = _("Indata or instatus were modified. If this was not intended make "
                            "sure that any new tables you create are not saved back to the "
                            "processor_data object. Instead save your updates to the "
                            "outdata and outstatus attributes on processor_data")
                log_lcl.warning(msg)

            # Release these references now that we are 100% done with the old tables
            indata_pre_execute = None
            instatus_pre_execute = None

            # Remove filtered datasets since the proc has completed so references
            # below will use the original when performing updates
            bd.clear_filtered_data()

            # Get the out datasets but don't pop them until after update methods have run
            curr_outstatus = bd.get_dataset("outstatus")
            curr_outdata = bd.get_dataset("outdata")

            if(curr_outstatus):
                if(table_empty(curr_outstatus)):
                    # This can be either intentional or a mistake, depending on the plugin
                    msg = _("Process {} in job {} at seqno {} set an outstatus dataset but "
                            "it was empty.").format(job_step.process, job_step.jobid, job_step.seqno)
                    log_lcl.warning(msg)
                elif(curr_outstatus is curr_status_file):
                    # If the user didn't copy() when forming outstatus from status_file
                    # the update will break. So give them a more informative error.
                    msg = _("Process {} in job {} at seqno {}. processor_data.outstatus should not "
                        "reference the same dataset as instatus.").format(job_step.process, job_step.jobid,
                                                                          job_step.seqno)
                    log_lcl.exception(msg)
                    raise UserDefinedPluginError(msg)
                else:
                    # Updates status_file and status_log files using the outstatus dataset
                    bd.update_status()
                    # We no longer save non-cumulative files

            if(curr_outdata):
                if(table_empty(curr_outdata)):
                    # This can be either intentional or a mistake, depending on the plugin
                    msg = _("Process {} in job {} at seqno {} set an outdata dataset but "
                            "it was empty.").format(job_step.process, job_step.jobid, job_step.seqno)
                    log_lcl.warning(msg)
                elif(curr_outdata is curr_imputed):
                    # If the user didn't copy() when forming outdata from indata (imputed_file)
                    # the update will break. So give them a more informative error.
                    msg = _("Process {} in job {} at seqno {}. processor_data.outdata "
                            "should not reference the same dataframe as indata.").format(
                                job_step.process, job_step.jobid, job_step.seqno)
                    log_lcl.exception(msg)
                    raise UserDefinedPluginError(msg)
                else:
                    # Updates imputed_file using outdata
                    bd.update_imputed_file()
                    # Note that we no longer keep the non-cumulative files

            # Now that these have been used in their respective update methods and saved under
            # new names (if desired), we remove these references so that the next proc doesn't
            # accidentally use the same dataset.
            bd.pop_dataset("outstatus")
            bd.pop_dataset("outdata")

            # Remove the single-step outputs and update their respective cumulative version
            bd.update_cumulatives(pre_execute_datasets)

            # Print the footer string, which also logs time/duration if specified in options
            end_time = datetime.now() # noqa: DTZ005
            # list indexed from 0 so add 1 to accurately count steps

            # The log's Streamhandler is set to only ERROR, therefore need to print()
            # as we want this to be the only other thing seen in console
            # Also log to INFO so that it will also show in the log file, if one is set
            log_lcl.info(self._get_step_footer(bd.curr_step_count, start_time, end_time))
            write_to_console(self._get_console_step_footer(bd.curr_step_count))

            # Reset local variables so the garbage collector can clean them up
            curr_outdata = None
            curr_outstatus = None
            curr_imputed = None
            curr_status_file = None
            curr_proc = None
            msg = None
            end_time = None
            # Just in case
            pre_execute_datasets = None

        if(not self.is_child_block):
            msg = self._get_execution_footer()
            write_to_console(msg)
            log_lcl.info(msg)

        # clean the status file one last time
        bd.clean_status_file()

    def save_outputs(self) -> None:
        """Call the save_outputs method for the current job's processor_data."""
        self.processor_data.save_outputs()

    def _get_execution_header(self) -> str:
        border_string = "="*112
        msg = "\n" + border_string + "\n"
        msg += _("Job ID                       : {}\n").format(self.processor_data.input_params.job_id)
        msg += _("Banff Processor Version      : {}\n").format(bpp.__version__)
        msg += _("Banff Version                : {}\n").format(banff.__version__)
        msg += _("Support Email                : {}\n").format("banff@statcan.gc.ca")
        msg += _("Start Time                   : {} ({})\n").format(datetime.now().strftime("%c"), datetime.now().astimezone().tzinfo) # noqa: DTZ005
        msg += border_string

        return msg

    def _get_execution_footer(self) -> str:

        time_store_table = self.processor_data.get_dataset("time_store")
        total_duration = pc.max(time_store_table["total_job_duration"]).as_py()

        border_string = "="*112
        msg = "\n" + border_string + "\n"
        msg += _("The Banff Processor executed {} successfully. ").format(self.processor_data.current_job_step.jobid)
        msg += _("Duration: {}").format(total_duration)
        msg += "\n" + border_string + "\n"

        return msg

    def _get_step_header(self) -> str:
        """Return a string containing the header text for the current job step.

        :return: The header string for the current job step.
        :rtype: str
        """
        border_string = "="*100
        msg = "\n" + border_string + "\n"
        msg += _("JOBID: {}\n").format(self.processor_data.current_job_step.jobid)
        msg += _("PROCESS: {}\n").format(self.processor_data.current_job_step.process)
        msg += _("SEQNO: {}\n").format(self.processor_data.current_job_step.seqno)
        msg += _("SPECID: {}\n").format(self.processor_data.current_job_step.specid)
        msg += _("CONTROLID: {}\n").format(self.processor_data.current_job_step.controlid)
        msg += border_string
        return msg

    def _get_step_footer(self, cur_step_index: int, start_time: datetime|float, end_time: datetime|float) -> str:
        """Return a string containing the footer text for the current job step which includes
        the computed start/end time and duration. Also saves time values to the timestore dataset.

        :param start_time: The start time of the job step as a datetime object
            or a perf_counter float output, defaults to None
        :type start_time: datetime | float | None, optional
        :param end_time: The end time of the job step as a datetime object
            or a perf_counter float output, defaults to None
        :type end_time: datetime | float | None, optional
        :raises TypeError: If `start_time` or `end_time` are not provided but the
            TIME or TIMESTORE option is set
        :raises TypeError: If `start_time` or `end_time` are not datetime or float
        :return: The footer string for the current job step.
        :rtype: str
        """
        time_print = self.processor_data.input_params.time
        time_store = self.processor_data.input_params.time_store
        border_string = "="*100

        job_progress = round((cur_step_index/self.processor_data.total_job_steps)*100)
        footer = "\n" + border_string + "\n"
        footer += _("END OF PROCESS: {}\n").format(self.processor_data.current_job_step.process)
        footer += _("JOBID: {}\n").format(self.processor_data.current_job_step.jobid)
        footer += _("SEQNO: {}\n").format(self.processor_data.current_job_step.seqno)
        footer += _("SPECID: {}\n").format(self.processor_data.current_job_step.specid)
        footer += _("JOB PROGRESS: {}/{} - {}%\n").format(cur_step_index, self.processor_data.total_job_steps, job_progress)

        # If the start and end time were not provided, skip duration
        if (start_time is None or end_time is None):
            return (footer + border_string)

        duration = end_time - start_time
        start_stamp = ""
        end_stamp = ""
        if(isinstance(start_time, datetime) and isinstance(end_time, datetime)):
            # datetime will give us ms but we need to truncate the string with [:-4]
            # to get the same reduced precision as the SAS
            start_stamp = start_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-4]
            end_stamp = end_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-4]

            if(time_print):
                footer += _("START TIME: {}\n").format(start_stamp)
                footer += _("END TIME: {}\n").format(end_stamp)

        elif(isinstance(start_time, float) and isinstance(end_time, float)):
            duration = timedelta(seconds=(duration))
        else:
            msg = _("start_time or end_time must be datetime objects or floats.")
            log_lcl.exception(msg)
            raise TypeError(msg)

        # datetime will give us ms but we need to truncate the string with [:-4]
        # to get the same reduced precision as the SAS
        duration_stamp = str(duration)[:-4]
        footer += _("STEP DURATION: {}\n").format(duration_stamp)

        if(self.processor_data.total_job_duration is None):
            self.processor_data.total_job_duration = duration
        else:
            self.processor_data.total_job_duration = self.processor_data.total_job_duration + duration

        new_total_duration_stamp = str(self.processor_data.total_job_duration)[:-4]
        footer += _("TOTAL DURATION: {}\n").format(new_total_duration_stamp)

        if(time_store):
            if(start_stamp and end_stamp):
                self._store_time(start_stamp, end_stamp, duration_stamp, new_total_duration_stamp)
            else:
                msg = _("TIMESTORE option was set but start_time and end_time were not passed in as datetime stamps.")
                log_lcl.warning(msg)

        return (footer + border_string)

    def _get_console_step_footer(self, cur_step_index: int) -> str:

        def truncate_output(val: str, max_len: int) -> str:
            return (val[:max_len - 2] + "..") if len(val) > max_len else val

        job_progress = round((cur_step_index/self.processor_data.total_job_steps)*100)
        job_progress = str(job_progress) + "%"

        time_store_table = self.processor_data.get_dataset("time_store")

        # Get the last (should be the latest) record in the time_store table
        time_store_curr_rec = time_store_table.slice(offset=time_store_table.shape[0]-1)
        duration = time_store_curr_rec["duration"][0].as_py()
        total_duration = time_store_curr_rec["total_job_duration"][0].as_py()

        step = f"{cur_step_index}/{self.processor_data.total_job_steps}"

        curr_process = self.processor_data.current_job_step.process
        if(curr_process == "job"):
            curr_process = f"job:{self.processor_data.current_job_step.specid}"

        footer = ""
        if cur_step_index == 1:
            footer = _("STEP       JOBID       PROCESS               SEQNO   END TIME         DURATION         TOTAL DURATION   PROGRESS\n")
            footer +=  "=========  ==========  ====================  ======  ===============  ===============  ===============  ========\n"

        footer += _("{:<9}  {:<10}  {:<20}  {:<6}  {:<15}  {:<15}  {:<15}  {:>8}").format(step,
                                                                                  truncate_output(self.processor_data.current_job_step.jobid, 10),
                                                                                  truncate_output(curr_process, 20),
                                                                                  self.processor_data.current_job_step.seqno,
                                                                                  datetime.now().strftime("%X"), # noqa: DTZ005
                                                                                  duration,
                                                                                  total_duration,
                                                                                  job_progress)
        return footer

    def _store_time(self, start_stamp: str, end_stamp: str,
                    duration: str, total_job_duration: str) -> None:
        """Store the timestamps of the start and end time and the duration of the current job step to the timestore output dataset.

        :param start_time: The timestamp of the procedure start time
        :type start_time: str
        :param end_time: The timestamp of the procedure end time
        :type end_time: str
        :param duration: The difference between the start and end times in seconds
        :type duration: str
        :param total_job_duration: The total duration of the job up to this point
        :type total_job_duration: str
        """
        specid = "" if self.processor_data.current_job_step.specid is None else self.processor_data.current_job_step.specid
        time_store_new = pa.table({"job_id": [self.processor_data.current_job_step.jobid],
                                   "process": [self.processor_data.current_job_step.process],
                                   "seqno": [self.processor_data.current_job_step.seqno],
                                   "specid": [specid],
                                   "start_time": [start_stamp],
                                   "end_time": [end_stamp],
                                   "duration": [duration],
                                   "total_job_duration": [total_job_duration]})

        time_store_name = "time_store"
        time_store_curr_obj = self.processor_data.get_dataset(time_store_name, ds_format="object")
        # append a new record with the info for this job run
        if(time_store_curr_obj is not None):
            # As these 2 tables are only produced/modified here we shouldn't
            # need to set any promote_options for now as it might obscure an error
            time_store_curr_obj.ds = pa.concat_tables([time_store_curr_obj.ds, time_store_new])
        else:
            self.processor_data.set_dataset(time_store_name, time_store_new)

def write_to_console(text: str) -> None:
    """Write text to the console.

    Write the text to the console instead of the log file. This was put in
    a function as there may be a better way to do this.
    """
    print(text) # noqa: T201

def get_args(args:list | str | None = None) -> argparse.ArgumentParser:
    """Create an argument parser.

    Example args -> ["my_filename.xlsx", "-o", "/my/out/folder", "-l", "fr"]
    """
    parser = argparse.ArgumentParser(description="Execute the Banff Processor using the parameters in the provided JSON file.\n\n"
                                     "Exécutez le processeur Banff à l'aide des paramètres du fichier JSON fourni.",
                                     formatter_class=RawTextHelpFormatter)

    # First argument is positional, required by default
    parser.add_argument("filename", help="The name of the JSON file that contains the Banff Processor parameters.\n"
                        "Le nom du fichier JSON qui contient les paramètres du processeur Banff.")

     # Second argument is set by flag
    parser.add_argument("-l", "--lang", default="en",
                        help="Set the language, supported langauges are en for English and fr for French. \n"
                        "Définissez la langue, les langues prises en charge sont en pour l'anglais et fr pour le français.")

    return parser.parse_args(args)

def main(iargs: list | str | None = None) -> None:
    """Call the Banff Processor function.

    Used when running this module from the command line. Created to faciliate testing.
    """
    if iargs is None:
        iargs = sys.argv[1:]

    args = get_args(iargs)

    bpp.set_language(bpp.SupportedLanguage[args.lang])

    my_bp = Processor.from_file(args.filename)
    my_bp.execute()
    my_bp.save_outputs()

def init() -> None:
    """Call the main function.

    Used when running this module from the command line. Created to faciliate testing.
    """
    if __name__  == "__main__":
        sys.exit(main())

init()
