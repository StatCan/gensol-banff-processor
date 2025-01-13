"""Metadata model for VerifyEdits specifications."""

import duckdb

from banffprocessor.exceptions import MetadataConstraintError
from banffprocessor.metadata.models.metadataclass import MetadataClass
from banffprocessor.nls import _


class Verifyeditsspecs(MetadataClass):
    """Metadata class for verify edit procedure specifications."""

    def __init__(self, specid: str, imply: int | None =None, extremal: int | None =None,
                 dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Validate and create metadata entry, if validation passes."""
        self.specid = specid

        self.imply = None if imply is None else int(imply)
        #constraint invalidImply
        if(self.imply is not None) and (self.imply <= 0):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be greater than {}.").format("Imply", "0")
            raise MetadataConstraintError(msg)

        self.extremal = None if extremal is None else int(extremal)
        #constraint invalidExtremal
        if(self.extremal is not None) and (self.extremal <= 0):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be greater than {}.").format("Extremal", "0")
            raise MetadataConstraintError(msg)

        # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO  banff.{self.__class__.__name__} VALUES (?, ?, ?)" # noqa: S608
        dbconn.execute(statement,[self.specid, self.imply, self.extremal])

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Create duckdb table to store the metadata."""
        cls.setup(dbconn=dbconn)

        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            specid VARCHAR PRIMARY KEY,
            imply INT,
            extremal INT)
        """
        dbconn.execute(create_statement)

    @staticmethod
    def get_schema(root_element_name: str = "banffProcessor") -> str:
        """Return schema (XSD) contents as a string."""
        return f"""<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
<xs:element name="{root_element_name}">
<xs:complexType>
<xs:sequence>
<xs:element name="verifyeditsspecs" maxOccurs="5000" minOccurs="0">
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
<xs:element minOccurs="0" name="imply" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:positiveInteger"></xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="extremal" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:positiveInteger"></xs:restriction>
</xs:simpleType>
</xs:element>
</xs:all>

</xs:complexType>
</xs:element>
</xs:sequence>
</xs:complexType>
</xs:element>
</xs:schema>"""
