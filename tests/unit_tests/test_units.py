import pytest
from pathlib import Path
import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
from banffprocessor.metadata import metaobjects
from banffprocessor.metadata.models.donorspecs import Donorspecs
from banffprocessor.metadata.models.jobs import Jobs
from banffprocessor.metadata.models.editgroups import Editgroups
from banffprocessor.metadata.models.processcontrols import ProcessControls
from banffprocessor.exceptions import MetadataConstraintError
from banffprocessor.util.dataset import Dataset
from banffprocessor.util.dataset import (table_empty, copy_table, add_single_value_column, 
                                         get_dataset_name_alias, get_dataset_real_name)

#region METAOBJECTS

@pytest.mark.unit()
def test_metaobjects_add_and_get(empty_metaobjects, input_jobs_list):
    empty_metaobjects.add_objects_of_single_type(input_jobs_list)
    assert empty_metaobjects.get_objects_of_type(metaobjects.Jobs) == input_jobs_list

@pytest.mark.unit()
def test_metaobjects_add_dif_objects(empty_metaobjects, input_jobs_list, input_algorithms_list):
    with pytest.raises(TypeError):
        empty_metaobjects.add_objects_of_single_type(input_jobs_list + input_algorithms_list)

@pytest.mark.unit()
def test_metaobjects_add_empty(empty_metaobjects):
    with pytest.raises(ValueError):
        empty_metaobjects.add_objects_of_single_type([])

@pytest.mark.unit()
def test_metaobjects_get_not_found(empty_metaobjects):
    assert empty_metaobjects.get_objects_of_type(metaobjects.Jobs) == []

@pytest.mark.unit()
def test_metaobjects_get_job_steps(full_metaobjects):
    jobs = full_metaobjects.get_job_steps("j1")

    assert len(jobs) == 3
    assert all(x.jobid == "j1" for x in jobs)
    assert jobs[0].seqno < jobs[1].seqno
    assert jobs[1].seqno < jobs[2].seqno

@pytest.mark.unit()
def test_jobs_invalid_acceptnegative():
    Jobs.initialize()
    with pytest.raises(Exception) as e_info:
        Jobs("j1", 1, "TEST","SPEC1", None, None, '?', 'ControlID')
    Jobs.cleanup()

def test_editgroups_undefined_edit(empty_metaobjects):
    Editgroups("grp1", "edit_unknown", dbconn=empty_metaobjects.dbconn)
    with pytest.raises(Exception) as e_info:
        Editgroups.check_constraints(dbconn=empty_metaobjects.dbconn)
        print(e_info)

@pytest.mark.unit()
def test_jobs_duplicate():
    Jobs.initialize()
    with pytest.raises(Exception) as e_info:
        Jobs("j1", 1, "TEST","SPEC1", None, None, 'Y', 'ControlID')
        Jobs("j1", 1, "TEST","SPEC2", None, None, 'N', 'ControlID')
    Jobs.cleanup()
 
@pytest.mark.unit()
def test_metaobjects_get_job_steps_not_found(full_metaobjects):
    jobs = full_metaobjects.get_job_steps("abcd")

    assert jobs == []

@pytest.mark.unit()
def test_metaobjects_get_job_steps_empty(empty_metaobjects):
    jobs = empty_metaobjects.get_job_steps("j1")

    assert jobs == []

@pytest.mark.unit()
def test_metaobjects_get_specs_objs(full_metaobjects):
    specid = "Donorspecs2"
    spec = full_metaobjects.get_specs_obj(Donorspecs, specid)

    assert spec is not None
    assert spec.specid == specid
    assert spec.n == 2

@pytest.mark.unit()
def test_metaobjects_get_specs_objs_not_found(full_metaobjects):
    specid = "Donorspecs6"
    spec = full_metaobjects.get_specs_obj(Donorspecs, specid)

    assert spec is None

@pytest.mark.unit()
def test_metaobjects_get_specs_objs_empty(empty_metaobjects):
    specid = "Donorspecs2"
    spec = empty_metaobjects.get_specs_obj(Donorspecs, specid)

    assert spec is None

@pytest.mark.unit()
def test_metaobjects_get_varlist(full_metaobjects):
    varlist = full_metaobjects.get_varlist_fieldids("v2")

    assert len(varlist) == 2
    assert varlist[0] == "v2-field2"
    assert varlist[1] == "v2-field"

@pytest.mark.unit()
def test_metaobjects_get_varlist_not_found(full_metaobjects):
    varlist = full_metaobjects.get_varlist_fieldids("v7")

    assert varlist == []

@pytest.mark.unit()
def test_metaobjects_get_varlist_empty(empty_metaobjects):
    varlist = empty_metaobjects.get_varlist_fieldids("v2")

    assert varlist == []

@pytest.mark.unit()
def test_metaobjects_get_edits_string(full_metaobjects):
    edits = full_metaobjects.get_edits_string("v1")

    assert edits == "PASS: x > y; FAIL: a < b; g != h;"

@pytest.mark.unit()
def test_metaobjects_get_edits_string_not_found(full_metaobjects):
    edits = full_metaobjects.get_edits_string("v5")

    assert edits == ""

@pytest.mark.unit()
def test_metaobjects_get_edits_string_empty(empty_metaobjects):
    edits = empty_metaobjects.get_edits_string("v1")

    assert edits == ""

@pytest.mark.unit()
def test_metaobjects_get_weights_string(full_metaobjects):
    weights = full_metaobjects.get_weights_string("w1")

    # weights should be read in as a float, therefore decimals needed
    assert weights == "volume=9.0; area=7.0; length=5.0;"

@pytest.mark.unit()
def test_metaobjects_get_weights_string_not_found(full_metaobjects):
    weights = full_metaobjects.get_weights_string("w9")

    assert weights == ""

@pytest.mark.unit()
def test_metaobjects_get_weights_string_empty(empty_metaobjects):
    weights = empty_metaobjects.get_weights_string("w1")

    assert weights == ""

@pytest.mark.unit()
def test_metaobjects_get_expression(full_metaobjects, input_expressions_list):
    expression = full_metaobjects.get_expression("e3")

    assert expression == "z"

@pytest.mark.unit()
def test_metaobjects_get_expression_notfound(empty_metaobjects):
    with pytest.raises(ValueError, match="The following value was not found: expressions.expressionid = 'e3'.") as e_info:
        expressions = empty_metaobjects.get_expression("e3")

@pytest.mark.unit()
def test_metaobjects_get_estimators(full_metaobjects):
    estimators = full_metaobjects.get_estimators("est1")

    assert len(estimators) == 2
    assert estimators[0].seqno < estimators[1].seqno

@pytest.mark.unit()
def test_metaobjects_get_estimators_not_found(full_metaobjects):
    estimators = full_metaobjects.get_estimators("est9")

    assert estimators == []

@pytest.mark.unit()
def test_metaobjects_get_estimators_empty(empty_metaobjects):
    estimators = empty_metaobjects.get_estimators("est1")

    assert estimators == []

@pytest.mark.unit()
def test_metaobjects_get_user_vars_dict(full_metaobjects):
    uservars = full_metaobjects.get_user_vars_dict("test1","test")

    assert len(uservars) == 2
    assert uservars["var1"] == "1"
    assert uservars["var2"] == "2"

@pytest.mark.unit()
def test_metaobjects_get_user_vars_dict_not_found(full_metaobjects):
    uservars = full_metaobjects.get_user_vars_dict("test5", "test")

    assert uservars == {}

@pytest.mark.unit()
def test_metaobjects_get_user_vars_dict_empty(empty_metaobjects):
    uservars = empty_metaobjects.get_user_vars_dict("test1", "myplugin")

    assert uservars == {}

@pytest.mark.unit()
def test_metaobjects_get_algorithm(full_metaobjects):
    algo = full_metaobjects.get_algorithm("CUST_PREAUX")

    assert algo.algorithmname == "CUST_PREAUX"

@pytest.mark.unit()
def test_metaobjects_get_algorithm_not_found(full_metaobjects):
    algo = full_metaobjects.get_algorithm("CUST_HISTREG")

    assert algo == None

@pytest.mark.unit()
def test_metaobjects_get_algorithm_not_found(empty_metaobjects):
    algo = empty_metaobjects.get_algorithm("CUST_HISTREG")

    assert algo == None

@pytest.mark.unit()
def test_metaobjects_get_algorithm_istype(full_metaobjects):
    algo = full_metaobjects.get_algorithm("CUST_PREAUX")

    assert algo.algorithmname == "CUST_PREAUX"
    assert algo.type == "LR"

@pytest.mark.unit()
def test_metaobjects_get_algorithm_not_found(full_metaobjects):
    with pytest.raises(ValueError, match="The following value was not found: algorithms.algorithm_name = 'DOES_NOT_EXIST'.") as e_info:
        algo = full_metaobjects.get_algorithm("DOES_NOT_EXIST")

@pytest.mark.unit()
def test_metaobjects_get_process_controls(full_metaobjects):
    specid = "TEST_1"
    controls = full_metaobjects.get_process_controls(specid)
    
    indata_controls = controls["indata"][metaobjects.ProcessControlType.ROW_FILTER]
    instatus_controls = controls["instatus"][metaobjects.ProcessControlType.COLUMN_FILTER]

    assert len(indata_controls) == 1 and len(instatus_controls) == 1 
    
    assert indata_controls[0].controlid == specid
    assert indata_controls[0].parameter == metaobjects.ProcessControlType.ROW_FILTER
    assert indata_controls[0].value.casefold() == "a > b"

    assert instatus_controls[0].controlid == specid
    assert instatus_controls[0].parameter == metaobjects.ProcessControlType.COLUMN_FILTER
    assert [x.casefold() for x in instatus_controls[0].value] == ["a", "c"]

@pytest.mark.unit()
def test_metaobjects_get_process_controls_not_found(full_metaobjects):
    controls = full_metaobjects.get_process_controls("TEST_2")

    assert controls == {}

@pytest.mark.unit()
def test_metaobjects_get_process_controls_empty(empty_metaobjects):
    controls = empty_metaobjects.get_process_controls("TEST_1")

    assert controls == {}
    
@pytest.mark.unit()
def test_metaobjects_validate_job_sequence(input_jobs_list):
    assert metaobjects.MetaObjects.validate_job_sequence(input_jobs_list, "j1")
    
@pytest.mark.unit()
def test_metaobjects_validate_job_sequence_exception(jobs_list_with_cycle):
    with pytest.raises(Exception, match='contains a cycle caused by job_id') as e_info:
        result = metaobjects.MetaObjects.validate_job_sequence(jobs_list_with_cycle, "j1")

@pytest.mark.unit()
def test_metaobjects_errors_in_processcontrols():
    dbconn = duckdb.connect(database=":memory:")
    ProcessControls.initialize(dbconn)
    
    # No semi-colon allowed in value
    with pytest.raises(MetadataConstraintError) as e_info:
        x = ProcessControls("abcd", "row_filter", "x; SELECT * FROM ProcessControls", "indata", dbconn=dbconn)

    # Missing value for non-edit_group_filter control
    with pytest.raises(MetadataConstraintError) as e_info:
        x = ProcessControls("abcd", "row_filter", targetfile="indata", dbconn=dbconn)

    # Including value for edit_group_filter control
    with pytest.raises(MetadataConstraintError) as e_info:
        x = ProcessControls("abcd", "edit_group_filter", value="test", targetfile="indata", dbconn=dbconn)

    # Non-existent control name
    with pytest.raises(MetadataConstraintError) as e_info:
        x = ProcessControls("abcd", "non_existent_control", "test", "indata", dbconn=dbconn)
    
    # Success
    x = ProcessControls("abcd", "column_filter", "col1, col2, col3", "indata", dbconn=dbconn)
    assert x.value == ["col1", "col2", "col3"]
    dbconn.close()
    
#endregion

#region PROCESSOR_DATA

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_table_empty():
    my_table = pa.table([])
    
    assert table_empty(my_table) is True

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_full_table_empty(pyarrow_test_data):
    
    assert table_empty(pyarrow_test_data) is False

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_no_data_table_empty():
    my_table = pa.table({"test": [], "other": []})
    
    assert table_empty(my_table) is False

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_copy_table(pyarrow_test_data):
    my_copied_table = copy_table(pyarrow_test_data)
    
    assert pyarrow_test_data is not my_copied_table
    assert pyarrow_test_data.shape == my_copied_table.shape
    
@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_add_single_val_col(pyarrow_test_data):
    new_col_name = "new_col"
    new_col_dtype = pa.int64()
    new_table = add_single_value_column(pyarrow_test_data, new_col_name, 1234, new_col_dtype)
    
    assert new_col_name in new_table.column_names
    assert new_table.shape == (3,3)
    assert new_table[new_col_name].type == new_col_dtype
    assert pc.all(pc.equal(new_table[new_col_name], 1234)).as_py()

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_get_alias_indata():
    assert get_dataset_name_alias("imputed_file") == "indata"
    
@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_get_alias_instatus():
    assert get_dataset_name_alias("status_file") == "instatus"

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_set_dataset(session_processor_data):
    ds = pa.table([])
    session_processor_data.set_dataset("test_status", ds)
    ret_ds = session_processor_data._datasets["test_status"]
    
    assert isinstance(ret_ds, Dataset)
    assert ret_ds.ds is ds

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_set_dataset_overwrite(session_processor_data, input_test_status):
    ds_name = "test_status"
    ds = session_processor_data.get_dataset(ds_name, ds_format="object")
    ds.ds = input_test_status
    
    # Not necessary to call set_dataset again in practice, just for testing
    session_processor_data.set_dataset(ds_name, ds)
    
    ret_ds = session_processor_data.get_dataset(ds_name, ds_format="object")
    assert ret_ds.ds is input_test_status

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_set_dataset_curr_output(session_processor_data):
    new_ds = pa.table({'nums': [1,2,3,4], 
                      'letters': ["a", "b", "c", "d"], 
                      'overlap': [None, 2, 3, 4]})
    session_processor_data.set_dataset("test_status", new_ds)
    
    assert session_processor_data._datasets["test_status"].ds_curr_output is new_ds

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_set_dataset_from_file(session_processor_data):
    file_folder = Path(__file__).parent.joinpath("test_files")
    to_load_path = str(file_folder.joinpath("instatus.parq"))
    session_processor_data.set_dataset_from_file("filedata", to_load_path)
    
    result = session_processor_data._datasets["filedata"]
    # By default get should create as a pyarrow Table
    assert isinstance(result, Dataset)
    assert result.ds_filtered is None
    assert result.ds.shape == (4,8)

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_get_dataset(session_processor_data, input_test_status):
    ds = session_processor_data.get_dataset("test_status")
    
    assert ds is input_test_status
    
@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_get_dataset_case_insensitive(session_processor_data, input_test_status):
    ds = session_processor_data.get_dataset("tEsT_sTaTuS")
    
    assert ds is input_test_status

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_get_dataset_not_found(session_processor_data):
    ds = session_processor_data.get_dataset("my_table")
    
    assert ds is None

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_get_dataset_create_new(session_processor_data):
    ds = session_processor_data.get_dataset("my_new_table", create_if_not_exist=True)
    
    assert ds is not None
    assert isinstance(ds, pa.Table)
    assert table_empty(ds)
    assert "my_new_table" in session_processor_data._datasets

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_get_dataset_pandas(session_processor_data):
    ds = session_processor_data.get_dataset("test_status", ds_format="pandas")
    
    assert ds is not None
    # By default get should return a pyarrow Table
    assert isinstance(ds, pd.DataFrame)
    assert not ds.empty

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_set_dataset_filtered(session_processor_data, pyarrow_test_data):
    ds_name = "test_status"
    test_ds = session_processor_data.get_dataset(ds_name, create_if_not_exist=True, ds_format="object")
    test_ds.ds_filtered = pyarrow_test_data
    
    assert session_processor_data.get_dataset(ds_name, ds_format="object").ds_filtered is pyarrow_test_data

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_set_registered(session_processor_data, pyarrow_test_data):
    table_name = "my_new_ds"
    query = f"SELECT * FROM {table_name}"
    
    # Ensure the table doesn't exist yet
    with pytest.raises(duckdb.CatalogException) as e_info:
        session_processor_data.dbconn.sql(query)

    # Check it was registered to duckdb after it was set
    session_processor_data.set_dataset(table_name, pyarrow_test_data)
    test_res = session_processor_data.dbconn.sql(query).arrow()
    assert not table_empty(test_res)

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_get_dataset_filtered(session_processor_data, pyarrow_test_data):
    ds = session_processor_data.get_dataset("test_status")
    
    assert ds is pyarrow_test_data
    
@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_clear_filtered(session_processor_data, input_test_status):
    session_processor_data.clear_filtered_data()
    ds = session_processor_data.get_dataset("test_status")
    
    # After clearing filtered data, the original dataset should be returned instead
    assert ds is input_test_status

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_getset_using_alias(session_processor_data, pyarrow_test_data):
    session_processor_data.set_dataset("indata", pyarrow_test_data)
    
    ds_std = session_processor_data.get_dataset("imputed_file")
    ds_alias = session_processor_data.get_dataset("indata")
    assert ds_std is ds_alias is pyarrow_test_data

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_set_with_pandas(session_processor_data):
    ds = pd.DataFrame(data={'col1': [1,2,3,4], 'col2': [5,6,7,8]})
    session_processor_data.set_dataset("my_df", ds)
    
    ret_ds = session_processor_data.get_dataset("my_df")
    assert isinstance(ret_ds, pa.Table)
    assert not table_empty(ret_ds)

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_set_unsupported_type(session_processor_data):
    with pytest.raises(TypeError) as e_info:
        session_processor_data.set_dataset("not_supported", [1,2,3,4,5])

@pytest.mark.unit()
@pytest.mark.processor_data()
def test_processor_data_pop(session_processor_data, input_test_data):
    my_table = input_test_data
    name = "to_pop"
    session_processor_data.set_dataset(name, my_table)
    popped_rec = session_processor_data.pop_dataset(name)
    
    assert popped_rec.ds.shape == my_table.shape
    assert session_processor_data.get_dataset(name) is None
    
    # Clear the object reference so the DB reference is cleared
    popped_rec = None
    
    query = f"SELECT * FROM {name}"
    # Ensure the table was de-registered
    with pytest.raises(duckdb.CatalogException) as e_info:
        session_processor_data.dbconn.sql(query)

# Update Status
# Update File All
# Update Imputed
# Clean Status All
# apply_process_controls

#endregion