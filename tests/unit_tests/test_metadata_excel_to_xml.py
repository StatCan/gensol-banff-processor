import os
import shutil
from pathlib import Path
from unittest import mock

import banffprocessor.util.metadata_excel_to_xml as e2x
import pytest


def setup_temp_excel(temp_path: str) -> str:
    file_dir = Path(__file__).parent.joinpath("test_files")
    excel_path = file_dir.joinpath("Banff_2.08_Processor_Test.xlsx")
    return shutil.copy(str(excel_path), temp_path)

def expected_file_asserts(tmp_path: str) -> None:
    # for each file created. 
    assert Path(tmp_path).joinpath("algorithms.xml").is_file()
    assert Path(tmp_path).joinpath("donorspecs.xml").is_file()
    assert Path(tmp_path).joinpath("estimators.xml").is_file()
    assert Path(tmp_path).joinpath("estimatorspecs.xml").is_file()
    assert Path(tmp_path).joinpath("expressions.xml").is_file()
    assert Path(tmp_path).joinpath("massimputationspecs.xml").is_file()
    assert Path(tmp_path).joinpath("outlierspecs.xml").is_file()
    assert Path(tmp_path).joinpath("processcontrols.xml").is_file()
    assert Path(tmp_path).joinpath("proratespecs.xml").is_file()
    assert Path(tmp_path).joinpath("varlists.xml").is_file()
    assert Path(tmp_path).joinpath("verifyeditsspecs.xml").is_file()
    assert Path(tmp_path).joinpath("weights.xml").is_file()
    
    # getsize() returns different values for local vs on the CI/CD pipeline.
    # so these will need to be changed to something that works on both
    # seemingly 1 additional character per line    
    assert Path(tmp_path).joinpath("jobs.xml").is_file()
    #assert os.path.getsize(test_file) == 3593

    assert Path(tmp_path).joinpath("edits.xml").is_file()
    #assert os.path.getsize(test_file) == 7239

    assert Path(tmp_path).joinpath("editgroups.xml").is_file()
    #assert os.path.getsize(test_file) == 4612

@pytest.mark.excel_convert()
def test_metadata_excel_to_xml(tmp_path):
    excel_filepath = setup_temp_excel(tmp_path)
    assert Path(excel_filepath).is_file()

    # Function to be tested
    e2x.convert_excel_to_xml(excel_filepath, tmp_path)

    expected_file_asserts(tmp_path)

@pytest.mark.excel_convert()
def test_metadata_excel_to_xml_main(tmp_path):
    excel_filepath = setup_temp_excel(tmp_path)
    assert Path(excel_filepath).is_file()

    # Function to be tested
    e2x.main([excel_filepath])
    
    expected_file_asserts(tmp_path)

@pytest.mark.excel_convert()
def test_input_args(tmp_path):
    """Test parsing on input args"""
    excel_filepath = setup_temp_excel(tmp_path)

    assert Path(excel_filepath).is_file()

    test_args = e2x.get_args([excel_filepath, "-o", str(tmp_path)])
    assert test_args.filename == excel_filepath
    assert test_args.outdir == str(tmp_path)

@pytest.mark.excel_convert()
def test_input_with_no_args(capsys):
    """Test parsing with no input args"""
    with pytest.raises(SystemExit):
        e2x.get_args([])
    out, err = capsys.readouterr()

    assert "the following arguments are required" in err

@pytest.mark.excel_convert()
def test_main_with_no_args(capsys):
    """Test main with no input args"""
    with pytest.raises(SystemExit) as e:
        e2x.main(None)

    # This is how to check for a SystemExit
    assert e.value.code != 0

@pytest.mark.excel_convert()
def test_input_with_extra_args(capsys):
    """Test parsing with no extra positional arg"""
    with pytest.raises(SystemExit):
        e2x.get_args(["arg1", "arg2"])
    out, err = capsys.readouterr()

    assert "unrecognized arguments" in err

@pytest.mark.excel_convert()
def test_excel_not_provided(capsys):
    with pytest.raises(FileNotFoundError):
        e2x.convert_excel_to_xml("","")

@pytest.mark.excel_convert()
def test_init():
    from banffprocessor.util import metadata_excel_to_xml as module
    with mock.patch.object(module, "main", return_value=42):
        with mock.patch.object(module, "__name__", "__main__"):
            with mock.patch.object(module.sys, "exit") as mock_exit:
                module.init()

                assert mock_exit.call_args[0][0] == 42
