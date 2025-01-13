"""Metadata model for user-defined estimator algorithms."""

import duckdb

from banffprocessor.exceptions import MetadataConstraintError
from banffprocessor.metadata.models import estimators
from banffprocessor.metadata.models.metadataclass import MetadataClass
from banffprocessor.nls import _


class Algorithms(MetadataClass):
    """Metadata class for user-defined algorithms which define estimators."""

    def __init__(self, algorithmname: str, status: str, formula: str,
                 type: str, description: str | None = None,
                 dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Validate and create metadata entry, if validation passes."""
        self.algorithmname = algorithmname

        self.type = type.upper()
        #constraint invalidType
        # a little confusing, createRelationalTables.sas has type as NOT NULL
        # but allows empty values in constraint
        if(self.type is not None and self.type not in {"EF", "LR"}):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} value must be one of {}.").format("Algorithm", " 'EF', 'LR' ")
            raise MetadataConstraintError(msg)

        if (self.algorithmname in estimators.builtin_estimators()):
            msg = _("Constraint violated in {} table: ").format(self.__class__.__name__)
            msg += _("{} is a built-in algorithm and cannot be re-defined.").format(self.algorithmname)
            raise MetadataConstraintError(msg)

        self.status = status
        self.formula = str(formula) if formula else None
        self.description = description

         # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO  banff.{self.__class__.__name__} VALUES (?, ?, ?, ?, ?)" # noqa: S608
        dbconn.execute(statement,[self.algorithmname, self.type, self.status, self.formula, self.description])

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Create duckdb table to store the metadata."""
        cls.setup(dbconn=dbconn)

        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            algorithmname VARCHAR PRIMARY KEY,
            type VARCHAR NOT NULL,
            status VARCHAR,
            formula VARCHAR,
            description VARCHAR
            )
        """
        dbconn.execute(create_statement)

    # Used for creating a Dataframe from the object. Explicitly makes all fields values
    # reflect their type, if no value was provided. This way there is no possiblity of
    # an incorrect datatype (character seen as numeric or vice versa) for any empty fields
    # when the constructed dataframe is passed to the Banff package c-code.
    def to_dict(self) -> dict[str, str]:
        """Return the algormithm metadata as a dictionary."""
        return {
            "algorithmname": self.algorithmname if self.algorithmname else "",
            "status": self.status if self.status else "",
            "formula": str(self.formula) if self.formula is not None else "",
            "type": self.type if self.type else "",
            "description": self.description if self.description else "",
        }

    @staticmethod
    def get_schema(root_element_name: str = "banffProcessor") -> str:
        """Return schema (XSD) contents as a string."""
        return f"""<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
<xs:element name="{root_element_name}">
<xs:complexType>
<xs:sequence>
<xs:element name="algorithms" maxOccurs="1000" minOccurs="0">
<xs:complexType>

<xs:all>
<xs:element name="algorithmname">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="type">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:enumeration value="EF"/>
<xs:enumeration value="ef"/>
<xs:enumeration value="LR"/>
<xs:enumeration value="lr"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="status">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="3"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="formula">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="5000"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="description" nillable="true">
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
