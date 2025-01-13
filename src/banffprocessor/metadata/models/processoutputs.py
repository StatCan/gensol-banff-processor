"""Metadata model for ProcessOutputs."""

import duckdb

from banffprocessor.metadata.models.metadataclass import MetadataClass


class ProcessOutputs(MetadataClass):
    """Allow the user to define which additional outputs they would like for each process type."""

    def __init__(self, process: str, output_name: str, dbconn: duckdb.DuckDBPyConnection=duckdb) -> None:
        """Validate and create metadata entry, if validation passes."""
        self.process = process.casefold()
        self.output_name = output_name.casefold()

        # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO banff.{self.__class__.__name__} VALUES (?, ?)" # noqa: S608
        dbconn.execute(statement,[self.process, self.output_name])

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection=duckdb) -> None:
        """Initialize metadata model.

        An empty metadata table is created to load the metadata into.
        """
        cls.setup(dbconn=dbconn)

        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            process VARCHAR NOT NULL,
            output_name VARCHAR NOT NULL,
            PRIMARY KEY (process, output_name)
            )
        """
        dbconn.execute(create_statement)

    @staticmethod
    def get_schema(root_element_name: str = "banffProcessor") -> str:
        """Return the XSD for the metadata model as a string."""
        return f"""
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
<xs:element name="{root_element_name}">
<xs:complexType>
<xs:sequence>
<xs:element name="processoutputs" maxOccurs="5000" minOccurs="1">
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
<xs:element name="output_name">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="128"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
</xs:all>

</xs:complexType>
</xs:element>
</xs:sequence>
</xs:complexType>
</xs:element>
</xs:schema>
"""
