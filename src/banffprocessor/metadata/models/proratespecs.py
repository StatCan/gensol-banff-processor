"""Metadata model for Prorate specifications."""

import duckdb

from banffprocessor.metadata.models.metadataclass import MetadataClass


class Proratespecs(MetadataClass):
    """Metadata class for prorate imputation specifications."""

    def __init__(self, specid: str, decimal: int | None =None, lowerbound: float | None =None,
                 upperbound: float | None =None, modifier: str | None = None,
                 method: str | None = None, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Initialize metadata entry."""
        self.specid = specid
        self.decimal = None if decimal is None else int(decimal)
        self.lowerbound = None if lowerbound is None else float(lowerbound)
        self.upperbound = None if upperbound is None else float(upperbound)
        self.modifier = modifier
        self.method = method

        # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO  banff.{self.__class__.__name__} VALUES (?, ?, ?, ?, ?, ?)" # noqa: S608
        dbconn.execute(statement,[self.specid, self.decimal, self.lowerbound, self.upperbound, self.modifier, self.method])

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Create duckdb table to store the metadata."""
        cls.setup(dbconn=dbconn)

        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            specid VARCHAR PRIMARY KEY,
            decimal INT,
            lowerbound REAL,
            upperbound REAL,
            modifier VARCHAR,
            method VARCHAR
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
<xs:element name="proratespecs" maxOccurs="5000" minOccurs="0">
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
<xs:element minOccurs="0" name="decimal" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:integer">
<xs:minInclusive value="0"/>
<xs:maxInclusive value="9"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="lowerbound" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:float"></xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="upperbound" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:float"></xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="modifier">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="8"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="method">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="7"/>
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
