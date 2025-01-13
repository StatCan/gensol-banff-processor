"""Metadata model for Outlier specifications."""

from typing import ClassVar

import duckdb

from banffprocessor.exceptions import MetadataConstraintError
from banffprocessor.metadata.models.metadataclass import MetadataClass
from banffprocessor.nls import _


class Outlierspecs(MetadataClass):
    """Metadata class for donor imputation specifications."""

    methods: ClassVar[dict[str, str]] = {
        "H": "HISTORIC",
        "R": "RATIO",
        "S": "SIGMAGAP",
        "C": "CURRENT",
    }

    invalid_min_obs: int = 3

    def __init__(self, specid: str, method: str, varid: str | None =None, minobs: int | None =None,
                 side: str | None = None, withid: str | None = None, mii: float | None =None,
                 mei: float | None =None, mdm: float | None =None, exponent: float | None =None,
                 sigma: str | None =None, betai: float | None =None, betae: float | None =None,
                 startcentile: float | None =None, acceptzero: bool | None =None, weight: str | None =None,
                 dataexclvar: str | None = None, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Validate and create metadata entry, if validation passes."""
        self.specid = specid

        try:
            self.method = self.methods[method[0].upper()]
        except KeyError as e:
            # custom constraint not originally from SAS program
            #constraint outlierMethod
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be one of {}.").format("Method", self.methods.keys() )
            raise MetadataConstraintError(msg) from e
        # e.g. 'HISTORIC - two data sets'
        self.numDataSets = 2 if "TWO" in method.upper() else 1

        self.varid = varid
        self.withid = withid
        self.weight = weight
        self.dataexclvar = dataexclvar

        # Currently gives value None if field is empty or whitespace
        if acceptzero is not None and acceptzero != " ":
            if(acceptzero.upper() == "Y"):
                self.acceptzero = True
            elif(acceptzero.upper() == "N"):
                self.acceptzero = False
            else:
                msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
                msg += _("{} value must be one of {}.").format("AcceptZero", " ' ', 'Y', 'N' ")
                raise MetadataConstraintError(msg)
        else:
            self.acceptzero = None

        self.minobs = None if minobs is None else int(minobs)
        #constraint invalidMinobs
        if(self.minobs is not None) and (self.minobs < self.invalid_min_obs):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be greater than or equal to {}.").format("MinObs", "3")
            raise MetadataConstraintError(msg)

        self.side = side
        #constraint invalidSide
        if(self.side is not None) and (self.side.upper() not in {" ", "LEFT", "RIGHT", "BOTH"}):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be one of {}.").format("side", " ' ', 'LEFT', 'RIGHT', 'BOTH' ")
            raise MetadataConstraintError(msg)

        self.mii = None if mii is None else float(mii)
        #constraint invalidMII
        if(self.mii is not None) and (self.mii <= 0):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be greater than {}.").format("MII", "0")
            raise MetadataConstraintError(msg)

        self.mei = None if mei is None else float(mei)
        #constraint invalidMEI
        if(self.mei is not None) and (self.mei <= 0):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be greater than {}.").format("MEI", "0")
            raise MetadataConstraintError(msg)

        self.mdm = None if mdm is None else float(mdm)
        #constraint invalidmdm
        if(self.mdm is not None) and (self.mdm < 0):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be greater than {}.").format("MDM", "0")
            raise MetadataConstraintError(msg)

        self.exponent = None if exponent is None else float(exponent)
        #constraint invalidExponent
        if(self.exponent is not None) and (self.exponent < 0 or self.exponent > 1):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("Exponent value must be between 0 and 1 inclusive.")
            raise MetadataConstraintError(msg)

        self.sigma = sigma
        #constraint invalidSigma
        if(self.sigma is not None) and (self.sigma.upper() not in {" ", "STD", "MAD"}):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be one of {}.").format("Sigma", " ' ', 'STD', 'MAD' ")
            raise MetadataConstraintError(msg)

        #one or both must be specified when using method=SIGMAGAP
        self.betai = None if betai is None else float(betai)
        #constraint invalidBetai
        if(self.betai is not None) and (self.betai <= 0):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be greater than {}.").format("BETAI", "0")
            raise MetadataConstraintError(msg)

        self.betae = None if betae is None else float(betae)
        #constraint invalidBetae
        if(self.betae is not None) and (self.betae <= 0):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be greater than {}.").format("BETAE", "0")
            raise MetadataConstraintError(msg)

        self.startcentile = None if startcentile is None else float(startcentile)
        #constraint invalidStartCentile
        if(self.startcentile is not None) and (self.startcentile < 0 or self.startcentile >= 100):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("StartCentile value must be between 0 inclusive and 100 exclusive.")
            raise MetadataConstraintError(msg)

        # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO  banff.{self.__class__.__name__} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)" # noqa: S608
        dbconn.execute(statement,[self.specid, self.method, self.mei, self.mii, self.mdm, self.exponent, self.minobs,
                                  self.varid, self.withid, self.dataexclvar, self.betae, self.betai, self.weight, self.sigma,
                                  self.side, self.startcentile, self.acceptzero])

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Create duckdb table to store the metadata."""
        cls.setup(dbconn=dbconn)

        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            specid VARCHAR PRIMARY KEY,
            method VARCHAR NOT NULL,
            mei REAL,
            mii REAL,
            mdm REAL,
            exponent REAL,
            minobs INT,
            varid VARCHAR,
            withid VARCHAR,
            dataexclvar VARCHAR,
            betae REAL,
            betai REAL,
            weight VARCHAR,
            sigma VARCHAR,
            side VARCHAR,
            startcentile REAL,
            acceptzero BOOLEAN
            )
        """
        dbconn.execute(create_statement)

    @staticmethod
    def get_schema(root_element_name: str = "banffProcessor") -> str:
        """Return schema (XSD) contents as a string."""
        return f"""<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
<xs:element name="{root_element_name}">
<xs:complexType>
<xs:sequence>
<xs:element name="outlierspecs" maxOccurs="1000" minOccurs="0">
<xs:complexType>

<xs:all>
<xs:element name="specid">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="method">
<xs:simpleType>
<xs:restriction base="xs:string">
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="mei" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:float">
<xs:minExclusive value="0"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="mii" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:float">
<xs:minExclusive value="0"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="mdm" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:float">
<xs:minInclusive value="0"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="exponent" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:float">
<xs:minInclusive value="0"/>
<xs:maxInclusive value="1"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="minobs" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:positiveInteger">
<xs:minInclusive value="3"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="varid" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="0"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="withid" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="0"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="dataexclvar" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="0"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="betae" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:float">
<xs:minExclusive value="0"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="betai" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:float">
<xs:minExclusive value="0"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="weight" minOccurs="0" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="0"/>
<xs:maxLength value="{MetadataClass.DATA_FIELD_SCHEMA_MAX_LENGTH}"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="sigma" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:enumeration value="STD"/>
<xs:enumeration value="MAD"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="side" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:enumeration value="LEFT"/>
<xs:enumeration value="RIGHT"/>
<xs:enumeration value="BOTH"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="startcentile" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:float">
<xs:minInclusive value="0"/>
<xs:maxExclusive value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="acceptzero" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:enumeration value="Y"/>
<xs:enumeration value="N"/>
<xs:enumeration value="y"/>
<xs:enumeration value="n"/>
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

    @classmethod
    def check_constraints(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Check constaints after all metadata has been loaded (typically foreign key constraints)."""
        table_name = cls.__name__

        foreign_keys = [["varid", "VarLists", "varlistid"],
                        ["dataexclvar", "Expressions", "expressionid"],
                        ["withid", "VarLists", "varlistid"]]

        for item in foreign_keys:
            var_name = item[0]
            table2_name = item[1]
            table2_var_name = item[2]
            undefined_values = dbconn.sql(f"""select distinct {var_name} from banff.{table_name}
                                        where {var_name} is not NULL and {var_name} not in (select {table2_var_name} from banff.{table2_name})
                                        limit 5
                                        """) # noqa: S608
            if undefined_values.shape[0] > 0:
                values_not_found = ", ".join(undefined_values.to_df()[var_name])
                cls.handle_foreign_key_violation(table_name, var_name, table2_name, table2_var_name, values_not_found)
