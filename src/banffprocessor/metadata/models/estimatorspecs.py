"""Metadata model for Estimator specifications."""

import duckdb

from banffprocessor.metadata.models.metadataclass import MetadataClass


class Estimatorspecs(MetadataClass):
    """Metadata class for Estimator specifications."""

    def __init__(self, specid: str, estimatorid: str, dataexclvar: str | None = None,
                 histexclvar: str | None = None, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Validate and create metadata entry, if validation passes."""
        self.specid = specid
        self.estimatorid = estimatorid
        self.dataexclvar = dataexclvar
        self.histexclvar = histexclvar

         # Note that the order of attributes must match the order in the create statement
        statement = f"INSERT INTO  banff.{self.__class__.__name__} VALUES (?, ?, ?, ?)" # noqa: S608
        dbconn.execute(statement,[self.specid, self.dataexclvar, self.histexclvar, self.estimatorid])

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection = duckdb)-> None:
        """Create duckdb table to store the metadata."""
        cls.setup(dbconn=dbconn)

        create_statement =  f"""CREATE TABLE banff.{cls.__name__} (
            specid      VARCHAR PRIMARY KEY,
            dataexclvar VARCHAR,
            histexclvar VARCHAR,
            Estimatorid VARCHAR NOT NULL
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
<xs:element name="estimatorspecs" maxOccurs="5000" minOccurs="0">
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
<xs:element minOccurs="0" name="dataexclvar" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element minOccurs="0" name="histexclvar" nillable="true">
<xs:simpleType>
<xs:restriction base="xs:string">
<xs:minLength value="1"/>
<xs:maxLength value="100"/>
</xs:restriction>
</xs:simpleType>
</xs:element>
<xs:element name="estimatorid">
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
        """Check constaints after all metadata has been loaded (typically foreign key constraints)."""
        table_name = cls.__name__

        forniegn_keys = [["dataexclvar", "Expressions", "expressionid"],
                         ["histexclvar", "Expressions", "expressionid"]]

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
