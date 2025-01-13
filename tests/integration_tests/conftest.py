from collections import defaultdict
from io import StringIO

import numpy as np
import pandas as pd
import pyarrow as pa
import pytest

# def pytest_sessionstart(session):
#     """Called after the Session object has been created and
#     before performing collection and entering the run test loop.
#     """

def indataCharKey():
    # synthetic input dataset
    return pd.read_csv(StringIO("""
    ident area total Q1 Q2 Q3 Q4 staff
    REC01 A1 500 120 150 80 150 50
    REC02 A1 750 200 170 130 250 75
    REC04 A1 1000 150 250 350 250 100
    REC05 A2 1050 200 225 325 300 100
    """), sep=r"\s+", dtype={"ident": str, "area": str})

def instatCharKey():
    return pd.read_csv(StringIO("""
    ident fieldid status
    REC01 Q3 IPR
    REC04 Q2 FTE
    REC04 Q3 FTI
    REC04 Q4 FTI
    """), sep=r"\s+", dtype={"ident": str, "fieldid": str, "status": str})

@pytest.fixture()
def instatCharKey_by_var():
    """Originally taken from donorD03 test case, modified to add BY variables"""
    return pd.read_csv(StringIO("""
    ident fieldid status area staff
    REC01 Q3 IPR A1 50
    REC04 Q2 FTE A1 100
    REC04 Q3 FTI A1 100
    REC04 Q4 FTI A1 100
    """), sep=r"\s+", dtype={"ident": str, "fieldid": str, "status": str})

@pytest.fixture()
def prorate_expected_outdata_o04():
    return pd.read_csv(StringIO("""
REC,AREA,VA,VB,VC,VD,TOT1,VE,VF,VG,TOT2,GT
1,1,1,2,3,4,5,6,7,8,9,10
2,1,-5,2,3,4,4,6,7,8,6,10
3,1,-5,2,3,4,4,6,7,8,6,10
4,1,1,2,3,4,5,6,7,8,9,10
5,1,1,2,3,4,5,6,7,8,9,10
6,2,-5,2,3,4,4,6,7,8,6,10
7,2,-5,2,3,4,4,6,7,8,6,10
8,2,1,2,3,4,5,6,7,8,9,10
9,3,-5,2,3,4,4,6,7,8,6,10
    """), dtype={"REC": str})

@pytest.fixture()
def deterministic_expected_outdata_h02():
    # defaultdict allows us to specify character columns and make others float by default
    d = defaultdict(lambda: np.float64)
    d["rec"] = str
    return pd.read_csv(StringIO("""
        rec VA VB VC VD TOT1 VE VF VG TOT2 GT
        3 16.0 149.05 36.21 10.54 211.8 49.21 88.23 38.95 178.2 390.0
        6 76.21 20.54 38.99 33.63 102.1 53.58 16.73 95.63 115.8 470.5
        7 50.6 45.24 97.48 45.96 297.0 NaN 86.4 0.05 89.6 434.2
    """), sep=r"\s+", dtype=d, float_precision="round_trip") # `float_precision` only works in this case when 'round_trip' or 'legacy'

@pytest.fixture()
def udp_imputed_file():
    return pd.read_csv(StringIO("""
        IDENT area V1 V2
        R01 1 15004 19
        R02 1 14 5
        R03 1 18 19
        R04 1 7 15006
        R05 1 1 1
    """), sep=r"\s+")

@pytest.fixture()
def donorimp_expected_outdata_it04():
    df = indataCharKey().copy()

    df.at[1,"staff"] = 100

    # specific change expected for this test
    df.loc[df["ident"] == "REC04", ["Q3"]] = 130
    return df

@pytest.fixture()
def estimator_expected_outdata_01b():
    return pd.read_csv(StringIO("""
        ID X Y Z
        1A 1 1 1.0
        2A 2 2 2.0
        3A 3 3 1.5
    """), sep=r"\s+")

@pytest.fixture()
def massimp_outdonormap_01():
    d = defaultdict(lambda: np.float64)
    d["RECIPIENT"] = str
    d["DONOR"] = str
    d["JOBID"] = str

    return pd.read_csv(StringIO("""
    RECIPIENT  DONOR  NUMBER_OF_ATTEMPTS DONORLIMIT JOBID SEQNO
    03         02     1.0                NaN        j1    1.0
    05         04     1.0                NaN        j1    1.0
     """), sep=r"\s+", dtype=d)

@pytest.fixture
def editstat_indata_02():
    var_types = defaultdict(lambda: np.float64) # default to numeric
    # explicitly set character values
    #var_types['ident'] = str
    
    return pd.read_csv(StringIO("""
            A B C D E F G H TOT1 TOT2 TOT
            10 0 -4 0 5 6 15 0 6 26 30
            0 10 20 1 5 7 0 12 31 24 55
            25 55 0 -2 -2 20 14 30 80 62 NaN
            -5 15 12 NaN 12 17 -3 19 NaN 45 71
            15 -4 -5 2 4 -1 12 -20 8 -5 3
        """), 
        sep=r'\s+', 
        dtype=var_types
    )