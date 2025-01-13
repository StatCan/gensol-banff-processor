import io
import pyarrow as pa
import pyarrow.csv
import duckdb
import pytest
import logging

from banffprocessor.processor_data import ProcessorData
from banffprocessor.processor_input import ProcessorInput
from banffprocessor.processor_logger import *
from banff import logging as lg

from banffprocessor.metadata.metaobjects import MetaObjects
from banffprocessor.metadata.models.metadataclass import MetadataClass
from banffprocessor.metadata.models.algorithms import Algorithms
from banffprocessor.metadata.models.donorspecs import Donorspecs
from banffprocessor.metadata.models.editgroups import Editgroups
from banffprocessor.metadata.models.edits import Edits
from banffprocessor.metadata.models.errorlocspecs import Errorlocspecs
from banffprocessor.metadata.models.estimators import Estimators
from banffprocessor.metadata.models.estimatorspecs import Estimatorspecs
from banffprocessor.metadata.models.jobs import Jobs
from banffprocessor.metadata.models.expressions import Expressions
from banffprocessor.metadata.models.massimputationspecs import Massimputationspecs
from banffprocessor.metadata.models.outlierspecs import Outlierspecs
from banffprocessor.metadata.models.processcontrols import ProcessControls
from banffprocessor.metadata.models.proratespecs import Proratespecs
from banffprocessor.metadata.models.uservars import Uservars
from banffprocessor.metadata.models.varlists import Varlists
from banffprocessor.metadata.models.verifyeditsspecs import Verifyeditsspecs
from banffprocessor.metadata.models.weights import Weights

@pytest.fixture(scope="module", autouse=True)
def clear_file_log_handler():
    """Clear any log handlers on the logger so that unit tests do not inadvertently
    append errors or other information to the last log file created by integration tests.
    """
    print("Clearing log handler...")
    logger = lg.get_top_logger()
    # Remove all FileHandlers used by the previous tests
    logger.handlers = [ h for h in logger.handlers if not isinstance(h, logging.FileHandler) ]
    print("Cleared log handler.")

def base_metaobjects(dbconn=duckdb) -> MetaObjects:
    return MetaObjects(dbconn=dbconn)

def base_jobs_list(dbconn=duckdb) -> list[Jobs]:
    return [
        Jobs("j1", 20, "procA", dbconn=dbconn),
        Jobs("j1", 50, "JOB", specid="j2", dbconn=dbconn),
        Jobs("j1", 30.5, "procA", dbconn=dbconn),
        Jobs("j2", 1, "procC", dbconn=dbconn),
        Jobs("j2", 2, "procA", dbconn=dbconn),
        Jobs("j2", 3, "JOB", specid="j3", dbconn=dbconn),
        Jobs("j3", 100, "procA", dbconn=dbconn),
    ]

def base_varlists_list(dbconn=duckdb) -> list[Varlists]:
    return [
        Varlists("v1", 1, "v1-field", dbconn=dbconn),
        Varlists("v1", 2, "v1-field2", dbconn=dbconn),
        Varlists("v2", 2, "v2-field", dbconn=dbconn),
        Varlists("v2", 1, "v2-field2", dbconn=dbconn),
        Varlists("v3", 1, "v3-field", dbconn=dbconn),
        Varlists("v4", 1, "v4-field", dbconn=dbconn),
    ]

def base_editgroups_list(dbconn=duckdb) -> list[Editgroups]:
    return [
        Editgroups("v1", "e1", dbconn=dbconn),
        Editgroups("v1", "e2", dbconn=dbconn),
        Editgroups("v1", "e5", dbconn=dbconn),
        Editgroups("v2", "e3", dbconn=dbconn),
        Editgroups("v2", "e4", dbconn=dbconn),
        Editgroups("v3", "e1", dbconn=dbconn),
        Editgroups("v4", "e2", dbconn=dbconn),
    ]

def base_edits_list(dbconn=duckdb) -> list[Edits]:
    return [
        Edits("e1", "x", "y", ">", "PASS", dbconn=dbconn),
        Edits("e2", "a", "b", "<", "FAIL", dbconn=dbconn),
        Edits("e3", "c", "d", ">=", "ACCEPTE", dbconn=dbconn),
        Edits("e4", "e", "f", "=", "REJET", dbconn=dbconn),
        Edits("e5", "g", "h", "!=", dbconn=dbconn),
    ]

def base_expressions_list(dbconn=duckdb) -> list[Expressions]:
    return [
        Expressions("e1", "x", dbconn=dbconn),
        Expressions("e2", "y", dbconn=dbconn),
        Expressions("e3", "z", dbconn=dbconn),
        Expressions("e4", "w", dbconn=dbconn),
    ]

def base_weights_list(dbconn=duckdb) -> list[Weights]:
    return [
        Weights("w1", "area", 7, dbconn=dbconn),
        Weights("w1", "length", 5, dbconn=dbconn),
        Weights("w1", "volume", 9, dbconn=dbconn),
        Weights("w2", "width", 3, dbconn=dbconn),
        Weights("w2", "height", 1, dbconn=dbconn),
        Weights("w3", "mass", 9, dbconn=dbconn),
    ]

def base_algorithms_list(dbconn=duckdb) -> list[Algorithms]:
    return [
        Algorithms("CUST_CURREG", "", "1", "LR", dbconn=dbconn),
        Algorithms("CUST_PREMEAN", "", "2", "EF", dbconn=dbconn),
        Algorithms("CUST_PREAUX", "", "3", "LR", dbconn=dbconn),
        Algorithms("TESTALGO", "", "4", "LR", dbconn=dbconn),
    ]

def base_estimators_list(dbconn=duckdb) -> list[Estimators]:
    return [
        Estimators("est1", 2, "v1", "algo2", "y", dbconn=dbconn),
        Estimators("est1", 1, "v2", "algo1", "n", dbconn=dbconn),
        Estimators("est2", 1, "v1", "algo1", "y", dbconn=dbconn),
        Estimators("est3", 1, "v1", "algo1", "y", dbconn=dbconn),
        Estimators("est4", 1, "v1", "algo1", "y", dbconn=dbconn),
    ]

def base_uservars_list(dbconn=duckdb) -> list[Uservars]:
    return [
        Uservars("test", "test1", "var1", "1", dbconn=dbconn),
        Uservars("test", "test1", "var2", "2", dbconn=dbconn),
        Uservars("test", "test2", "var1", "2", dbconn=dbconn),
        Uservars("other_test", "other_test1", "var1", "1", dbconn=dbconn),
        Uservars("other_test", "other_test2", "var1", "1", dbconn=dbconn),
    ]

#region Specs objects
def base_donorspecs_list(dbconn=duckdb) -> list[Donorspecs]:
    return [Donorspecs(specid=Donorspecs.__name__ + str(x),
                                n=x, dbconn=dbconn) for x in range(1,6)]

def base_errorlocspecs_list(dbconn=duckdb) -> list[Errorlocspecs]:
    return [Errorlocspecs(specid=Errorlocspecs.__name__ + str(x), dbconn=dbconn) for x in range(1,6)]

def base_estimatorspecs_list(dbconn=duckdb) -> list[Estimatorspecs]:
    return [Estimatorspecs(specid=Estimatorspecs.__name__ + str(x),
                                    estimatorid=str(x), dbconn=dbconn) for x in range(1,6)]

def base_massimputationspecs_list(dbconn=duckdb) -> list[Massimputationspecs]:
    return [Massimputationspecs(specid=Massimputationspecs.__name__ + str(x),
                                         mustimputeid=str(x), dbconn=dbconn) for x in range(1,6)]

def base_outlierspecs_list(dbconn=duckdb) -> list[Outlierspecs]:
    methods = ["Historic", "Ratio", "Sigmagap", "Current"]
    return [Outlierspecs(specid=Outlierspecs.__name__ + str(x),
                                  method=methods[x % 4], dbconn=dbconn) for x in range(1,6)]

def base_proratespecs_list(dbconn=duckdb) -> list[Proratespecs]:
    return [Proratespecs(specid=Proratespecs.__name__ + str(x), dbconn=dbconn) for x in range(1,6)]

def base_verifyeditsspecs_list(dbconn=duckdb) -> list[Verifyeditsspecs]:
    return [Verifyeditsspecs(specid=Verifyeditsspecs.__name__ + str(x), dbconn=dbconn) for x in range(1,6)]

def base_processcontrols_list(dbconn=duckdb) -> list[ProcessControls]:
    return [
        ProcessControls("TEST_1", "column_filter", "a, c", targetfile="instatus", dbconn=dbconn),
        ProcessControls("TEST_3", "column_filter", "b, d", targetfile="instatus", dbconn=dbconn),
        ProcessControls("TEST_4", "column_filter", "b, d", targetfile="instatus", dbconn=dbconn),
        ProcessControls("TEST_1", "row_filter", "a > b", targetfile="indata", dbconn=dbconn),
    ]

#endregion

#region DataFrames/Table

def ds_test_data() -> pa.Table:
    return pyarrow.csv.read_csv(io.BytesIO("""
ident,FIELDID,STATUS,OUTSTATUS,METHOD,CURRENT_VALUE,HIST_AUX,HIST_AUX_VALUE,EFFECT
R01,V1,FTI,ODIL,HB,4,V1,19,-4.089285714
R04,V2,FTE,ODEL,HB,3,V1,8,-1.857142857
R03,V2,FTE,ODER,HB,8,V2,3,1.8444444444
R02,V2,FTI,ODIR,HB,19,V2,4,4.0666666667
R04,V3,FTI,ODIR,HB,19,V2,4,4.0666666667
""".encode()))

def ds_test_data_sorted() -> pa.Table:
    return pyarrow.csv.read_csv(io.BytesIO("""
ident,FIELDID,STATUS,OUTSTATUS,METHOD,CURRENT_VALUE,HIST_AUX,HIST_AUX_VALUE,EFFECT
R01,V1,FTI,ODIL,HB,4,V1,19,-4.089285714
R02,V2,FTI,ODIR,HB,19,V2,4,4.0666666667
R03,V2,FTE,ODER,HB,8,V2,3,1.8444444444
R04,V2,FTE,ODEL,HB,3,V1,8,-1.857142857
R04,V3,FTI,ODIR,HB,19,V2,4,4.0666666667
""".encode()))
    
def ds_test_status() -> pa.Table:
    #TODO: Don't use Pandas, just temporary
    return pyarrow.csv.read_csv(io.BytesIO("""
IDENT,FIELDID,STATUS,VALUE,JOBID,SEQNO
R01,EGG_LAID,FTI,1448.0,j1,10.0
R02,QR_EXP,FTI,2352.0,j1,10.0
R03,QR_REV,FTI,1533.0,j1,10.0
R04,EGG_SOLD,FTI,-11.0,j1,10.0
R05,EGG_LAID,FTI,-12.0,j1,10.0
R06,HEN_OTH,FTI,587.0,j1,10.0
""".encode()))

#endregion

def processor_input_dummy() -> ProcessorInput:
    # Minimum required fields for a ProcessorInput object
    return ProcessorInput(job_id="j1", unit_id="abcd", input_folder="./")

def pyarrow_test_table() -> pa.Table:
    return pa.table({"test": [1,2,3], "other": ["a", "b", "c"]})

#region Fixtures

@pytest.fixture()
def input_test_data() -> pa.Table:
    return ds_test_data()

@pytest.fixture()
def input_test_data_sorted()  -> pa.Table:
    return ds_test_data_sorted()

@pytest.fixture(scope="session")
def input_test_status() -> pa.Table:
    return ds_test_status()

@pytest.fixture(scope="session")
def pyarrow_test_data() -> pa.Table:
    return pyarrow_test_table()

@pytest.fixture(scope="session")
def session_processor_data() -> ProcessorData:
    return ProcessorData(processor_input_dummy())

#region Metadata Fixtures

@pytest.fixture()
def empty_metaobjects() -> MetaObjects:
    return base_metaobjects()

@pytest.fixture(scope="session")
def full_metaobjects():
    conn = duckdb.connect(database=':memory:')
    metaobjects = base_metaobjects(dbconn=conn)
    metaobjects.add_objects_of_single_type(base_jobs_list(dbconn=metaobjects.dbconn))
    metaobjects.add_objects_of_single_type(base_varlists_list(dbconn=metaobjects.dbconn))
    metaobjects.add_objects_of_single_type(base_editgroups_list(dbconn=metaobjects.dbconn))
    metaobjects.add_objects_of_single_type(base_edits_list(dbconn=metaobjects.dbconn))
    metaobjects.add_objects_of_single_type(base_expressions_list(dbconn=metaobjects.dbconn))
    metaobjects.add_objects_of_single_type(base_weights_list(dbconn=metaobjects.dbconn))
    metaobjects.add_objects_of_single_type(base_algorithms_list(dbconn=metaobjects.dbconn))
    metaobjects.add_objects_of_single_type(base_estimators_list(dbconn=metaobjects.dbconn))
    metaobjects.add_objects_of_single_type(base_uservars_list(dbconn=metaobjects.dbconn))
    metaobjects.add_objects_of_single_type(base_processcontrols_list(dbconn=metaobjects.dbconn))

    # Specs objects
    metaobjects.add_objects_of_single_type(base_donorspecs_list(dbconn=metaobjects.dbconn))
    metaobjects.add_objects_of_single_type(base_errorlocspecs_list(dbconn=metaobjects.dbconn))
    metaobjects.add_objects_of_single_type(base_estimatorspecs_list(dbconn=metaobjects.dbconn))
    metaobjects.add_objects_of_single_type(base_massimputationspecs_list(dbconn=metaobjects.dbconn))
    metaobjects.add_objects_of_single_type(base_outlierspecs_list(dbconn=metaobjects.dbconn))
    metaobjects.add_objects_of_single_type(base_proratespecs_list(dbconn=metaobjects.dbconn))
    metaobjects.add_objects_of_single_type(base_verifyeditsspecs_list(dbconn=metaobjects.dbconn))
    yield metaobjects
    conn.close()
 
@pytest.fixture()
def input_jobs_list():
    Jobs.initialize()
    yield base_jobs_list()
    Jobs.cleanup()

@pytest.fixture()
def jobs_list_with_cycle():
    Jobs.initialize()
    ret = base_jobs_list()
    ret.append(Jobs("j2", 4, "JOB", specid="j1"))
    yield ret
    Jobs.cleanup()

@pytest.fixture()
def input_editgroups_list():
    Editgroups.initialize()
    yield base_editgroups_list()
    Editgroups.cleanup()

@pytest.fixture()
def input_edits_list() -> list[Edits]:
    return base_edits_list()

@pytest.fixture()
def input_expressions_list():
    Expressions.initialize()
    yield base_expressions_list()
    Expressions.cleanup()

@pytest.fixture()
def input_weights_list():
    Weights.initialize()
    yield base_weights_list()
    Weights.cleanup()

@pytest.fixture()
def input_algorithms_list():
    Algorithms.initialize()
    yield base_algorithms_list()
    Algorithms.cleanup()

@pytest.fixture()
def input_estimators_list():
    conn = duckdb.connect(database=':memory:')
    Estimators.initialize(dbconn=conn)
    yield base_estimators_list(dbconn=conn)
    Estimators.cleanup(dbconn=conn)
    conn.close()

@pytest.fixture()
def input_donorspecs_list() -> list[Donorspecs]:
    return base_donorspecs_list()

@pytest.fixture()
def input_uservars_list() -> list[Uservars]:
    return base_uservars_list()

@pytest.fixture()
def input_test_dict() -> dict[str,str]:
    return {
        "vara":1,
        "varb":2,
        "varc":3,
        "vard":4
    }
    
#endregion
#endregion