"""Metadata model for Donor Imputation specifications."""

import duckdb

from banffprocessor.exceptions import MetadataConstraintError
from banffprocessor.metadata.models.metadataclass import MetadataClass
from banffprocessor.nls import _


class Donorspecs(MetadataClass):
    """Metadata class for donor imputation specifications."""

    def __init__(self, specid: str, n: int, dataexclvar: str | None =None,
                 posteditgroupid: str | None =None, mustmatchid: str | None =None,
                 mindonors: int | None =None, pcentdonors: float | None =None,
                 eligdon: str | None =None, random: bool | None =None, nlimit: int | None =None,
                 mrl: float | None =None, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Validate and create metadata entry, if validation passes."""
        self.specid = specid
        self.mindonors = None if mindonors is None else int(mindonors)

        #constraint invalidMinDonors
        if(self.mindonors is not None) and (self.mindonors < 1):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be greater than or equal to {}.").format("MinDonors", "1")
            raise MetadataConstraintError(msg)

        self.pcentdonors = None if pcentdonors is None else float(pcentdonors)
        #constraint invalidPcentdonors
        if(self.pcentdonors is not None) and (self.pcentdonors < 1 or self.pcentdonors >= 100):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("PcentDonors value must be between 1 inclusive and 100 exclusive.")
            raise MetadataConstraintError(msg)

        self.n = int(n)
        #constraint invalidN
        if(self.n < 1):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be greater than or equal to {}.").format("N", "1")
            raise MetadataConstraintError(msg)

        self.eligdon = eligdon
        #constraint invalidEligdon
        if(self.eligdon is not None) and (self.eligdon.upper() not in {" ", "A", "ANY", "O", "ORIGINAL"}):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be one of {}.").format("Eligdon", " ' ', 'A', 'ANY', 'O', 'Original' ")
            raise MetadataConstraintError(msg)

        # Currently gives value None if field is empty or whitespace
        #constraint invalidRandom
        if random is not None and random != " ":
            if(random.upper() == "Y"):
                self.random = True
            elif(random.upper() == "N"):
                self.random = False
            else:
                msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
                msg += _("{} value must be one of {}.").format("Random", " ' ', 'Y' or 'N' ")
                raise MetadataConstraintError(msg)
        else:
            self.random = None

        self.nlimit = None if nlimit is None else int(nlimit)
        #constraint invalidNlimit
        if(self.nlimit is not None) and (self.nlimit < 1):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be greater than or equal to {}.").format("Nlimit", "1")
            raise MetadataConstraintError(msg)

        self.mrl = None if mrl is None else float(mrl)
        #constraint invalidMRL
        if(self.mrl is not None) and (self.mrl <= 0):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be greater than {}.").format("MRL","0")
            raise MetadataConstraintError(msg)

        self.mustmatchid = mustmatchid
        self.posteditgroupid = posteditgroupid
        self.dataexclvar = dataexclvar

        # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO  banff.{self.__class__.__name__} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)" # noqa: S608
        dbconn.execute(statement,[self.specid, self.mindonors, self.pcentdonors, self.n, self.eligdon,
                                  self.random, self.nlimit, self.mrl, self.dataexclvar, self.mustmatchid, self.posteditgroupid])

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection =duckdb) -> None:
        """Create duckdb table to store the metadata."""
        cls.setup(dbconn=dbconn)

        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            specid          VARCHAR PRIMARY KEY,
            mindonors       INT,
            pcentdonors     REAL,
            n               INT NOT NULL,
            eligdon         VARCHAR,
            random          BOOLEAN,
            nlimit          INT,
            mrl             REAL,
            dataexclvar     VARCHAR,
            mustmatchid     VARCHAR,
            posteditgroupid VARCHAR
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
<xs:element name="donorspecs" maxOccurs="1000" minOccurs="0">
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
<xs:element minOccurs="0" name="mindonors" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:positiveInteger">
<xs:minInclusive value="1"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="pcentdonors" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:float">
<xs:maxExclusive value="100"/>
<xs:minInclusive value="1"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="n">
<xs:simpleType>
<xs:restriction base="xs:positiveInteger">
<xs:minInclusive value="1"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="eligdon" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:enumeration value="ANY"/>
<xs:enumeration value="any"/>
<xs:enumeration value="ORIGINAL"/>
<xs:enumeration value="original"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="random" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:enumeration value="Y"/>
<xs:enumeration value="N"/>
<xs:enumeration value="y"/>
<xs:enumeration value="n"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="nlimit" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:positiveInteger">
<xs:minInclusive value="1"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="mrl" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:float">
<xs:minExclusive value="0"/>
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
<xs:element  minOccurs="0" name="mustmatchid" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="0"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="posteditgroupid" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="0"/>
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

    @classmethod
    def check_constraints(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Check constaints after all metadata has been loaded (typically foreign key constraints)."""
        table_name = cls.__name__

        forniegn_keys = [["dataexclvar", "Expressions", "expressionid"],
                         ["mustmatchid", "VarLists", "varlistid"],
                        ["posteditgroupid", "Editgroups", "editgroupid"]]

        for item in forniegn_keys:
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
