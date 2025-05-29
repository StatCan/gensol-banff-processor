"""Metadata model for Process Controls."""

from enum import Enum

import duckdb

from banffprocessor.exceptions import MetadataConstraintError
from banffprocessor.metadata.models.metadataclass import MetadataClass
from banffprocessor.nls import _
from banffprocessor.util.case_insensitive_enum_meta import CaseInsensitiveEnumMeta


class ProcessControls(MetadataClass):
    """Metadata class for defining process control specifications."""

    def __init__(self, controlid: str, parameter: str, value: str | None = None,
                 targetfile: str | None = None, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Validate and create metadata entry, if validation passes."""
        self.controlid = controlid

        msg = _("ProcessControl record with controlid {} ").format(controlid)

        try:
            self.parameter = ProcessControlType[parameter]
        except KeyError as e:
            msg += _("has unrecognized parameter value {}.").format(controlid, parameter)
            raise MetadataConstraintError(msg) from e

        if(self.parameter is ProcessControlType.EDIT_GROUP_FILTER):
            if(value or targetfile):
                msg += _(" is an EDIT_GROUP_FILTER control and therefore requires empty value and targetfile fields.")
                raise MetadataConstraintError(msg)
            self.value = ["FTI", "FTE"]
            self.targetfile = "instatus"
        else:
            if(not value or not targetfile):
                msg += _("is missing a value for required fields 'value' and/or 'targetfile'").format(controlid)
                raise MetadataConstraintError(msg)

            if(";" in value):
                # Make sure our query string does not contain any characters that could allow injection
                msg += _("may not contain any ';' characters in the value field.")
                raise MetadataConstraintError(msg)

            self.targetfile = targetfile.casefold()
            if(self.parameter is ProcessControlType.ROW_FILTER):
                # We take this in the case it is given. Table names we would want
                # lower-case but column names could be anything. If this was
                # parameterized more we could be ore granular but without it
                # we have to expect/tell users to use original case for columns and
                # lower case for table names
                self.value = value
            elif(self.parameter is ProcessControlType.COLUMN_FILTER):
                self.value = [x.strip() for x in value.split(",")]
            else:
                self.value = bool(value.strip().upper() in ("TRUE", "Y", "YES"))

        # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO  banff.{self.__class__.__name__} VALUES (?, ?, ?, ?)" # noqa: S608
        dbconn.execute(statement,[self.controlid, self.parameter.name, self.targetfile, self.value])

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Create duckdb table to store the metadata."""
        cls.setup(dbconn=dbconn)

        # Only value must be unique between the same controlid, parameter and targetfile
        # thus our key is made up of all 4 fields.
        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            controlid VARCHAR,
            parameter VARCHAR,
            targetfile VARCHAR,
            value VARCHAR,
            PRIMARY KEY(controlid, parameter, targetfile, value)
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
<xs:element name="processcontrols" maxOccurs="5000" minOccurs="0">
<xs:complexType>

<xs:all>
<xs:element name="controlid">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="targetfile" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="128"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="parameter">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:enumeration value="column_filter"/>
<xs:enumeration value="exclude_rejected"/>
<xs:enumeration value="row_filter"/>
<xs:enumeration value="edit_group_filter"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="value" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="6000"/>
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


class ProcessControlType(Enum, metaclass=CaseInsensitiveEnumMeta):
    """Define process control type.

    Ordering of these enum values could be used to dictate order of operations
    but is not currently used as all current control types are applied simultaneously.
    """

    ROW_FILTER = 1
    COLUMN_FILTER = 2
    EXCLUDE_REJECTED = 3
    EDIT_GROUP_FILTER = 4
