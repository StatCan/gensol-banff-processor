import copy
from datetime import datetime
from pathlib import Path
from typing import ClassVar

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from banff import io_util
from banff.io_util import handle_arrow_string_data
from banff.io_util import type_converters as tc
from banff.proc import BanffProcedure

import banffprocessor.processor_logger as plg
from banffprocessor.exceptions import MetadataConstraintError, ProcessControlError, ProcessorInputParameterError, UserDefinedPluginError
from banffprocessor.metadata.metaobjects import MetaObjects
from banffprocessor.metadata.models.jobs import Jobs
from banffprocessor.metadata.models.processcontrols import ProcessControlType
from banffprocessor.nls import _
from banffprocessor.processor_input import ProcessorInput
from banffprocessor.util.dataset import Dataset, add_single_value_column, copy_table, get_dataset_real_name, table_empty

log_lcl = plg.get_processor_child_logger("processor_data")

class ProcessorData:
    """Helper class for the Processor in order to allow easier passing of data to user procs.

    :attribute _datasets: A collection of datasets for the current job
    :type _datasets: dict[str, :class:`banffprocessor.util.dataset.Dataset`]
    :attribute input_params: The object containing the input parameters from the user's input JSON file
    :type input_params: :class:`src.banffprocessor.processor_input.ProcessorInput`
    :attribute metaobjects: The collection of metadata objects
    :type metaobjects: :class:`src.banffprocessor.metadata.MetaObjects`
    :attribute by_varlist: The list of by variable fieldIDs for the current job step
    :type by_varlist: list[str]
    :attribute current_job_step: The :class:`src.banffprocessor.metadata.models.Jobs` object for the
        current job step being run
    :type current_job_step: :class:`src.banffprocessor.metadata.models.Jobs`
    :attribute current_uservars: A mapping of `var` to `value` attributes for the
        :class:`src.banffprocessor.metadata.models.Uservars` objects for the current job step
    :type current_uservars: dict[str,str]
    :attribute custom_outputs: The table names that are requested to be output from a proc used in the job
    :type custom_outputs: list[str]
    :attribute total_job_duration: Used for tracking runtime when performing execute()
    :type total_job_duration: datetime
    :attribute curr_step_count: The current step in the absolute sequence of all job steps.
    :type curr_step_count: int
    """

    _datasets: dict[str, Dataset]

    input_params: ProcessorInput
    metaobjects: MetaObjects

    by_varlist: list[str]
    current_job_step: Jobs
    current_uservars: dict[str,str]
    custom_outputs: list[str]
    _minimal_outputs: ClassVar[list[str]] = ["imputed_file", "status_file", "status_log",
                                             "outreject", "outreject_all", "time_store"]

    total_job_duration: datetime
    curr_step_count: int

    @property
    def total_job_steps(self) -> int | None:
        """Return the total number of job steps for the current job."""
        return self.metaobjects.total_job_steps if self.metaobjects else None

    @property
    def dbconn(self) -> duckdb.DuckDBPyConnection:
        """Return a connection to the database being used."""
        return self._dbconn

    @property
    def minimal_outputs(self) -> list[str]:
        """Return the minimal list of names of tables output by default."""
        return self._minimal_outputs

    @property
    def datasets(self) -> dict[str, Dataset]:
        """Return a dictionary of datasets being tracked by the ProcessorData object."""
        return self._datasets

    def __init__(self, input_params: ProcessorInput | None = None,
                 dbconn: duckdb.DuckDBPyConnection | None = None) -> None:
        """Construct an instance of ProcessorData.

        :param input_params: The object containing the input parameters from the user's
            input JSON file
        :type input_params: :class:`src.banffprocessor.processor_input.ProcessorInput`
        """
        self.input_params = input_params
        self.by_varlist = []
        self._datasets = {}
        self._filtered_data = {}
        self.current_job_step = None
        self.metaobjects = None
        self.custom_outputs = None

        self.total_job_duration = None
        # We increment the step count at the beginning of every job step in the execute() loop
        self.curr_step_count = 0

        self._dbconn = dbconn
        if self._dbconn is None:
            self._dbconn = duckdb.connect(database=":memory:")
            self._is_private_connection = True
        else:
            self._is_private_connection = False

    def __del__(self) -> None:
        del self.metaobjects
        if self._is_private_connection:
            self._dbconn.close()

    @property
    def indata(self) -> pa.Table:
        """The indata dataset for a Banff procedure.

        :getter: Returns the imputed_file input dataset
        :setter: Sets the imputed_file input dataset
        :type: pa.Table
        """
        return self.get_dataset("indata", create_if_not_exist=True)

    @indata.setter
    def indata(self, value: pa.Table | pd.DataFrame | Dataset) -> None:
        self.set_dataset("indata", value)

    # instatus has no setter method as is is only intended
    # to provide easy access for reading and producing a different output.
    @property
    def instatus(self) -> pa.Table:
        """The instatus dataset for a Banff procedure.

        :getter: Returns the status_file dataset
        :type: pa.Table
        """
        return self.status_file

    @instatus.setter
    def instatus(self, value: pa.Table | pd.DataFrame | Dataset) -> None:
        self.status_file = value

    @property
    def status_file(self) -> pa.Table:
        """The status_file dataset for a Banff job.

        :getter: Returns the status_file dataset
        :setter: Sets the status_file dataset
        :type: pa.Table
        """
        return self.get_dataset("status_file", create_if_not_exist=True)

    @status_file.setter
    def status_file(self, value: pa.Table | pd.DataFrame | Dataset) -> None:
        self.set_dataset("status_file", value)

    # Outdata and Outstatus are only for outputs from user procs, otherwise the
    # built-in banff procs update imputed_file/status_file directly and
    # save their respective outdata/status files as specially named files
    @property
    def outdata(self) -> pa.Table:
        """The outdata dataset of a procedure.

        Required to be set for a procedure to update the imputed_file on completion.

        :getter: Returns the outdata dataset
        :setter: Sets the outdata dataset
        :type: pa.Table
        """
        return self.get_dataset("outdata")

    @outdata.setter
    def outdata(self, value: pa.Table | pd.DataFrame) -> None:
        self.set_dataset("outdata", value)

    @property
    def outstatus(self) -> pa.Table:
        """The outstatus dataset for a Banff procedure.

        Required to be set for a procedure to update the status_file dataset on completion.

        :getter: Returns the outstatus dataset
        :setter: Sets the outstatus dataset
        :type: pa.Table
        """
        return self.get_dataset("outstatus")

    @outstatus.setter
    def outstatus(self, value: pa.Table | pd.DataFrame) -> None:
        self.set_dataset("outstatus", value)

    def output_required(self, output_name : str) -> bool:
        """Return true if the output is required for the current job step."""
        std_name = get_dataset_real_name(output_name)
        return (std_name in self.minimal_outputs or self.input_params.output_all or
                (std_name in self.custom_outputs))

    def get_dataset(self, name: str, create_if_not_exist: bool = False,
                    ds_format: str = "pyarrow") -> pa.Table | pd.DataFrame | Dataset | None:
        """Get a dataset by `name` (case-insensitive) in format `ds_format`.

        If no dataset is found returns `None` unless `create_if_not_exist` is True in which case a
        new dataset is created under the name `name` with an empty pyarrow Table. This new Table
        is then returned.

        :param name: The name of the dataset to retrieve
        :type name: str
        :param create_if_not_exist: Creates a dataset with `name` if no existing one
            was found, defaults to False
        :type create_if_not_exist: bool, optional
        :param ds_format: A string with the name of the format to return the dataset in.
            Possible options are "pyarrow" for a pyarrow Table, "pandas" for a pandas
            DataFrame, and "object" for a :class:`banffprocessor.util.Dataset` object, defaults to "pyarrow"
        :type ds_format: str, optional
        :return: The dataset with `name` if it is found or `create_if_not_exist` is set,
            `None` if not
        :rtype: `pa.Table` | `pd.DataFrame` | banffprocessor.util.dataset.Dataset | None
        """
        std_name = get_dataset_real_name(name)

        # Load a Historic/Auxillary file if one was provide but it has not yet been read from disk
        if(std_name not in self._datasets):
            if(std_name == "indata_hist" and self.input_params.indata_hist_filename is not None):
                self.set_dataset_from_file(std_name, self.input_params.indata_hist_filename)
            elif(std_name == "indata_aux" and self.input_params.indata_aux_filename is not None):
                self.set_dataset_from_file(std_name, self.input_params.indata_aux_filename)
            elif(std_name == "instatus_hist" and self.input_params.instatus_hist_filename is not None):
                self.set_dataset_from_file(std_name, self.input_params.instatus_hist_filename)

        if(std_name in self._datasets):
            ds_obj = self._datasets[std_name]
            if(ds_format != "object"):
                dataset = ds_obj.ds_filtered if ds_obj.ds_filtered is not None else ds_obj.ds
        elif(create_if_not_exist):
            # No existing dataset was found but we were told to make one.
            # So add a new entry with an empty Table
            dataset = pa.table([])
            ds_obj = Dataset(std_name, dataset, dbconn=self.dbconn)
            self.set_dataset(std_name, ds_obj)
        else:
            dataset = None
            ds_obj = None

        return ds_obj if ds_format=="object" else ds_to_format(dataset, ds_format)

    def set_dataset(self, name: str, ds: pa.Table | pd.DataFrame | Dataset) -> None:
        """Set `ds` as an entry in the dataset collection under `name` (case-insensitive).

        If a dataset under `name` already exists, `ds` will be saved as the current output
        version of the `name` dataset and will be used to update the cumulative version
        when the current job step completed. If `name` identifies a dataset that is produced
        by default, `ds` instead directly overwrites the cumulative version, and no current
        output version is saved.

        :param name: The name of the dataset to set
        :type name: str
        :param ds: The dataset to set
        :type ds: `pyarrow.Table` | `pandas.DataFrame` | banffprocessor.util.dataset.Dataset
        """
        std_name = get_dataset_real_name(name)

        if(isinstance(ds, Dataset)):
            # If given as an object, just overwrite existing
            # Assumes that the underlying dataset does not need any preparation
            self._datasets[std_name] = ds
        else:
            # Ensuring that the datasets are using type string for character data.
            # Sometimes pandas sets the type as large_string
            dataset: pa.Table = handle_arrow_string_data(ds_to_format(ds, "pyarrow"), dest_type=pa.string())

            if(std_name in self._datasets):
                curr_ds = self._datasets[std_name]

                if(curr_ds.ds_filtered is not None):
                    msg = _("The Banff Processor does not currently support direct updates "
                            "made to any datasets with a process control applied to them.")
                    log_lcl.exception(msg)
                    raise UserDefinedPluginError(msg)
                if(std_name in self.minimal_outputs):
                    # Minimal outputs just get overwritten, not updated using ds_curr_output
                    curr_ds.ds = dataset
                else:
                    # If the dataset already exists as an object, add this as the current output,
                    # which will be used to update the cumulative version after the proc completes
                    curr_ds.ds_curr_output = dataset
            else:
                self._datasets[std_name] = Dataset(std_name, dataset, dbconn=self.dbconn)

    def set_dataset_from_file(self, name: str, data_file: str | Path) -> None:
        """Create a :class:`pa.Table` from the data file at `data_file` and load it to the
        dataset collection under the name `name` (case-insensitive).

        If `data_file` only contains a filename and not a full path, the input parameters are
        used to determine the appropriate directory to look in. Any existing dataset of the
        same name is replaced.

        :param name: The name to identify the resultant dataset by
        :type name: str
        :param data_file: The full filepath or just filename of the data file to create
            a dataset from
        :type data_file: str | Path
        """
        self.set_dataset(name, self.load_dataset_from_file(data_file))

    def pop_dataset(self, name: str) -> Dataset | None:
        """Remove the :class:`banffprocessor.util.dataset.Dataset` object found under
        `name` (case-insensitive) from the dataset collection and return the object if it exists.

        Returns `None` if the dataset is not found.

        :param name: The name of the dataset to pop
        :type name: str
        :return: The pop()'d dataset, `None` if not found
        :rtype: pd.DataFrame | None
        """
        name_lower = get_dataset_real_name(name)
        ds = self._datasets.pop(name_lower, None)
        if(ds):
            # We want to make sure we unregister now. If it's done in the Dataset
            # __del__() method, we can't guarantee de-registration until the object is GC'd
            ds.unregister_table()
        return ds

    def clear_filtered_data(self) -> None:
        """Clear all filtered datasets off of the dataset objects in the _dataset collection.

        Use once a proc has finished executing as we no longer need the filtered data.
        """
        for ds in self._datasets.values():
            ds.ds_filtered = None

    def update_cumulatives(self, pre_execute_tables: set[str]) -> None:
        """Update every non-default dataset in the dataset collection with its
        respective ds_curr_output version, if the output is required by the configured
        input parameters and metadata.

        :param pre_execute_tables: The set of table names in the dataset collection prior
            to the execution of the current job step
        :type pre_execute_tables: set[str]
        """
        # We will be popping off datasets so convert to a list first
        for name, ds_obj in list(self.datasets.items()):
            # Remove the aux and hist conditions if we want those files wiped from memory after use
            if(name not in self.minimal_outputs and ("_aux" not in name and "_hist" not in name)):
                if(self.output_required(name)):
                    # The current proc requests this file, either via ALL or CUSTOM
                    self.update_file_all(ds_obj)
                elif(name not in pre_execute_tables):
                    # The current proc doesn't want this file and it wasn't
                    # created by a different proc so we can discard it
                    self.pop_dataset(name)
                else:
                    # Don't want the output from curr proc, but DO want existing Dataset object
                    # All built-ins should already have this attribute empty, but UDPs may have
                    # loaded a table they didn't want
                    ds_obj.ds_curr_output = None
                    msg = _("Output table {} was created but output settings exclude this table "
                            "from saving for the current proc and so it was discarded.").format(name)
                    log_lcl.warning(msg)

    def update_status(self) -> None:
        """Append `outstatus` dataset to `status_file` and updates `status_file`
        where `outstatus` shares the same index values.

        Also calls `update_file_all()` to update `status_log` with `outstatus`.
        """
        proc_status = self.get_dataset("outstatus")

        # If proc_status is empty, nothing to update
        if(proc_status is None or table_empty(proc_status)):
            return

        # Check against upper case column names in the unlikely chance JOBID and SEQNO were
        # originally on the user's instatus file in some other capitalization
        upper_cols = [x.upper() for x in proc_status.column_names]
        # These fields are likely added during a preceding call to updateFileAll() so don't re-add
        # them if we don't have to
        if("JOBID" not in upper_cols):
            proc_status = add_single_value_column(proc_status, "JOBID", self.current_job_step.jobid, pa.string())
        if("SEQNO" not in upper_cols):
            proc_status = add_single_value_column(proc_status, "SEQNO", self.current_job_step.seqno, pa.float32())

        status_file_obj = self.get_dataset("status_file", ds_format="object")
        status_file = status_file_obj.ds

        if(status_file_obj is None or table_empty(status_file)):
            # Create a copy of proc_status
            status_file_new = copy_table(proc_status)
        else:
            # Index values to use for concat and update
            index_cols = ["JOBID", "FIELDID"]
            if(self.input_params.unit_id):
                index_cols.append(self.input_params.unit_id.upper())

            #NOTE: Pyarrow 16.1 docs erroneously claim that it accepts a dict to rename columns,
            # and treats the dict as {old_name: new_name}. However all of the 16.1.0 branches
            # from the project's github show that the method is not yet updated to accept a dict.
            # This is an issue as it allows you to pass a dict with no error, then iterates over
            # the keys of the dict as if it is a list and renames your columns as if the key of
            # the dict is the NEW name and not the old name.
            # So make sure only lists are used for renaming until this feature is properly implemented
            proc_status_col_dict = {x.upper():x for x in proc_status.column_names}
            proc_status = proc_status.rename_columns(list(proc_status_col_dict.keys()))
            status_file_col_dict = {x.upper():x for x in status_file.column_names}
            status_file = status_file.rename_columns(list(status_file_col_dict.keys()))

            # Get the records from each dataset with unique index values (i.e. no overlap)
            proc_status_non_matching = proc_status.join(status_file, keys=index_cols, join_type="left anti")
            status_file_non_matching = status_file.join(proc_status, keys=index_cols, join_type="left anti")

            # Get records from both datasets with matching index values
            combined_status_matching = status_file.join(proc_status, keys=index_cols, join_type="inner", left_suffix="to_drop")
            # Drop the old value column from status_file to replace it with the new values from status
            # Since we want non-NaN values replaced with NaN, we can just drop the whole column
            combined_status_matching = combined_status_matching.drop_columns([x for x in combined_status_matching.column_names if "to_drop" in x])

            # Combine all of our subsets to create the final dataset
            # Note: If we can be sure that the schemas of status_file and proc_status are the same we
            # don't need to set the promote_options and this operation may be faster
            status_file_new = pa.concat_tables([status_file_non_matching, proc_status_non_matching, combined_status_matching], promote_options="permissive")

            # Revert capitalization on status_file
            # Dict feature only available in Python 3.9
            # Computes the combined dictionary where any key overlaps are won by the
            # right side dictionary
            proc_status = proc_status.rename_columns(list(proc_status_col_dict.values()))
            merged_dict = proc_status_col_dict | status_file_col_dict
            normal_columns_merged = [merged_dict[x] for x in status_file_new.column_names]
            status_file_new = status_file_new.rename_columns(normal_columns_merged)

        self.outstatus = proc_status
        self.update_file_all(proc_status, "status_log")
        status_file_obj.ds = status_file_new

    def update_file_all(self, dataset: str | pa.Table | Dataset, dataset_all_name: str | None = None) -> None:
        """Update the respective cumulative version of `dataset` using the contents of the
        non-cumulative version after adding the current jobid and seqno to it.

        If `dataset` is given as a Dataset object or the name of the object to fetch, the object may
        contain both the cumulative and curr_output versions. If it only contains the cumulative version,
        the jobid and seqno columns are still added to it if they are not yet present. As well in this case,
        the jobid and seqno column additions will be saved back to the non-cumulative dataset if
        `dataset_all_name` is seperately provided. Otherwise the changes to the non-cumulative dataset are
        discarded and only the updated cumulative version is saved.

        :param dataset: Either the name of a dataset to fetch, the Dataset object itself or a specific
        pyarrow table. If provided as a pyarrow table no changes are saved back to this dataset and
        `dataset_all_name` must be provided as well.
        :type dataset: str | pa.Table | banffprocessor.util.dataset.Dataset
        :param dataset_all_name: The name of the dataset to update using dataset_name.
            If not provided the non-cumulative dataset's name is used, defaults to None
        :type dataset_all_name: str, optional
        :raises ValueError: If `dataset` is given as a pa.Table but no `dataset_all_name` is given.
        """
        dataset_obj = None

        if(isinstance(dataset, str)):
            if(dataset_all_name):
                # If both a dataset table name AND a dataset_all table name are given,
                # we are in a special case. Most likely outreject, but could change in the future
                dataset_all_obj = self.get_dataset(dataset_all_name, create_if_not_exist=True, ds_format="object")
                dataset_obj = self.get_dataset(dataset, ds_format="object")
                dataset = dataset_obj.ds
            else:
                # If only a single table name is given, the underlying object should
                # hold both the curr_output and cumulative versions
                dataset_all_obj = self.get_dataset(dataset, create_if_not_exist=True, ds_format="object")
                dataset = dataset_all_obj.ds_curr_output
                dataset_all_obj.ds_curr_output = None
        elif(isinstance(dataset, Dataset)):
            if(dataset_all_name):
                dataset_all_obj = self.get_dataset(dataset_all_name, create_if_not_exist=True, ds_format="object")
                dataset_obj = dataset
                dataset = dataset_obj.ds
            else:
                # If we were given an object, we always use ds_curr_output to update ds_cumulative
                dataset_all_obj = dataset
                dataset = dataset_all_obj.ds_curr_output
                dataset_all_obj.ds_curr_output = None
        elif(isinstance(dataset, pa.Table)):
            if(not dataset_all_name):
                msg = _("dataset was given as a pyarrow table but no name was given for the table to update.")
                log_lcl.exception(msg)
                raise ValueError(msg)
            dataset_all_obj = self.get_dataset(dataset_all_name, create_if_not_exist=True, ds_format="object")
        else:
            msg = _("dataset was given as an invalid type. dataset must be of type str, pa.Table or Dataset.")
            log_lcl.exception(msg)
            raise TypeError(msg)

        # We only ever want to update the unfiltered version of the dataset
        dataset_all = dataset_all_obj.ds

        if(dataset is None):
            # A cumulative dataset was passed in alone and it has no ds_curr_output
            # So we swap the variables to carry out the update with an empty table
            # to ensure the JobID/seqno is added to ds_cumulative
            dataset = dataset_all
            dataset_all = pa.table([])

        # See update_status() NOTE on using dict vs list for rename_columns
        dataset_col_dict = {x.upper():x for x in dataset.column_names}
        dataset = dataset.rename_columns(list(dataset_col_dict.keys()))
        dataset_all_col_dict = {x.upper():x for x in dataset_all.column_names}
        dataset_all = dataset_all.rename_columns(list(dataset_all_col_dict.keys()))

        # Ensure the jobid and seqno for the current job step are present in the dataset first
        if("JOBID" not in dataset.column_names and "JOB_ID" not in dataset.column_names):
            dataset = add_single_value_column(dataset, "JOBID", self.current_job_step.jobid, pa.string())
            # Need this for when we revert things later
            dataset_col_dict["JOBID"] = "JOBID"
        if("SEQNO" not in dataset.column_names):
            dataset = add_single_value_column(dataset, "SEQNO", self.current_job_step.seqno, pa.float32())
            # Need this for when we revert things later
            dataset_col_dict["SEQNO"] = "SEQNO"

        # Append the new dataset to the existing dataset_all
        dataset_all_new = pa.concat_tables([dataset_all, dataset], promote_options="permissive")

        # Revert capitalization, only necessary if keeping dataset
        if(dataset_obj):
            dataset = dataset.rename_columns([dataset_col_dict[x] for x in dataset.column_names])
            dataset_obj.ds = dataset

        merged_dict = dataset_col_dict | dataset_all_col_dict
        normal_columns_merged = [merged_dict[x] for x in dataset_all_new.column_names]
        dataset_all_new = dataset_all_new.rename_columns(normal_columns_merged)

        # Save back the changes we made to dataset_all, explicitly to the non-filtered ds
        dataset_all_obj.ds = dataset_all_new

    def update_imputed_file(self) -> None:
        """Implement non-'prebanff' section of updateImputedFile.sas.

        Updates the `imputed_file` with the data found in `outdata`.
        Does not add any records from `outdata` without a matching index value in `imputed_file`,
        only updates matching records. `imputed_file` is updated inplace.
        """
        unit_id = self.input_params.unit_id
        if(not unit_id):
            msg = _("update_imputed_file requires a unit_id value to sort and update on.")
            log_lcl.exception(msg)
            raise ValueError(msg)

        unit_id_upper = unit_id.upper()
        imputed_file_obj = self.get_dataset("imputed_file", create_if_not_exist=True, ds_format="object")
        imputed_file = imputed_file_obj.ds
        outdata = self.get_dataset("outdata", create_if_not_exist=True)

        # See update_status() NOTE on using dict vs list for rename_columns
        imputed_file_col_dict = {x.upper():x for x in imputed_file.column_names}
        imputed_file = imputed_file.rename_columns(list(imputed_file_col_dict.keys()))
        outdata_col_dict = {x.upper():x for x in outdata.column_names}
        outdata = outdata.rename_columns(list(outdata_col_dict.keys()))

        imputed_file = imputed_file.sort_by(unit_id_upper)
        outdata = outdata.sort_by(unit_id_upper)

        # In updateImputedFile.sas the update statement in the final data step includes a
        # terminating if-statement which prevents any new rows from being copied over.

        # Get imputed_file records that don't have a matching key in outdata
        imputed_non_matching = imputed_file.join(outdata, keys=unit_id_upper, join_type="left anti")

        # Get outdata records with matching keys in imputed_file, mark the imputed_file columns
        # as we want to overwrite old data in imputed_file with new data from outdata. Use an
        # inner join because we do not want any new records from outdata, only update existing
        drop_suffix = "_to_drop"
        outdata = outdata.join(imputed_file, keys=unit_id_upper, join_type="inner", right_suffix=drop_suffix)
        # Drop any new columns from outdata that aren't originally found in imputed_file, also drop
        # the old imputed_file data columns we marked above
        outdata = outdata.drop_columns([x for x in outdata.column_names if
                                        (drop_suffix in x or x not in imputed_file.column_names)])

        # Concat our non-overlapping imputed data with the new values for matching records in outdata
        new_imputed = pa.concat_tables([imputed_non_matching, outdata], promote_options="permissive")

        # Our concat can make the order a little messed up so perform a final sort
        new_imputed = new_imputed.sort_by(unit_id_upper)

        # Save back the changes we made to imputed_file with original column names,
        # we can discard outdata changes
        imputed_file_obj.ds = new_imputed.rename_columns([imputed_file_col_dict[x] for x in new_imputed.column_names])

    def clean_status_file(self) -> None:
        """Implement cleanStatusAll.sas. Removes all extra columns from the statusAll file."""
        status_file_obj = self.get_dataset("status_file", ds_format="object")

        if(status_file_obj is None):
            return

        status_file = status_file_obj.ds

        keep_list_upper = [
            "JOBID",
            "SEQNO",
            "FIELDID",
            "STATUS",
            "VALUE",
        ]
        if(self.input_params.unit_id):
            keep_list_upper.append(self.input_params.unit_id.upper())

        # Get the keep list columns with correct capitalization in status_file
        keep_list_actual = [x for x in status_file.column_names if x.upper() in keep_list_upper]

        # filter the dataset
        status_file_obj.ds = status_file.select(keep_list_actual)

    def apply_process_controls(self) -> None:
        """Apply a set of process controls for a single controlid in `controls` according to their
        specifications and sets the filtered dataset(s) in processor_data.
        """
        # If the current job step has no controls, just return
        if(not self.current_job_step.controlid):
            return

        controls = self.metaobjects.get_process_controls(self.current_job_step.controlid)
        if(not controls):
            msg = _("Undefined control ID found: controlid ='{}', jobid='{}', seqno='{}'").format(self.current_job_step.controlid,
                                                                                                 self.current_job_step.jobid,
                                                                                                 self.current_job_step.seqno)
            log_lcl.exception(msg)
            raise MetadataConstraintError(msg)

        # Each control_set is a dict of all process controls for a single targetfile
        for control_set in controls.values():
            # arbitrary record we can use to get controlid and targetfile as every
            # record in control_set should have the same values for these
            arbitrary_control = next(iter(control_set.values()))[0]

            try:
                target_file_obj = self.get_dataset(arbitrary_control.targetfile, ds_format="object")
                if(target_file_obj is None):
                    msg = _("Process Control has an unrecognized target file value: targetfile='{}'",
                            ).format(arbitrary_control.targetfile)
                    if(Path(arbitrary_control.targetfile).suffix):
                        msg += _(". Note: targetfile must be an in-memory table, not one on disk.")
                    log_lcl.exception(msg)
                    raise ProcessControlError(msg)

                target_file = target_file_obj.ds

                if(table_empty(target_file)):
                    msg = _("Target file exists but is empty: targetfile='{}'. "
                            "Skipping process controls for file...").format(arbitrary_control.targetfile)
                    log_lcl.warning(msg)
                    # Continue to process the next targetfile
                    continue

                row_filter = None
                column_filter = []
                exclude_rejected = None
                edit_group_filter = None
                if(ProcessControlType.ROW_FILTER in control_set):
                    row_filter = "(" + ") AND (".join([x.value for x in control_set[ProcessControlType.ROW_FILTER]]) + ")"
                if(ProcessControlType.COLUMN_FILTER in control_set):
                    for x in control_set[ProcessControlType.COLUMN_FILTER]:
                        column_filter.extend([y.upper() for y in x.value])
                if(ProcessControlType.EXCLUDE_REJECTED in control_set):
                    exclude_control = control_set[ProcessControlType.EXCLUDE_REJECTED]
                    if(len(exclude_control) != 1):
                        msg = _("Too many EXCLUDEREJECTED controls for one targetfile.")
                        log_lcl.exception(msg)
                        raise ProcessControlError(msg)

                    exclude_control = exclude_control[0]
                    # currently allows True/False values for this control, so users don't have to
                    # remove the control from their file if they want to disable it temporarily
                    if(exclude_control.value):
                        # Get the correct capitalization for unit_id, just in case.
                        curr_unit_id = [x for x in target_file.column_names if x.upper() == self.input_params.unit_id.upper()][0]
                        # We want to use rejected here, not outreject_all
                        # The banff package produces the rejected files and SHOULD use the original
                        # capitalizaion of unit_id
                        exclude_rejected = f"({curr_unit_id} NOT IN (SELECT {curr_unit_id} FROM outreject))"  # noqa: S608
                    else:
                        exclude_rejected = False
                if(ProcessControlType.EDIT_GROUP_FILTER in control_set):
                    egf_control = control_set[ProcessControlType.EDIT_GROUP_FILTER]
                    if(len(egf_control) != 1):
                        msg = _("Too many EDIT_GROUP_FILTER controls for one targetfile.")
                        log_lcl.exception(msg)
                        raise ProcessControlError(msg)
                    egf_control = egf_control[0]

                    if(not self.current_job_step.editgroupid):
                        msg = _("An EDIT_GROUP_FILTER process control was specified but no editgroupid was "
                                "given in the metadata for the job step.")
                        log_lcl.exception(msg)
                        raise ProcessControlError(msg)

                    egi_cols = {x.upper():x for x in target_file.column_names if x.upper() in ("JOBID", "JOB_ID", "SEQNO", "STATUS")}

                    if(("JOBID" in egi_cols or "JOB_ID" in egi_cols)
                       and "SEQNO" in egi_cols and "STATUS" in egi_cols):
                        statuses = ", ".join([f"'{status}'" for status in egf_control.value])
                        edit_group_filter = (
                            f"""
                            (({egi_cols['JOBID']}, {egi_cols['SEQNO']}) IN (
                            SELECT (jobid, seqno) FROM banff.Jobs WHERE
                            editgroupid = '{self.current_job_step.editgroupid}'))
                            OR
                            (({egi_cols['JOBID']}, {egi_cols['SEQNO']}) IN (
                            SELECT (jobid, seqno) FROM banff.Jobs WHERE
                            process = 'outlier') AND status IN ({statuses}))
                            """ # noqa: S608
                        )
                    else:
                        msg = _("An EDIT_GROUP_FILTER process control was used but one or more required fields were "
                                "missing (STATUS, JOBID and SEQNO) on the instatus file. The control has been skipped.")
                        log_lcl.warning(msg)
                        edit_group_filter = None

                if(not row_filter and not column_filter and not edit_group_filter):
                    if(exclude_rejected is None):
                        # No valid controls were found in this control_set
                        msg = _("No supported controls found in process controls metadata.")
                        log_lcl.exception(msg)
                        raise MetadataConstraintError(msg)
                    if(not exclude_rejected):
                        # The only valid control is an exclude_rejected set to False, not an error,
                        # go to the next control_set/targetfile
                        continue

                # Convert the column labels in the filter to the same capitalization as the target_file
                column_filter_string = None
                if(column_filter):
                    column_filter_normal = [x for x in target_file.column_names if x.upper() in column_filter]
                    column_filter_string = ", ".join(column_filter_normal)

                # Currently column_filter KEEPS columns specified NOT DROPS
                # Currently row_filter only supports arguments that are all present in one of
                # indata, instatus or target_file
                query = "SELECT "

                if(column_filter_string is None):
                    query += "* "
                elif(column_filter_string):
                    query += f"{column_filter_string} "
                else:
                    # If none of the column_filter names are found in the targetfile columns
                    # column_filter_string will be an empty string
                    msg = _("A column filter was specified but none of the columns were found in targetfile.")
                    log_lcl.exception(msg)
                    raise ProcessControlError(msg)

                # Make sure we use the name given by the user (i.e. "instatus" not "status_file")
                # as the user-given name should be the names registered in duckdb.
                query += f"FROM '{arbitrary_control.targetfile}'"

                if(row_filter or exclude_rejected or edit_group_filter):
                    # Connect non-empty condition strings with 'AND'
                    query += f" WHERE {' AND '.join(filter(None, [row_filter, exclude_rejected, edit_group_filter]))}"

                msg = _("Computed filter: \n\t{}").format(query)
                log_lcl.debug(msg)

                result = self.dbconn.sql(query).arrow()

                if(result is None):
                    raise ProcessControlError
                if(result.shape[0] < 1):
                    # if the resulting table has no rows
                    msg = _("Process filter resulted in a dataset containing {} columns but 0 rows. Continuing...").format(result.shape[1])
                    log_lcl.warning(msg)

            except Exception as e:
                msg = _("There was an error while applying process controls with controlid {} "
                        "in job {} seqno {}.\nException: {}").format(self.current_job_step.controlid,
                                                                     self.current_job_step.jobid,
                                                                     self.current_job_step.seqno, e)
                log_lcl.exception(msg)
                raise e

            # Update the target_file with the new filtered version
            target_file_obj.ds_filtered = result

            msg = _("Filter succesfully applied.")
            log_lcl.debug(msg)

    def get_new_block_copy(self) -> "ProcessorData":
        """Return a new ProcessorData object with the necessary attributes copied in
        from this ProcessorData object to spawn a new processor block.

        :return: A new ProcessorData object with the required input parameters, metadata
            and datasets copied in.
        :rtype: ProcessorData
        """
        # Make a deep copy of input_params (to avoid any potential issues with a shallow copy)
        new_input_params = copy.deepcopy(self.input_params)

        # New block's job_id is stored in the specid field of the calling block
        new_input_params.job_id = self.current_job_step.specid

        # Create a new subfolder for the block
        new_block_folder = self.input_params.output_folder.joinpath(
            Path(f"{self.current_job_step.jobid}_{self.current_job_step.seqno}_{self.current_job_step.specid}"),
        )
        if(not new_block_folder.is_dir()):
            new_block_folder.mkdir(parents=True)
        new_input_params.input_folder = new_block_folder

        new_input_params.output_folder = new_block_folder / "out"
        if not new_input_params.output_folder.exists():
            new_input_params.output_folder.mkdir(parents=True)

        # input_params are copied with slight modifications made above
        copied_data = ProcessorData(input_params=new_input_params, dbconn=self.dbconn)

        # metadata may be copied in directly as the objects and tables should only
        # be used in a read-only manner
        copied_data.metaobjects = self.metaobjects

        # Make sure the child block reports duration as continuous from the parent
        copied_data.total_job_duration = self.total_job_duration
        # The parent block increments the count, then the child runs, then the parent reports.
        # Therefore, the curr_step_count must be decremented/incremented before/after the
        # child block executes
        copied_data.curr_step_count = self.curr_step_count - 1

        # Copy input files (aux/hist if they have already been read into memory)
        # rejected is a special case as it is directly used by name in a Process Control
        to_copy = ["indata", "instatus", "outreject", "outreject_all", "indata_aux", "indata_hist", "instatus_hist"]
        for name in to_copy:
            # If a filtered version of a table exists it should be set as an un-filtered
            # version for the new block.
            data = self.get_dataset(name, ds_format="object")
            if(data):
                copied_data.set_dataset(name, data.ds_filtered if data.ds_filtered else data.ds)

        return copied_data

    def update_with_block_result(self, block_data: "ProcessorData") -> None:
        """Update this ProcessorData object with the datasets found in `block_data`
        as it is upon completion of a JOB process which calls a Process Block.

        :param block_data: The ProcessorData object containing the results from a
            Process Block execution.
        :type block_data: ProcessorData
        """
        # Correct our step count now the block is complete. Remember the increment
        # to revert the decrement done when entering the child block
        self.curr_step_count = block_data.curr_step_count + 1

        # If update_status() modifies status_log it will not properly carry over all the records
        # we want, so we do it seperately like this.
        # First, make sure status_log is popped from the child so it is not revisited in the loop
        child_status_log = block_data.pop_dataset("status_log")
        if(child_status_log is not None):
            # make sure the parent's status_log exists before updating it,
            # we don't need the object here though, we're just using the flag
            self.get_dataset("status_log", create_if_not_exist=True)
            # Append child status_log to parent
            self.update_file_all(child_status_log, "status_log")
            # Now store a local reference to the updated status_log
            # we will overwrite the resulting status_log in the parent after
            # update_status() runs with this table instead
            updated_status_log = self.get_dataset("status_log", ds_format="object").ds
        else:
            # What if a user calls `job` as their first step, then the child block calls
            # UDPs which update instatus directly with no status_log involvement?
            # If the child did not produce a status_log we just let update_status()
            # do it's thing with the parent status_log, if it runs at all
            updated_status_log = None

        # At this point there should be no filtered datasets in block_data
        for name, block_ds in block_data.datasets.items():
            if("_aux" in name or "_hist" in name or name == "status_log"):
                continue
            if(name == "imputed_file"):
                # Since we directly copied in table references, if the 2 ProcessorData objects
                # reference the same table, we know no updates were made
                # We cannot replace self's imputed_file with the block's imputed_file as it's
                # possible the block started with a filtered file, so use outdata
                if(block_ds.ds is not self.indata):
                    self.outdata = block_ds.ds
            elif(name == "status_file"):
                # If instatus is unchanged, child status_log should also be empty
                if(block_ds.ds is not self.instatus):
                    # Only grab newly added records
                    status_file = block_ds.ds.filter(pa.compute.field("JOBID") == f"{block_data.current_job_step.jobid}")
                    # Remove the child block jobid, to be replaced by the current block's jobid on update
                    status_file = status_file.drop(["JOBID", "SEQNO"])
                    self.outstatus = status_file
                    # Perform the status_file update here, so we can ignore the status_log result
                    # in favour of our own updates
                    self.update_status()
                    # Make sure we only run update_status the one time by popping off outstatus
                    self.pop_dataset("outstatus")
            elif(name == "time_store"):
                time_store_curr_obj = self.get_dataset(name, ds_format="object")
                if(time_store_curr_obj):
                    time_store_curr_obj.ds = pa.concat_tables([time_store_curr_obj.ds, block_ds.ds])
                else:
                    self.set_dataset(name, block_ds.ds)
            else:
                # outreject and outreject_all will correctly fall here
                self.set_dataset(name, block_ds.ds)

        # Overwrite any changes made to status_log by any calls to update_status above
        if(updated_status_log is not None):
            self.set_dataset("status_log", updated_status_log)

    def save_proc_output(self, banff_call: BanffProcedure, all_tables: list[str]) -> None:
        """Save procedure output datasets.

        Append the non-default tables, the list of which is set on processor_data by the
        main processor loop, from `banff_call` to their respective cumulative datasets
        in the dataset collection based on the output type parameters set in the input_params.

        :param banff_call: A BanffProcedure call object that has completed execution and contains
            the output tables as attributes named as they are specified in `processor_to_proc`
        :type banff_call: :class:`banff.proc.BanffProcedure`
        :param all_tables: The list of all possible table names available on `banff_call`,
            required if `process_output_type` is ALL
        :type all_tables: list[str]
        :raises MetadataConstraintError: If a user's ProcessOutputs metadata contains an
            unrecognized output_name
        :raises AttributeError: If the `processor_to_proc` mapping contains a table name
            that is not found as an attribute on the `banff_call` object.
        """
        table_names = ([x for x in all_tables if x not in self.minimal_outputs]
                       if self.input_params.output_all
                       else self.custom_outputs)

        for name in table_names:
            try:
                table = getattr(banff_call, name)
            except AttributeError:
                msg = _("ProcessOutputs metadata entry found under process {} with "
                        "unrecognized output_name {}").format(self.current_job_step.process, name)
                log_lcl.exception(msg)
                raise MetadataConstraintError from AttributeError

            if(table is not None and not table_empty(table)):
                self.set_dataset(name, table)

    def save_outputs(self) -> None:
        """Save all current tables in `_datasets` to the output folder.

        Each dataset's name will be used as the filename, the extension is determined by the input parameters:
        The `save_format` input parameter is checked first, then the file type of indata.
        If neither parameter is provided or the filetype is unrecognized .parq is used by default.
        """
        # default save format is parquet file
        file_ext = [".parq"]

        # save_format input param overrides other options
        if(self.input_params.save_format):
            file_ext = [x.casefold() for x in self.input_params.save_format]
        # otherwise just use the same format as indata
        elif(self.input_params.indata_filename):
            file_ext = [self.input_params.indata_filename.suffix]

        for name, ds_obj in self._datasets.items():
            ds = ds_obj.ds
            if("_aux" in name or "_hist" in name):
                continue
            if(table_empty(ds)):
                log_lcl.warning(_("Output dataset {} was created but is empty.").format(name))
            else:
                if(not self.input_params.output_folder):
                    msg = _("No output folder set. Ouputs will not be saved.")
                    log_lcl.warning(msg)
                    return

                for ext in file_ext:
                    if(ext and not ext.isspace()):
                        if(ext in tc.file_ext_csv):
                            ds.to_pandas().to_csv(self.input_params.output_folder / f"{name}.csv", sep=",", index=False)
                        else:#if(ext in tc.file_ext_parquet):
                            # If a non-supported file extension is used (or a sas7bdat indata file is used)
                            # then we just default to .parq for now
                            pq.write_table(ds, self.input_params.output_folder / f"{name}.parq")

    def load_dataset_from_file(self, data_file: str | Path) -> pa.Table:
        """Load a Pyarrow Table from the data file indicated by the `data_file` parameter.

        If `data_file` contains a full filepath, the file will be retrieved using
        this filepath. If `data_file` only contains a filename, the `processor_input.input_folder`
        is used as the containing directory to fetch from.

        :param data_file: The full filepath or filename of the data file to load
        :type data_file: str | Path
        :raises ProcessorInputParameterError: If an empty filename is given or just
            a filename but no `input_folder` had been previously specified in the
            processor_input member object.
        :raises Exception: If some other issue causes the file to not be read
        :return: The `data_file` as loaded into a PyArrow Table
        :rtype: pa.Table
        """
        dataset = None

        # Currently supported data formats from io_util.type_converters include:
        #   Parquet --- ".parquet", ".parq"
        #   Pickle --- ".pickle", ".pkl", ".pcl"
        #   SAS --- ".sas7bdat"
        #   CSV --- ".csv"
        #   Feather --- ".feather"

        try:
            # First determine if the filename is a full filepath or just the filename
            file_path = Path(data_file)
            if(file_path.is_absolute()):
                # data_file is a full filepath, so pass the whole thing
                dataset = io_util.load_input_dataset(str(file_path), log_lcl)
                if isinstance(dataset, pd.DataFrame):
                    dataset = io_util.pandas_to_arrow(dataset)
            else:
                # data_file is just a filename, so use the input folder as the filepath
                if(not file_path.name or not self.input_params.input_folder):
                    msg = _("Input folder was not provided or data_file string was empty when "
                            "attempting to load datafile without full filepath.")
                    log_lcl.exception(msg)
                    raise ProcessorInputParameterError(msg)

                file_path_complete = (self.input_params.input_folder / file_path).resolve()
                dataset = io_util.load_input_dataset(str(file_path_complete), log_lcl)
                if isinstance(dataset, pd.DataFrame):
                    dataset = io_util.pandas_to_arrow(dataset)
        except Exception as e:
            msg = _("Error while reading input data file {}").format(data_file)
            log_lcl.exception(msg)
            raise e from None

        # This shouldn't happen really unless filetype not supported and not previously caught or filename is empty.
        if dataset is None:
            msg = _("Filetype not supported or filename empty.")
            log_lcl.exception(msg)
            raise ValueError(msg)

        return dataset

def ds_to_format(ds: pa.Table | pd.DataFrame, ret_format: str) -> pa.Table | pd.DataFrame | None:
    """Convert `ds` to `format`.

    `ret_format` currently supports these values:
        For Pandas DataFrame: ["pandas", "dataframe", "pandas dataframe"]
        For PyArrow Table: ["pyarrow", "table", "pyarrow table"]

    :param ds: The dataset to convert
    :type ds: pa.Table | pd.DataFrame | Dataset
    :param ret_format: The name of the format to convert to.
    :type ret_format: str
    :raises Exception: If an error occurs during the conversion of the file.
    :raises ValueError: If `ret_format` is not a recognized format string.
    :return: A new dataset containing the data of `ds` converted into `ret_format`, None if `ds` is None
    :rtype: pa.Table | pd.DataFrame | None
    """
    if(ds is None):
        return ds

    if(not(isinstance(ds, pd.DataFrame | pa.Table))):
        msg = _("Dataset provided in parameter 'ds' is of an unsupported type. "
                "'ds' must be a pandas Dataframe or pyarrow Table.")
        log_lcl.exception(msg)
        raise TypeError(msg)

    ret_format = ret_format.casefold()
    if(ret_format in tc.obj_id_pandas):
        if(isinstance(ds, pd.DataFrame)):
            ret_ds = ds
        else:
            try:
                # pyarrow option `split_blocks=True` is recommended for minimizing memory usage,
                # see https://arrow.apache.org/docs/python/pandas.html#reducing-memory-use-in-table-to-pandas
                ret_ds = ds.to_pandas(split_blocks=True)
                # Can't use type converter PAT_to_DF here due to self_destruct=True option
            except Exception as e:
                msg = _("Unhandled exception occurred while converting PyArrow Table to Pandas DataFrame")
                log_lcl.exception(msg)
                raise Exception(msg) from e
    elif(ret_format in tc.obj_id_pyarrow):
        ret_ds = ds if isinstance(ds, pa.Table) else tc.DF_to_arrow_table(ds)
    else:
        msg = _("Unrecognized format parameter '{}'. Must be either of 'pyarrow' or 'pandas'").format(ret_format)
        log_lcl.exception(msg)
        raise ValueError(msg)

    return ret_ds
