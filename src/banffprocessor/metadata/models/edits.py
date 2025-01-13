"""Metadata model for edits."""

import duckdb

from banffprocessor.exceptions import MetadataConstraintError
from banffprocessor.metadata.models.metadataclass import MetadataClass
from banffprocessor.nls import _


class Edits(MetadataClass):
    """Metadata class for defining edits."""

    def __init__(self, editid: str, leftside: str, rightside: str, operator: str,
                 modifier: str | None = None, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Validate and create metadata entry, if validation passes."""
        self.editid = editid
        self.leftside = leftside
        #constraint invalidLeftSide
        if(self.leftside is not None) and (self.leftside.find("'") != -1 or self.leftside.find('"') != -1):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must not contain any single or double quotes.").format("leftside")
            raise MetadataConstraintError(msg)

        self.rightside = rightside
        #constraint invalidRightSide
        if(self.rightside is not None) and (self.rightside.find("'") != -1 or self.rightside.find('"') != -1):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must not contain any single or double quotes.").format("rightside")
            raise MetadataConstraintError(msg)

        # xmltodict auto converts the html entities used by the XML tables to unicode
        # i.e. '&lt;' becomes '<', '&gt;=' becomes '>='
        # Therefore they don't need to be converted manually here, however they may
        # in the future should something change in the way the file is created
        self.operator = operator
        #constraint invalidOperator
        if(self.operator is not None) and (self.operator not in {"<", "<=", ">", ">=", "=", "!="}):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be one of {}.").format("operator", " '<', '<=', '>', '>=', '=', '!=' ")
            raise MetadataConstraintError(msg)

        self.modifier = modifier
        #constraint invalidModifier
        if(self.modifier is not None) and (self.modifier.upper() not in {"", "PASS", "FAIL", "ACCEPTE", "REJET"}):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be one of {}.").format("Modifier", " '', 'PASS', 'FAIL', 'ACCEPTE', 'REJET' ")
            raise MetadataConstraintError(msg)

        # Not in original processor, just for convenience
        if(self.modifier is None or self.modifier == ""):
            self.edit = self.leftside + " " + self.operator + " " + self.rightside + ";"
        else:
            self.edit = self.modifier + ": " + self.leftside + " " + self.operator + " " + self.rightside + ";"

        # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO  banff.{self.__class__.__name__} VALUES (?, ?, ?, ?, ?, ?)" # noqa: S608
        dbconn.execute(statement,[self.editid, self.leftside, self.operator, self.rightside, self.modifier, self.edit])


    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Create duckdb table to store the metadata."""
        cls.setup(dbconn=dbconn)

        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            editid VARCHAR PRIMARY KEY,
            leftside VARCHAR,
            operator VARCHAR,
            rightside VARCHAR,
            modifier VARCHAR,
            edit VARCHAR
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
<xs:element name="edits" maxOccurs="1000" minOccurs="0">
<xs:complexType>

<xs:all>
<xs:element name="editid">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="leftside">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="6000"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="operator">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:enumeration value="&lt;"/>
<xs:enumeration value="&lt;="/>
<xs:enumeration value=">"/>
<xs:enumeration value=">="/>
<xs:enumeration value="="/>
<xs:enumeration value="!="/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="rightside">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="1000"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="modifier" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:enumeration value="ACCEPTE"/>
<xs:enumeration value="FAIL"/>
<xs:enumeration value="PASS"/>
<xs:enumeration value="REJET"/>
<xs:enumeration value="accepte"/>
<xs:enumeration value="fail"/>
<xs:enumeration value="pass"/>
<xs:enumeration value="rejet"/>
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
