"""Metadata model for Varlists."""

import duckdb

from banffprocessor.metadata.models.metadataclass import MetadataClass


class Varlists(MetadataClass):
    """Metadata class for defining variable lists."""

    def __init__(self, varlistid: str, seqno: float, fieldid: str,
                 dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Validate and create metadata entry, if validation passes."""
        self.varlistid = varlistid
        self.seqno = float(seqno)

        # createRelationalTables.sas L316 checks for fieldid's validity
        # as a SAS field name. Probably unecessary here.
        self.fieldid = fieldid

        # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO  banff.{self.__class__.__name__} VALUES (?, ?, ?)" # noqa: S608
        dbconn.execute(statement,[self.varlistid, self.seqno, self.fieldid])

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection = duckdb)-> None:
        """Create duckdb table to store the metadata."""
        cls.setup(dbconn=dbconn)

        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            varlistid VARCHAR NOT NULL,
            seqno REAL NOT NULL,
            fieldid VARCHAR NOT NULL,
            PRIMARY KEY(varlistid, seqno)
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
<xs:element name="varlists" maxOccurs="10000" minOccurs="0">
<xs:complexType>

<xs:all>
<xs:element name="varlistid">
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
</xs:all>

</xs:complexType>
</xs:element>
</xs:sequence>
</xs:complexType>
</xs:element>
</xs:schema>"""
