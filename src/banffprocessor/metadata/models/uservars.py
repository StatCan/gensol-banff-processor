"""Metadata model for user-defined variables."""

import duckdb

from banffprocessor.metadata.models.metadataclass import MetadataClass


class Uservars(MetadataClass):
    """User-defined variables metadata class."""

    def __init__(self, process: str, specid: str, var: str, value: str,
                 dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Validate and create metadata entry, if validation passes."""
        self.process = process.casefold()
        self.specid = specid
        self.var = var
        self.value = value # Always store value as a string, leave it up to user to convert

        # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO  banff.{self.__class__.__name__} VALUES (?, ?, ?, ?)" # noqa: S608

        dbconn.execute(statement,[self.process, self.specid, self.var, self.value])

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Create duckdb table to store the metadata."""
        dbconn.execute(f"DROP TABLE IF EXISTS banff.{cls.__name__}")
        dbconn.execute("CREATE SCHEMA IF NOT EXISTS banff;")

        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            process VARCHAR NOT NULL,
            specid VARCHAR NOT NULL,
            var VARCHAR NOT NULL,
            value VARCHAR NOT NULL,
            PRIMARY KEY(process, specid, var)
            )
        """
        dbconn.execute(create_statement)

    @staticmethod
    def uservars_to_dict(specid: str, process: str, dbconn: duckdb.DuckDBPyConnection) -> dict[str,str]:
        """Return the user variables for the given specid as a dictionary."""
        select_statement =  "select var, value from banff.uservars where specid = ? and process = ?"
        return dict(dbconn.execute(select_statement,[specid, process]).fetchall())

    @staticmethod
    def get_schema(root_element_name: str = "banffProcessor") -> str:
        """Return schema (XSD) contents as a string."""
        return f"""<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
<xs:element name="{root_element_name}">
<xs:complexType>
<xs:sequence>
<xs:element name="uservars" maxOccurs="5000" minOccurs="0">
<xs:complexType>

<xs:all>
<xs:element name="process">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="specid">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="var">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="128"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="value" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="20000"/>
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
