"""Metadata model for defining edit groups."""

import duckdb

from banffprocessor.exceptions import MetadataConstraintError
from banffprocessor.metadata.models.metadataclass import MetadataClass
from banffprocessor.nls import _


class Editgroups(MetadataClass):
    """Metadata class for defining edit groups."""

    def __init__(self, editgroupid: str, editid: str, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Validate and create metadata entry, if validation passes."""
        self.editgroupid = editgroupid
        self.editid = editid

        # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO  banff.{self.__class__.__name__} VALUES (?, ?)" # noqa: S608
        dbconn.execute(statement,[self.editgroupid, self.editid])

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection = duckdb)-> None:
        """Create duckdb table to store the metadata."""
        cls.setup(dbconn=dbconn)

        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            editgroupid VARCHAR,
            editid VARCHAR,
            PRIMARY KEY(editgroupid, editid)
            );
        """
        dbconn.execute(create_statement)

    @staticmethod
    def get_schema(root_element_name: str = "banffProcessor") -> str:
        """Return schema (XSD) contents as a string."""
        return f"""<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
<xs:element name="{root_element_name}">
<xs:complexType>
<xs:sequence>
<xs:element name="editgroups" maxOccurs="5000" minOccurs="0">
<xs:complexType>

<xs:all>
<xs:element name="editgroupid">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="editid">
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
        """All edits defined in an edit group must exist."""
        select_statement =  """select editgroupid, editid from banff.Editgroups
        where editid not in (select editid from banff.Edits) limit 5"""
        violations_df = dbconn.execute(select_statement).fetch_df()
        if len(violations_df) > 0:
            msg = _("The following Edits belonging to an EditGroup are not defined: \n {}").format(violations_df)
            raise MetadataConstraintError(msg)
