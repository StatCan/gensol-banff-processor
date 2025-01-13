"""Metadata model for Weights."""

import duckdb

from banffprocessor.metadata.models.metadataclass import MetadataClass


class Weights(MetadataClass):
    """Metadata class for defining the weights of variables."""

    def __init__(self, weightid: str, fieldid: str, weight: float,
                 dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Validate and create metadata entry, if validation passes."""
        self.weightid = weightid
        self.fieldid = fieldid

        self.weight = float(weight)
        self.weight_string = f"{self.fieldid}={self.weight};"

        # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO  banff.{self.__class__.__name__} VALUES (?, ?, ?)" # noqa: S608
        dbconn.execute(statement,[self.weightid, self.fieldid, self.weight])

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Create duckdb table to store the metadata."""
        cls.setup(dbconn=dbconn)

        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            weightid VARCHAR,
            fieldid  VARCHAR NOT NULL,
            weight   REAL   CHECK(weight > 0),
            PRIMARY KEY (weightid, fieldid)
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
<xs:element name="weights" maxOccurs="1000" minOccurs="0">
<xs:complexType>

<xs:all>
<xs:element name="weightid">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="100"/>
</xs:restriction>
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
<xs:element name="weight">
<xs:simpleType>
<xs:restriction base="xs:float">
<xs:minExclusive value="0"/>
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
