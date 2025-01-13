"""Metadata model for Estimators."""

import duckdb
import numpy as np

from banffprocessor.exceptions import MetadataConstraintError
from banffprocessor.metadata.models.metadataclass import MetadataClass
from banffprocessor.nls import _


def builtin_estimators() -> dict:
    """Return built-in estimators as a dictionary, where the key is the name and the value is the type."""
    return {
        "AUXTREND": "EF",
        "AUXTREND2": "EF",
        "CURAUX": "EF",
        "CURAUXMEAN": "EF",
        "CURMEAN": "EF",
        "CURSUM2": "EF",
        "CURSUM3": "EF",
        "CURSUM4": "EF",
        "DIFTREND": "EF",
        "PREAUX": "EF",
        "PREVALUE": "EF",
        "PREMEAN": "EF",
        "PREAUXMEAN": "LR",
        "CURRATIO": "LR",
        "CURRATIO2": "LR",
        "CURREG": "LR",
        "CURREG_E2": "LR",
        "CURREG2": "LR",
        "CURREG3": "LR",
        "HISTREG": "LR",
    }

class Estimators(MetadataClass):
    """Estimators metadata class."""

    def __init__(self, estimatorid: str, seqno: float, fieldid: str, algorithmname: str, randomerror: bool,
                 auxvariables: str | None =None, weightvariable: str | None =None,
                 variancevariable: str | None =None, varianceexponent: float | None =None,
                 varianceperiod: str | None =None, excludeimputed: bool | None =None,
                 excludeoutliers: bool | None =None, countcriteria: int | None =None,
                 percentcriteria: float | None =None, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Validate and create metadata entry, if validation passes."""
        self.estimatorid = estimatorid
        self.seqno = float(seqno)
        self.fieldid = fieldid
        self.algorithmname = algorithmname
        self.auxvariables = auxvariables
        self.weightvariable = weightvariable

        self.variancevariable = variancevariable
        self.varianceexponent = None if varianceexponent is None else float(varianceexponent)
        self.varianceperiod = varianceperiod

        #constraint invalidVariance
        variance_empty = [self.variancevariable is None,
                         self.varianceexponent is None,
                         self.varianceperiod is None]

        if(not all(variance_empty) and any(variance_empty)):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("variance fields must either all be empty or all have values.")
            raise MetadataConstraintError(msg)

        # Currently gives value None if field is empty or whitespace
        if excludeimputed is not None and excludeimputed != " ":
            if(excludeimputed.upper() == "Y"):
                self.excludeimputed = True
            elif(excludeimputed.upper() == "N"):
                self.excludeimputed = False
            else:
                msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
                msg += _("{} value must be one of {}.").format("ExcludeImputed", " ' ', 'Y', 'N' ")
                raise MetadataConstraintError(msg)
        else:
            self.excludeimputed = None

        # Currently gives value None if field is empty or whitespace
        if excludeoutliers is not None and excludeoutliers != " ":
            if(excludeoutliers.upper() == "Y"):
                self.excludeoutliers = True
            elif(excludeoutliers.upper() == "N"):
                self.excludeoutliers = False
            else:
                msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
                msg += _("{} value must be one of {}.").format("ExcludeOutliers", " ' ', 'Y', 'N' ")
                raise MetadataConstraintError(msg)
        else:
            self.excludeoutliers = None

        # Field is mandatory and when used in generateEstimator.sas,
        # only checked for Y value, therefore default is False
        if randomerror is not None and randomerror != " ":
            if(randomerror.upper() == "Y"):
                self.randomerror = True
            elif(randomerror.upper() == "N"):
                self.randomerror = False
            else:
                msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
                msg += _("{} value must be one of {}.").format("RandomError", " ' ', 'Y', 'N' ")
                raise MetadataConstraintError(msg)
        else:
            self.randomerror = False

        self.countcriteria = None if countcriteria is None else int(countcriteria)
        #constraint invalidCountCriteria
        if ((self.countcriteria is not None) and (self.countcriteria <= 0)):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be greater than {}.").format("CountCriteria","0")
            raise MetadataConstraintError(msg)

        self.percentcriteria = None if percentcriteria is None else float(percentcriteria)
        #constraint invalidPercentCriteria
        if ((self.percentcriteria is not None) and (self.percentcriteria <= 0 or self.percentcriteria >= 100)):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("PercentCriteria value must be greater than 0 and less than 100.")
            raise MetadataConstraintError(msg)

        # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO  banff.{self.__class__.__name__} VALUES (?, ?, ?, ?, ?, ?, ?, ?,?, ?, ?, ?, ?, ?)" # noqa: S608
        dbconn.execute(statement,[self.estimatorid, self.seqno, self.fieldid, self.auxvariables,
                                  self.weightvariable, self.variancevariable, self.varianceexponent, self.varianceperiod,
                                  self.excludeimputed, self.excludeoutliers, self.countcriteria, self.percentcriteria,
                                  self.randomerror, self.algorithmname])

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Create duckdb table to store the metadata."""
        cls.setup(dbconn=dbconn)

        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            estimatorid VARCHAR NOT NULL,
            seqno INT NOT NULL,
            fieldid VARCHAR NOT NULL,
            auxvariables VARCHAR,
            weightvariable VARCHAR,
            variancevariable VARCHAR,
            varianceexponent Real,
            varianceperiod VARCHAR,
            excludeimputed BOOLEAN,
            excludeoutliers BOOLEAN,
            countcriteria  INT,
            percentcriteria REAL,
            randomerror BOOLEAN,
            algorithmname VARCHAR NOT NULL,
            PRIMARY KEY (estimatorid, seqno)
            )
        """
        dbconn.execute(create_statement)

    def to_dict(self) -> dict[str, str | int | float]:
        """Return the object as a dictionary.

        Used for creating a Dataframe from the object. Explicitly makes all fields values reflect their type, if no value was provided.
        This way there is no possiblity of an incorrect datatype (character seen as numeric or vice versa) for any empty fields when the
        constructed dataframe is passed to the Banff package c-code.
        """
        return {
            "estimatorid": self.estimatorid if self.estimatorid else "",
            "seqno": self.seqno if self.seqno is not None else np.nan,
            "fieldid": self.fieldid if self.fieldid else "",
            "algorithmname": self.algorithmname if self.algorithmname else "",
            "randomerror": "Y" if self.randomerror else "N",
            "auxvariables": self.auxvariables if self.auxvariables else "",
            "weightvariable": self.weightvariable if self.weightvariable else "",
            "variancevariable": self.variancevariable if self.variancevariable else "",
            "varianceexponent": self.varianceexponent if self.varianceexponent is not None else np.nan,
            "varianceperiod": self.varianceperiod if self.varianceperiod else "",
            # Neither excludeimputed or excludeoutliers are used by the SAS processor at all strangely
            "excludeimputed": "Y" if self.excludeimputed else (" " if self.excludeimputed is None else "N"),
            "excludeoutliers": "Y" if self.excludeoutliers else (" " if self.excludeoutliers is None else "N"),
            "countcriteria": self.countcriteria if self.countcriteria is not None else np.nan,
            "percentcriteria": self.percentcriteria if self.percentcriteria is not None else np.nan,
        }


    @staticmethod
    def get_schema(root_element_name: str = "banffProcessor") -> str:
        """Return schema (XSD) contents as a string."""
        return f"""<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
<xs:element name="{root_element_name}">
<xs:complexType>
<xs:sequence>
<xs:element name="estimators" maxOccurs="5000" minOccurs="0">
<xs:complexType>

<xs:all>
<xs:element name="estimatorid">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="seqno">
<xs:simpleType>
<xs:restriction base="xs:positiveInteger"></xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="fieldid">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="{MetadataClass.DATA_FIELD_SCHEMA_MAX_LENGTH}"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="auxvariables" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="1000"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="weightvariable" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="0"/>
<xs:maxLength value="{MetadataClass.DATA_FIELD_SCHEMA_MAX_LENGTH}"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="variancevariable" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="0"/>
<xs:maxLength value="{MetadataClass.DATA_FIELD_SCHEMA_MAX_LENGTH}"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="varianceexponent" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:float"></xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="varianceperiod" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:enumeration value="C"/>
<xs:enumeration value="c"/>
<xs:enumeration value="H"/>
<xs:enumeration value="h"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="excludeimputed" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:enumeration value="Y"/>
<xs:enumeration value="N"/>
<xs:enumeration value="y"/>
<xs:enumeration value="n"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="excludeoutliers" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:enumeration value="Y"/>
<xs:enumeration value="N"/>
<xs:enumeration value="y"/>
<xs:enumeration value="n"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="countcriteria" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:integer">
<xs:minExclusive value="0"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="percentcriteria" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:float">
<xs:minExclusive value="0"/>
<xs:maxExclusive value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="randomerror">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:enumeration value="Y"/>
<xs:enumeration value="N"/>
<xs:enumeration value="y"/>
<xs:enumeration value="n"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="algorithmname">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
</xs:all>

</xs:complexType>
</xs:element>
</xs:sequence>
</xs:complexType>
</xs:element>
</xs:schema>"""
