from pathlib import Path
import shutil
import banffprocessor.exceptions
import requests

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import banffprocessor
from banff import testing
from banff.testing import assert_log_contains
from banffprocessor.processor import Processor
from banffprocessor.processor_input import ProcessorInput
import banffprocessor.util.metadata_excel_to_xml as e2x

#NOTE: pytest automatically captures warnings when running all tests
# in a single session (i.e. "pytest") while running selectively will preserve
# existing warning settings (i.e. "pytest -k 'test_estimator'").
# This means warnings are only logged to file if selectively running tests
# or running the test code directly, outside of pytest.

def folder_setup(folder_name: str | Path, input_filename: str | None = None, 
                 output_folder_name: str | None = None) -> tuple[Path, Path]:
    """Takes a test's `folder_name` as input and returns the full paths
    to the expected output folder (after cleaning it of any existing files) 
    and the input JSON file with the name `input_filename`, or processor_input.json
    if the `input_filename` is not provided. If an `output_folder_name` is given it will
    be used instead of the default folder name of `out`.
    """
    integration_tests_folder = Path(__file__).parent
    individual_test_folder = integration_tests_folder / folder_name

    out_folder = individual_test_folder / (output_folder_name if output_folder_name else "out")
    if(out_folder.is_dir()):
        # Delete an existing out folder and all contents
        shutil.rmtree(out_folder)       
    
    if(output_folder_name):
        # If a non-standard output folder is used, we need to create it first, not the processor
        out_folder.mkdir(parents=True)
    
    return out_folder, individual_test_folder.joinpath(input_filename if input_filename else "processor_input.json")

def execute_processor(input_data: Path | str | ProcessorInput, 
                      indata: pa.Table | pd.DataFrame | None = None) -> None:
    if(isinstance(input_data, ProcessorInput)):
        bp = Processor(input_data, indata=indata)
    else:
        bp = Processor.from_file(input_data, indata=indata)
    bp.execute()
    bp.save_outputs()
    # Useful or not?
    bp = None

@pytest.mark.integration()
def test_outlier_c03():
    out_folder, input_filepath = folder_setup("outlier_test_c03")
    validate_folder = input_filepath.parent.joinpath("expected")
    execute_processor(input_filepath)

    outlier_status_all = pd.read_parquet(out_folder.joinpath("outlier_status.parq"))
    outlier_status_all_validate = pd.read_parquet(validate_folder.joinpath("outlier_status_validate.parq"))
    
    testing.assert_dataset_equal(outlier_status_all, outlier_status_all_validate, "OUTLIER_STATUS")

@pytest.mark.integration()
def test_outlier_error():
    out_folder, input_filepath = folder_setup("outlier_test_error")
    with pytest.raises(banffprocessor.exceptions.ProcedureReturnCodeError):
        execute_processor(input_filepath)
    
    with open(out_folder / "banffprocessor.log") as log_file:
        content = log_file.read()     
        msg = "ProcedureCError: Procedure 'Outlier' encountered an error and terminated early: variable in varlist not found (return code 5)"
        assert_log_contains(msg, content, clean_whitespace=True)

@pytest.mark.integration()
def test_donorimp_it04(donorimp_expected_outdata_it04):
    out_folder, input_filepath = folder_setup("donorimp_test_it04")
    validate_folder = input_filepath.parent.joinpath("expected")
    execute_processor(input_filepath)
    
    # Input parameters use process_output_type=ALL, so verify ALL expected files are correct

    outdata = pd.read_parquet(out_folder.joinpath("imputed_file.parq"))
    testing.assert_dataset_equal(outdata, donorimp_expected_outdata_it04, "IMPUTED_FILE")
    
    outstatus = pd.read_parquet(out_folder.joinpath("status_file.parq"))
    outstatus_validate = pd.read_parquet(validate_folder.joinpath("status_file_validate.parq"))
    testing.assert_dataset_equal(outstatus, outstatus_validate, "STATUS_FILE")
    
    status_log = pd.read_parquet(out_folder.joinpath("status_log.parq"))
    status_log_validate = pd.read_parquet(validate_folder.joinpath("status_log_validate.parq"))
    testing.assert_dataset_equal(status_log, status_log_validate, "STATUS_LOG")
    
    # time_store is different every run, just check it exists
    assert Path.is_file(out_folder / "time_store.parq")
    
    outdonormap = pd.read_parquet(out_folder.joinpath("outdonormap.parq"))
    outdonormap_validate = pd.read_parquet(validate_folder.joinpath("outdonormap_validate.parq"))
    testing.assert_dataset_equal(outdonormap, outdonormap_validate, "OUTDONORMAP")
    
    outmatching_fields = pd.read_parquet(out_folder.joinpath("outmatching_fields.parq"))
    outmatching_fields_validate = pd.read_parquet(validate_folder.joinpath("outmatching_fields_validate.parq"))
    testing.assert_dataset_equal(outmatching_fields, outmatching_fields_validate, "OUTMATCHING_FIELDS")

@pytest.mark.integration()
def test_prorate_o04(prorate_expected_outdata_o04):
    out_folder, input_filepath = folder_setup("prorate_test_o04")
    validate_folder = input_filepath.parent.joinpath("expected")
    execute_processor(input_filepath)

    outdata = pd.read_parquet(out_folder.joinpath("imputed_file.parq"))
    testing.assert_dataset_equal(outdata, prorate_expected_outdata_o04, "IMPUTED")

    outstatus = pd.read_parquet(out_folder.joinpath("status_log.parq"))
    outstatus_validate = pd.read_parquet(validate_folder.joinpath("status_log_validate.parq"))
    testing.assert_dataset_equal(outstatus, outstatus_validate, "OUTSTATUS")

    outreject = pd.read_parquet(out_folder.joinpath("outreject.parq"))
    outreject_validate = pd.read_parquet(validate_folder.joinpath("outreject_validate.parq"))
    testing.assert_dataset_equal(outreject, outreject_validate, "OUTREJECT")

    outreject_all = pd.read_parquet(out_folder.joinpath("outreject_all.parq"))
    outreject_all_validate = pd.read_parquet(validate_folder.joinpath("outreject_all_validate.parq"))
    testing.assert_dataset_equal(outreject_all, outreject_all_validate, "OUTREJECT_ALL")

@pytest.mark.integration()
def test_errorloc_tutorial():
    out_folder, input_filepath = folder_setup("errorloc_test_tutorial")
    validate_folder = input_filepath.parent.joinpath("expected")
    execute_processor(input_filepath)

    outstatus = pd.read_parquet(out_folder.joinpath("status_file.parq"))
    outstatus_validate = pd.read_parquet(validate_folder.joinpath("status_file_validate.parq"))
    testing.assert_dataset_equal(outstatus, outstatus_validate, "OUTSTATUS")

    outreject = pd.read_parquet(out_folder.joinpath("outreject_all.parq"))
    outreject_validate = pd.read_parquet(validate_folder.joinpath("outreject_all_validate.parq"))
    testing.assert_dataset_equal(outreject, outreject_validate, "OUTREJECT")

@pytest.mark.integration()
def test_deterministic_h02(deterministic_expected_outdata_h02):
    out_folder, input_filepath = folder_setup("deterministic_test_h02")
    validate_folder = input_filepath.parent.joinpath("expected")
    execute_processor(input_filepath)

    outstatus = pd.read_parquet(out_folder.joinpath("status_log.parq"))
    outstatus_validate = pd.read_parquet(validate_folder.joinpath("status_log_validate.parq"))
    testing.assert_dataset_equal(outstatus, outstatus_validate, "OUTSTATUS")

    outdata = pd.read_parquet(out_folder.joinpath("imputed_file.parq"))
    testing.assert_dataset_equal(outdata, deterministic_expected_outdata_h02, "IMPUTED")

@pytest.mark.integration()
def test_estimator_01b(estimator_expected_outdata_01b):
    out_folder, input_filepath = folder_setup("estimator_test_01b")
    validate_folder = input_filepath.parent / "expected"
    execute_processor(ProcessorInput(job_id="j1",
                                     unit_id="id",
                                     input_folder=input_filepath.parent,
                                     indata_filename="indata.parq",
                                     instatus_filename="instatus.parq",
                                     seed=30000,
                                     save_format=[".parq", ".csv"],
                                     #NOTE: We only need to validate the minimal output files
                                     # so we can also test that the minimal setting works correctly
                                     process_output_type="minimal",
                                     log_level=2))

    outstatus = pd.read_parquet(out_folder / "status_log.parq")
    outstatus_validate = pd.read_parquet(validate_folder / "status_log_validate.parq")
    testing.assert_dataset_equal(outstatus, outstatus_validate, "OUTSTATUS")

    outdata = pd.read_parquet(out_folder / "imputed_file.parq")
    testing.assert_dataset_equal(outdata, estimator_expected_outdata_01b, "IMPUTED")
    
    # These are produced under process_output_type=ALL, make sure the MINIMAL setting works
    assert not Path.is_file(out_folder / "outacceptable.parq")
    assert not Path.is_file(out_folder / "outest_ef.parq")
    assert not Path.is_file(out_folder / "outest_parm.parq")

@pytest.mark.integration()
def test_estimator_04a():
    out_folder, input_filepath = folder_setup("estimator_test_04a")
    validate_folder = input_filepath.parent.joinpath("expected")
    execute_processor(input_filepath)

    outacceptable = pd.read_parquet(out_folder.joinpath("outacceptable.parq"))
    outacceptable_validate = pd.read_parquet(validate_folder.joinpath("outacceptable_validate.parq"))
    testing.assert_dataset_equal(outacceptable, outacceptable_validate, "OUTACCEPTABLE")

    outest_ef = pd.read_parquet(out_folder.joinpath("outest_ef.parq"))
    outest_ef_validate = pd.read_parquet(validate_folder.joinpath("outest_ef_validate.parq"))
    testing.assert_dataset_equal(outest_ef, outest_ef_validate, "OUTEST_EF")

    outest_parm = pd.read_parquet(out_folder.joinpath("outest_parm.parq"))
    outest_parm_validate = pd.read_parquet(validate_folder.joinpath("outest_parm_validate.parq"))
    testing.assert_dataset_equal(outest_parm, outest_parm_validate, "OUTEST_PARM")
    
    # These are produced under process_output_type=ALL, make sure the CUSTOM setting works
    assert not Path.is_file(out_folder / "outest_lr.parq")
    assert not Path.is_file(out_folder / "outrand_err.parq")

@pytest.mark.integration()
def test_massimp_c02():
    out_folder, input_filepath = folder_setup("massimp_test_c02")
    validate_folder = input_filepath.parent.joinpath("expected")
    execute_processor(input_filepath)

    outdonormap = pd.read_parquet(out_folder.joinpath("outdonormap.parq"))
    outdonormap_validate = pd.read_parquet(validate_folder.joinpath("outdonormap_validate.parq"))
    testing.assert_dataset_equal(outdonormap, outdonormap_validate, "DONORMAP")

    status_log = pd.read_parquet(out_folder.joinpath("status_log.parq"))
    status_log_validate = pd.read_parquet(validate_folder.joinpath("status_log_validate.parq"))
    testing.assert_dataset_equal(status_log, status_log_validate, "STATUS_LOG")

@pytest.mark.integration()
def test_udp(udp_imputed_file):
    out_folder, input_filepath = folder_setup("udp_test")
    execute_processor(input_filepath)

    outdata = pd.read_parquet(out_folder.joinpath("imputed_file.parq"))
    testing.assert_dataset_equal(outdata, udp_imputed_file, "IMPUTED")

@pytest.mark.integration()
def test_ibsp_training():
    out_folder, input_filepath = folder_setup("training_test_ibsp")
    validate_folder = input_filepath.parent / "expected"
    execute_processor(input_filepath)

    outdata = pd.read_parquet(out_folder / "imputed_file.parq")
    outdata_validate = pd.read_parquet(validate_folder / "imputed_file.parq")
    testing.assert_dataset_equal(outdata, outdata_validate, "IMPUTED")

    status_file = pd.read_parquet(out_folder / "status_file.parq")
    status_file_validate = pd.read_parquet(validate_folder / "status_file.parq")
    testing.assert_dataset_equal(status_file, status_file_validate, "status_file")

@pytest.mark.integration()
def test_example2():
    out_folder, input_filepath = folder_setup("udp_test_example2")
    validate_folder = input_filepath.parent.joinpath("expected")
    
    execute_processor(input_filepath)

    outdata = pd.read_parquet(out_folder.joinpath("imputed_file.parq"))
    outdata_validate = pd.read_parquet(validate_folder.joinpath("imputed_file.parq"))
    testing.assert_dataset_equal(outdata, outdata_validate, "IMPUTED")

    status_file = pd.read_parquet(out_folder.joinpath("status_file.parq"))
    status_file_validate = pd.read_parquet(validate_folder.joinpath("status_file.parq"))
    testing.assert_dataset_equal(status_file, status_file_validate, "status_file")

@pytest.mark.integration()
def test_processor_main_fr():
    out_folder, input_filepath = folder_setup("errorloc_test_tutorial_fr")
    validate_folder = input_filepath.parent.joinpath("expected")
    
    try:
        banffprocessor.processor.main([str(input_filepath), '-l', 'fr'])
        outstatus = pd.read_parquet(out_folder.joinpath("status_file.parq"))
        outstatus_validate = pd.read_parquet(validate_folder.joinpath("status_file_validate.parq"))
        testing.assert_dataset_equal(outstatus, outstatus_validate, "OUTSTATUS")
    finally:
        # Make sure the language is reset for the next test
        banffprocessor.set_language(banffprocessor.SupportedLanguage["en"])

#region PROCESS CONTROLS
@pytest.mark.integration()
def test_process_control():
    out_folder, input_filepath = folder_setup("process_control_test", 
                                              output_folder_name="out_filter_row_and_column")
    validate_folder = input_filepath.parent.joinpath("expected")
    
    input_params = ProcessorInput(job_id="filter_row_and_column",
                                  unit_id="ident",
                                  input_folder=input_filepath.parent,
                                  indata_filename="indata.parq",
                                  output_folder=out_folder,
                                  user_plugins_folder= "../../../examples/plugins",
                                  save_format=[".parq", ".csv"],
                                  log_level=2)
    execute_processor(input_params)
    
    # Assert indata ends the same way it started, as process controls apply only during execution
    outdata = pd.read_parquet(out_folder / "imputed_file.parq")
    outdata_validate = pd.read_parquet(input_filepath.parent / "indata.parq")
    testing.assert_dataset_equal(outdata, outdata_validate, "IMPUTED")
    
    # Assert the 2 separate process controls were applied correctly
    outdata = pd.read_parquet(out_folder / "indata_TEST_1.parq")
    outdata_validate = pd.read_parquet(validate_folder / "indata_TEST_1_validate.parq")
    testing.assert_dataset_equal(outdata, outdata_validate, "IMPUTED")
    
    outdata = pd.read_parquet(out_folder / "indata_TEST_2.parq")
    outdata_validate = pd.read_parquet(validate_folder / "indata_TEST_2_validate.parq")
    testing.assert_dataset_equal(outdata, outdata_validate, "IMPUTED")

@pytest.mark.integration()
def test_process_control_editgroupfilter():
    out_folder, input_filepath = folder_setup("process_control_test", output_folder_name="out_filter_editgroup")
    validate_folder = input_filepath.parent.joinpath("expected")
    
    input_params = ProcessorInput(job_id="filter_editgroup",
                                  unit_id="ident",
                                  input_folder=input_filepath.parent,
                                  indata_filename="indata.parq",
                                  instatus_filename="instatus.parq",
                                  output_folder=out_folder,
                                  user_plugins_folder= "../../../examples/plugins",
                                  save_format=[".parq", ".csv"],
                                  log_level=2)
    execute_processor(input_params)
    
    # Assert status_file ends the same way it started, as process controls apply only during execution
    outstatus = pd.read_parquet(out_folder / "status_file.parq")
    outstatus_validate = pd.read_parquet(input_filepath.parent / "instatus.parq")
    testing.assert_dataset_equal(outstatus, outstatus_validate, "status_file")
    
    # Assert the process control was applied correctly
    outstatus = pd.read_parquet(out_folder / "instatus_TEST_3.parq")
    outstatus_validate = pd.read_parquet(validate_folder / "instatus_TEST_3_validate.parq")
    testing.assert_dataset_equal(outstatus, outstatus_validate, "INSTATUS_TEST_3")

@pytest.mark.integration()
def test_process_control_remove_rejected():
    out_folder, input_filepath = folder_setup("process_control_test_remove_rejected")
    validate_folder = input_filepath.parent.joinpath("expected")
    
    execute_processor(input_filepath)
    
    filtered_file = pd.read_parquet(out_folder.joinpath("filtered_data.parq"))
    filtered_file_validate = pd.read_parquet(validate_folder.joinpath("filtered_data.parq"))
    
    imputed_file = pd.read_parquet(out_folder.joinpath("imputed_file.parq"))
    imputed_file_validate = pd.read_parquet(validate_folder.joinpath("imputed_file.parq"))
    
    testing.assert_dataset_equal(filtered_file, filtered_file_validate, "FILTERED")
    testing.assert_dataset_equal(imputed_file, imputed_file_validate, "IMPUTED")

#ENDREGION

#region EDIT PROCS
@pytest.mark.integration()
def test_verifyedits_success():
    out_folder, input_filepath = folder_setup("verifyedits_test", output_folder_name="out_success")
    input_params = ProcessorInput(job_id="job_succeed", 
                                  input_folder=input_filepath.parent,
                                  output_folder=out_folder)
    execute_processor(input_params)
    
    # Make sure the previously run test leaves the Processor in English
    with open(out_folder / "banffprocessor.log") as log_file:
        content = log_file.read()
        
        msg = """Implied edits found:
                - X  <= 0
                    X  <= 16.66667
                    Y  <= 10"""
        assert_log_contains(msg, content, clean_whitespace=True)
        
        msg = """
            Submitted maximum number of implied edits ...................:  10
            Number of implied edits generated ...........................:  3
                Number of implied equalities ............................:  0
                Number of implied inequalities ..........................:  3"""
        assert_log_contains(msg, content, clean_whitespace=True)

@pytest.mark.integration()
def test_verifyedits_commas():
    out_folder, input_filepath = folder_setup("verifyedits_test", output_folder_name="out_commas")
    input_params = ProcessorInput(job_id="job_comma_format", 
                                  input_folder=input_filepath.parent,
                                  output_folder=out_folder)
    
    with pytest.raises(banffprocessor.exceptions.ProcedureReturnCodeError):
        execute_processor(input_params)
    
    with open(out_folder / "banffprocessor.log") as log_file:
        content = log_file.read()
        
        msg = "ERROR: Invalid edits."
        assert_log_contains(msg, content, clean_whitespace=True)
        
        msg = "ERROR: Edits parser: Looking for 'SemiColon' but found 'Unknown character' instead."
        assert_log_contains(msg, content, clean_whitespace=True)
    
@pytest.mark.integration()
def test_verifyedits_nonlinear():
    out_folder, input_filepath = folder_setup("verifyedits_test", output_folder_name="out_nonlinear")
    input_params = ProcessorInput(job_id="job_non_linear", 
                                  input_folder=input_filepath.parent,
                                  output_folder=out_folder)
    with pytest.raises(banffprocessor.exceptions.ProcedureReturnCodeError):
        execute_processor(input_params)
    
    with open(out_folder / "banffprocessor.log") as log_file:
        content = log_file.read()
        
        msg = "ERROR: Invalid edits."
        assert_log_contains(msg, content, clean_whitespace=True)
        
        msg = "ERROR: Edits parser: Looking for 'Operator' but found 'Unknown character' instead."
        assert_log_contains(msg, content, clean_whitespace=True)
    
@pytest.mark.integration()
def test_verifyedits_noedits():
    out_folder, input_filepath = folder_setup("verifyedits_test", output_folder_name="out_noedits")
    input_params = ProcessorInput(job_id="job_no_edits", 
                                  input_folder=input_filepath.parent,
                                  output_folder=out_folder)
    with pytest.raises(banffprocessor.exceptions.BanffPackageExecutionError):
        execute_processor(input_params)

@pytest.mark.integration()
def test_editstats(editstat_indata_02):
    # Test not giving edits? Might want to throw error sooner than later?
    out_folder, input_filepath = folder_setup("editstats_test")
    validate_folder = input_filepath.parent.joinpath("expected")
    
    input_params = ProcessorInput(job_id="j1", 
                                  input_folder=input_filepath.parent,
                                  process_output_type="custom",
                                  save_format=['.csv', '.parq'])
    execute_processor(input_params, editstat_indata_02)
    
    editapplic = pd.read_parquet(out_folder.joinpath("outedit_applic.parq"))
    editapplic_validate = pd.read_parquet(validate_folder.joinpath("outedit_applic_validate.parq"))
    testing.assert_dataset_equal(editapplic, editapplic_validate, "EDITAPPLIC")
    
    editstatus = pd.read_parquet(out_folder.joinpath("outedit_status.parq"))
    editstatus_validate = pd.read_parquet(validate_folder.joinpath("outedit_status_validate.parq"))
    testing.assert_dataset_equal(editstatus, editstatus_validate, "EDITSTATUS")
    
    keditsstatus = pd.read_parquet(out_folder.joinpath("outk_edits_status.parq"))
    keditsstatus_validate = pd.read_parquet(validate_folder.joinpath("outk_edits_status_validate.parq"))
    testing.assert_dataset_equal(keditsstatus, keditsstatus_validate, "KEDITSSTATUS")
    
    varsrole = pd.read_parquet(out_folder.joinpath("outvars_role.parq"))
    varsrole_validate = pd.read_parquet(validate_folder.joinpath("outvars_role_validate.parq"))
    testing.assert_dataset_equal(varsrole, varsrole_validate, "VARSROLE")
#endregion

#region PROCESS BLOCKS
@pytest.mark.integration()
def test_job_proc_basic():
    out_folder, input_filepath = folder_setup(Path("job_proc_test") / "basic")
    validate_folder = input_filepath.parent.joinpath("expected")

    metadata_folder = input_filepath.parent / "metadata"
    metadata_file = metadata_folder / "banffprocessor_metadata.xlsx"
    e2x.convert_excel_to_xml(metadata_file)

    # Loading parameters from the JSON file
    input_params = ProcessorInput(
        job_id="j1",
        unit_id="IDENT",
        input_folder=input_filepath.parent,
        indata_filename="current.parq",
        histdata_filename="historical.parq",
        no_by_stats=True,
        seed=1,
        save_format=[".csv"],
        log_level=2,
        process_output_type="Custom"
    )
 
    execute_processor(input_params)

    outdata = pd.read_csv(out_folder / "imputed_file.csv")
    outdata_validate = pd.read_csv(validate_folder / "imputed_file.csv")
    testing.assert_dataset_equal(outdata, outdata_validate, "IMPUTED")
    
    # Custom process_output_type was set so make sure the 2 expected tables are here
    outlier_status = pd.read_csv(out_folder / "outlier_status.csv")
    outlier_status_validate = pd.read_csv(validate_folder / "outlier_status.csv")
    testing.assert_dataset_equal(outlier_status, outlier_status_validate, "OUTLIER_STATUS")
    
    outsummary = pd.read_csv(out_folder / "outsummary.csv")
    outsummary_validate = pd.read_csv(validate_folder / "outsummary.csv")
    testing.assert_dataset_equal(outsummary, outsummary_validate, "OUTSUMMARY")
    
    status_log = pd.read_csv(out_folder / "status_log.csv")
    status_log_validate = pd.read_csv(validate_folder / "status_log.csv")
    testing.assert_dataset_equal(status_log, status_log_validate, "STATUS_LOG")
    
    assert Path.is_file(out_folder / "outreject_all.csv")
    assert Path.is_file(out_folder / "outreject.csv")
    assert Path.is_file(out_folder / "status_file.csv")
    assert Path.is_file(out_folder / "status_log.csv")
    assert Path.is_file(out_folder / "time_store.csv")
    # Ensure the Custom process_output_type is not producing extra files
    assert not Path.is_file(out_folder / "outest_lr.csv")
    assert not Path.is_file(out_folder / "outest_ef.csv")
    assert not Path.is_file(out_folder / "outest_parm.csv")
    assert not Path.is_file(out_folder / "outrand_err.csv")
    assert not Path.is_file(out_folder / "outmatching_fields.csv")
    
    # Ensure the sub-block's output folder is created properly
    block_out_folder = out_folder / "j1_1.0_j2" / "out"
    assert Path.is_file(block_out_folder / "imputed_file.csv")
    assert Path.is_file(block_out_folder / "outlier_status.csv")
    assert Path.is_file(block_out_folder / "outsummary.csv")
    assert Path.is_file(block_out_folder / "status_file.csv")
    assert Path.is_file(block_out_folder / "status_log.csv")
    assert Path.is_file(block_out_folder / "time_store.csv")
#endregion
