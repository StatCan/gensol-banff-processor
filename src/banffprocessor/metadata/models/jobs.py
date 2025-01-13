"""Metadata model for Jobs."""

import duckdb

from banffprocessor.exceptions import MetadataConstraintError
from banffprocessor.metadata.models.metadataclass import MetadataClass
from banffprocessor.nls import _


class Jobs(MetadataClass):
    """Metadata class for defining Jobs."""

    def __init__(self, jobid: str, seqno: float, process: str, specid: str | None = None,
                 editgroupid: str | None = None, byid: str | None = None, acceptnegative: str | None = None,
                 controlid: str | None = None, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Validate and create metadata entry, if validation passes."""
        self.jobid = jobid
        self.seqno = float(seqno)
        self.process = process.casefold()
        self.specid = specid
        self.editgroupid = editgroupid
        self.byid = byid
        self.controlid = controlid

        # Currently gives value None if field is empty or whitespace
        if acceptnegative is not None and acceptnegative != " ":
            if(acceptnegative.upper() == "Y"):
                self.acceptnegative = True
            elif(acceptnegative.upper() == "N"):
                self.acceptnegative = False
            else:
                msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
                msg += _("{} value must be one of {}.").format("AcceptNegative", " ' ', 'Y', 'N' ")
                raise MetadataConstraintError(msg)
        else:
            self.acceptnegative = None

        # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO  banff.{self.__class__.__name__} VALUES (?, ?, ?, ?, ?, ?, ?, ?)" # noqa: S608
        dbconn.execute(statement,[self.jobid, seqno, self.controlid, self.process, self.specid, self.editgroupid,
                                  self.byid, self.acceptnegative])

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Create duckdb table to store the metadata."""
        cls.setup(dbconn=dbconn)

        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            jobid VARCHAR,
            seqno REAL,
            controlid VARCHAR,
            process VARCHAR NOT NULL,
            specid VARCHAR,
            editgroupid VARCHAR,
            byid VARCHAR,
            acceptnegative BOOLEAN,
            PRIMARY KEY (jobid, seqno)
            )
        """
        dbconn.execute(create_statement)

    @staticmethod
    def get_schema(root_element_name: str = "banffProcessor") -> str:
        """Return schema (XSD) contents as a string."""
        return f"""
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
<xs:element name="{root_element_name}">
<xs:complexType>
<xs:sequence>
<xs:element name="jobs" maxOccurs="5000" minOccurs="1">
<xs:complexType>

<xs:all>
<xs:element name="jobid">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="seqno">
<xs:simpleType>
<xs:restriction base="xs:float">
<xs:minExclusive value="0"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="controlid" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="{MetadataClass.DATA_FIELD_SCHEMA_MAX_LENGTH}"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="process">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="{MetadataClass.DATA_FIELD_SCHEMA_MAX_LENGTH}"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="specid" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="editgroupid" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="byid" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="0"/>
<xs:maxLength value="{MetadataClass.DATA_FIELD_SCHEMA_MAX_LENGTH}"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="alternatebyid" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="0"/>
<xs:maxLength value="{MetadataClass.DATA_FIELD_SCHEMA_MAX_LENGTH}"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="acceptnegative" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:enumeration value="Y"/>
<xs:enumeration value="N"/>
<xs:enumeration value="y"/>
<xs:enumeration value="n"/>
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

    @classmethod
    def check_constraints(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Check constaints after all metadata has been loaded (typically foreign key constraints)."""
        table_name = cls.__name__

        forniegn_keys = [["controlid", "ProcessControls", "controlid"],
                         ["editgroupid", "EditGroups", "editgroupid"],
                         ["byid", "VarLists", "varlistid"]]

        for item in forniegn_keys:
            var_name = item[0]
            table2_name = item[1]
            table2_var_name = item[2]
            undefined_values = dbconn.sql(f"""select distinct {var_name} from banff.{table_name}
                                        where {var_name} is not NULL and {var_name} not in (select {table2_var_name} from banff.{table2_name})
                                        limit 5
                                        """) # noqa: S608
            if undefined_values.shape[0] > 0:
                values_not_found = ", ".join(undefined_values.to_df()[var_name])
                cls.handle_foreign_key_violation(table_name, var_name, table2_name, table2_var_name, values_not_found)
