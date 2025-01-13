"""Model for a Banff Processor working dataset."""

from typing import Any

import duckdb
import pyarrow as pa

import banffprocessor.processor_logger as plg
from banffprocessor.nls import _

log_lcl = plg.get_processor_child_logger("dataset")

class Dataset:
    """Model for a Banff Processor working dataset."""

    name: str
    _ds_cumulative: pa.Table
    _ds_filtered: pa.Table
    _ds_curr_output: pa.Table

    _dbconn: duckdb.DuckDBPyConnection
    _is_private_connection: bool

    @property
    def dbconn(self) -> duckdb.DuckDBPyConnection | None:
        """Return a connection to the database being used."""
        return self._dbconn

    def __init__(self, name: str, ds: pa.Table, dbconn: duckdb.DuckDBPyConnection | None = None) -> None:
        """Create a Banff Processor Dataset.

        :param name: The name of the dataset that the dataset will be identified by.
        :type name: str
        :param ds: The arrow table with the underlying data that this object will store.
        :type ds: pa.Table
        :param dbconn: The DuckDB connection to register cumulative datasets to, defaults to None
        :type dbconn: duckdb.DuckDBPyConnection | None, optional
        """
        self.name = name.casefold()
        self._ds_cumulative = ds

        self._ds_filtered = None
        self._ds_curr_output = None

        self._dbconn = dbconn
        if self._dbconn is None:
            self._dbconn = duckdb.connect(database=":memory:")
            self._is_private_connection = True
        else:
            self._is_private_connection = False

        self.register_table()

    def __del__(self) -> None:
        """Ensure memory is released and the database connection is closed."""
        self._ds_cumulative = None
        self._ds_curr_output = None
        self._ds_filtered = None
        if self._is_private_connection:
            self._dbconn.close()

    @property
    def ds(self) -> pa.Table:
        """Return the dataset as an Arrow Table."""
        return self._ds_cumulative

    @ds.setter
    def ds(self, value: pa.Table) -> None:
        """Set the dataset using the provided Arrow Table."""
        self._ds_cumulative = value
        self.register_table()

    @property
    def ds_filtered(self) -> pa.Table:
        """Return the filtered version of the dataset as an Arrow table."""
        return self._ds_filtered

    @ds_filtered.setter
    def ds_filtered(self, value: pa.Table) -> None:
        """Set the filtered version of the dataset using the provided Arrow table."""
        #NOTE: we don't re-register the filtered dataset to duckdb over the unfiltered
        # version. This is because if multiple process controls exist for a single step,
        # one control may filter instatus and then the 2nd control to be applied will
        # reference instatus to filter another file. We want the 2nd control to be able
        # to reference the original file, thus we don't replace the duckdb registration
        # of the original table with the filtered one.
        self._ds_filtered = value

    @property
    def ds_curr_output(self) -> pa.Table:
        """Return the dataset output by the current proc as an Arrow table."""
        return self._ds_curr_output

    @ds_curr_output.setter
    def ds_curr_output(self, value: pa.Table) -> None:
        """Set the version of this dataset output by the current proc using the provided Arrow table."""
        self._ds_curr_output = value

    def register_table(self) -> None:
        """Register `ds` in the in-memory duckdb instance under `name` or the alias of `name`, if one exists."""
        if(not table_empty(self.ds)):
            # Register the Dataset with duckdb so the latest version will always
            # be accesible for process controls
            alias_name = get_dataset_name_alias(self.name)
            self.dbconn.register(alias_name if alias_name is not None else self.name, self.ds)
        else:
            msg = _("Dataset {} was empty and so was not able to be registered to Duckdb.").format(self.name)
            log_lcl.warning(msg)

    def unregister_table(self) -> None:
        """Un-registers the dataset in the in-memory duckdb instance under `name` or the alias of `name`, if one exists."""
        # Unregister the tables when we remove them
        alias_name = get_dataset_name_alias(self.name)
        self.dbconn.unregister(alias_name if alias_name is not None else self.name)

# The real name is the only name actually stored in the datasets collection.
# Aliases are solely used for users identifying datasets for process controls or UDPs, thus
# aliases are used to register tables in duckdb
_alias_to_real = {
    "indata": "imputed_file",
    "instatus": "status_file",
    "cumulative_status_all": "status_log",
}
_real_to_alias = {
    "imputed_file": "indata",
    "status_file": "instatus",
    "status_log": "cumulative_status_all",
}

def get_dataset_name_alias(name: str) -> str | None:
    """Get the alias name of the given dataset name.

    Casefold() `name` and get the aliased name of the dataset `name`, if `name` exists with an alias.
    If no alias exists, None is returned.

    :param name: The name of the dataset to get the aliased name of
    :type name: str
    :return: `name` casefolded, or the proper dataset name if `name` is an alias
    :rtype: str
    """
    name_lower = name.casefold()
    if(name_lower in _real_to_alias):
        return _real_to_alias[name_lower]
    return None

def get_dataset_real_name(name: str) -> str:
    """Get the real name of the given dataset name.

    Casefold() `name` and get the actual name of the dataset `name`, if `name`
    exists as an alias. If no alias exists just returns the casefolded `name`.

    :param name: The name of the dataset to get the proper name of
    :type name: str
    :return: `name` casefolded, or the proper dataset name if `name` is an alias
    :rtype: str
    """
    name_lower = name.casefold()
    if(name_lower in _alias_to_real):
        return _alias_to_real[name_lower]
    return name_lower

#####
# Helper methods for working with pyarrow. In case I find a better way of doing these
# operations later, it's easier to just change them one time here
#####
def table_empty(table: pa.Table) -> bool:
    """Determine if `table` is empty (has no rows nor columns).

    :param table: The table to check
    :type table: pa.Table
    :return: True if the table's shape is (0,0), false otherwise
    :rtype: bool
    """
    return (table.shape == (0,0))

def copy_table(to_copy: pa.Table) -> pa.Table:
    """Return a copy of a PyArrow Table.

    :param to_copy: The table to make a copy of
    :type to_copy: pa.Table
    :return: A new table containing the data and metadata of `to_copy`
    :rtype: pa.Table
    """
    # This will create a copy of the table information but not a copy of the data.
    # However, a PyArrow Table's arrays are immutable and therefore any changes to the
    # data for one of the tables would not affect the other.
    return to_copy.select(to_copy.column_names)

def add_single_value_column(table: pa.Table, column_name: str, value: Any, dtype: pa.DataType | None = None) -> pa.Table:
    """Add a new column to `table` where every row of the column contains the same value and the column is the same length as `table`.

    :param table: The table to append the new column to
    :type table: pa.Table
    :param column_name: The name for the new column
    :type column_name: str
    :param value: The value to use for each row of the new column
    :type value: Any
    :param dtype: The PyArrow DataType to use for the columnc, defaults to None
    :type dtype: pa.DataType, optional
    :return: `table` with the new column appended to it
    :rtype: pa.Table
    """
    # Equivalent to: my_df[column_name] = value
    if(dtype):
        return table.append_column(column_name, pa.array([value]*len(table), dtype))
    return table.append_column(column_name, pa.array([value]*len(table)))
