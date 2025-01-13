"""Metadata model for Errorloc Specifiations."""

import duckdb

from banffprocessor.exceptions import MetadataConstraintError
from banffprocessor.metadata.models.metadataclass import MetadataClass
from banffprocessor.nls import _


class Errorlocspecs(MetadataClass):
    """Metadata class for ErrorLoc specifications."""

    def __init__(self, specid :str, cardinality: float | None =None, timeperobs: float | None =None,
                 weightid :str | None = None, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Validate and create metadata entry, if validation passes."""
        self.specid = specid
        self.cardinality = None if cardinality is None else float(cardinality)

        #constraint invalidCardinality
        if(self.cardinality is not None) and (self.cardinality <= 0):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be greater than {}.").format("Cardinality", "0")
            raise MetadataConstraintError(msg)

        self.timeperobs = None if timeperobs is None else float(timeperobs)
        #constraint invalidTimeperObs
        if(self.timeperobs is not None) and (self.timeperobs <= 0):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be greater than {}.").format("TimeperObs", "0")
            raise MetadataConstraintError(msg)

        self.weightid = weightid

        # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO  banff.{self.__class__.__name__} VALUES (?, ?, ?, ?)" # noqa: S608
        dbconn.execute(statement,[self.specid, self.cardinality, self.timeperobs, self.weightid])

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection = duckdb)-> None:
        """Create duckdb table to store the metadata."""
        cls.setup(dbconn=dbconn)

        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            specid VARCHAR PRIMARY KEY,
            cardinality REAL,
            timeperobs REAL,
            weightid VARCHAR
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
<xs:element name="errorlocspecs" maxOccurs="1000" minOccurs="0">
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
<xs:element minOccurs="0" name="cardinality" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:float">
<xs:minExclusive value="0"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="timeperobs" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:float">
<xs:minExclusive value="0"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="weightid" nillable="true">
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

    @classmethod
    def check_constraints(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Check constaints after all metadata has been loaded (typically foreign key constraints)."""
        var_name = "weightid"
        table1 = cls.__name__
        table2 = "Weights"
        undefined_values = dbconn.sql(f"""select distinct {var_name} from banff.{table1}
                                        where {var_name} is not NULL and {var_name} not in (select {var_name} from banff.{table2})
                                        limit 5
                                        """) # noqa: S608
        if undefined_values.shape[0] > 0:
            values_not_found = ", ".join(undefined_values.to_df()[var_name])
            cls.handle_foreign_key_violation(table1, var_name, table2, var_name, values_not_found)
