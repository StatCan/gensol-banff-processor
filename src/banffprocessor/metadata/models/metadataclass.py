"""Abstract Class for Banff Processor Metadata models."""

from io import StringIO

import duckdb
import xmlschema
from defusedxml.ElementTree import parse

from banffprocessor.exceptions import MetadataConstraintError
from banffprocessor.nls import _


class MetadataClass:
    """Banff Processor Metadata Class.

    Abstract class definition for all metadata classes to extend,
    to allow for easier type hinting without needing to explicitly
    write out all class names and it reduces replicated code
    """

    DATA_FIELD_SCHEMA_MAX_LENGTH: str = "64"

    @staticmethod
    def get_schema(root_element_name: str = "banffProcessor") -> str:
        """Return a string that contains the XML Schema Definition for the classes metadata.

        By default the root element will be banffProcessor, but this may be changed as some
        XML generators use a standard root, like 'root' or 'data'.
        """

    @classmethod
    def get_record_count(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> int:
        """Return the number of records in the metadata table."""
        select_statement =  f"select count(*) from banff.{cls.__name__}" # noqa: S608
        return dbconn.execute(select_statement).fetchone()[0]

    @classmethod
    def load_xml(cls, xml_file_name: str) -> None:
        """Attempt to load the given XML file.

        The xml file is attempted to be loaded in the banff processor metadata
        based on the XMLschema.
        """
        try:
            xml_tree = parse(xml_file_name)
            root_element_name = xml_tree.getroot().tag
            my_schema = xmlschema.XMLSchema(StringIO(cls.get_schema(root_element_name=root_element_name)))
            my_schema.validate(xml_tree)
            return my_schema.to_dict(xml_tree)
        except xmlschema.validators.exceptions.XMLSchemaValidationError as e:
            msg = _("XML Issue detected related to {}: {}").format(e.path, e.reason)
            raise MetadataConstraintError(msg) from None

    @classmethod
    def initialize(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Perform any initialization before loading metadata.

        This is typically creating the database table to store the metadata in.
        """

    @classmethod
    def setup(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Perform setup.

        This is called by sub-classes to ensure the the standard setup is performed during
        the initialization process.
        """
        # Calling cleanup just in case the table still exists from a previous run
        cls.cleanup(dbconn=duckdb)

        # Creating the Banff schema, if it doesn't already exist
        dbconn.execute("CREATE SCHEMA IF NOT EXISTS banff;")

    @classmethod
    def cleanup(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Cleanup metadata in the given database.

        The metadata table will be deleted if the connection is still open
        and the table exists. If the database is not open, the connection
        object will have no default_connection attribute.
        """
        if (hasattr(dbconn, "default_connection")):
            dbconn.execute(f"DROP TABLE IF EXISTS banff.{cls.__name__}")

    @classmethod
    def check_constraints(cls, dbconn: duckdb.DuckDBPyConnection = duckdb) -> None:
        """Constraints to check after all metadata has been loaded.

        Subclasses may implement a set of checks, if necessary. If a constraint fails,
        an exception is raised.
        """

    @staticmethod
    def handle_foreign_key_violation(table1_name :str, table1_column :str,
                                     table2_name :str, table2_column :str,
                                     values_not_found: str) -> None:
        """Handle foreign key violations.

        When a relationship error is detected, a MetadataConstraintError exception is raised.
        """
        msg = _("Constraint violated in {} table: ").format(table1_name)
        msg += _("Foreign key constraint violation between {}.{} and {}.{}. ").format(table1_name, table1_column, table2_name, table2_column)
        msg += _("The following are not defined: {}.").format(values_not_found)
        raise MetadataConstraintError(msg)
