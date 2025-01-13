"""Metadata model for Expressions."""

import duckdb

from banffprocessor.metadata.models.metadataclass import MetadataClass
from banffprocessor.nls import _


class Expressions(MetadataClass):
    """Metadata class for expressions."""

    def __init__(self, expressionid: str, expressions: str, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Validate and create metadata entry, if validation passes."""
        self.expressionid = expressionid
        self.expressions = expressions

        # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO  banff.{self.__class__.__name__} VALUES (?, ?)" # noqa: S608
        dbconn.execute(statement,[self.expressionid, self.expressions])

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Create duckdb table to store the metadata."""
        cls.setup(dbconn=dbconn)

        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            expressionid VARCHAR PRIMARY KEY,
            expressions VARCHAR NOT NULL);
        """
        dbconn.execute(create_statement)

    @staticmethod
    def get_expression(expression_id: str, dbconn: duckdb.DuckDBPyConnection = duckdb) -> str:
        """Return the expression as a string for the given id."""
        if(not expression_id):
            return None

        select_statement =  "select expressions from banff.expressions where expressionid = ?"
        result = dbconn.execute(select_statement,[expression_id]).fetchone()
        if result is None:
            # If is key is provided and not found, we should return an error.
            msg = _("The following value was not found: {} = '{}'.").format("expressions.expressionid", expression_id)
            raise ValueError(msg)
        return result[0]

    @staticmethod
    def get_schema(root_element_name: str = "banffProcessor") -> str:
        """Return schema (XSD) contents as a string."""
        return f"""<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
<xs:element name="{root_element_name}">
<xs:complexType>
<xs:sequence>
<xs:element name="expressions" maxOccurs="1000" minOccurs="0">
<xs:complexType>

<xs:all>
<xs:element name="expressionid">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="expressions">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="5000"/>
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
