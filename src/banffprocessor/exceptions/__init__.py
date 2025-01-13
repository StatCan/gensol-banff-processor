"""Provides a number of custom exception definitions to better identify failures during the Banff Processor's execution."""

class MetadataConstraintError(Exception):
    """Identifies errors during the import of metadata when a constraint is violated by a value read in from a table."""

class ProcessorInputParameterError(Exception):
    """Identifies errors in or from parameters supplied in the input parameter file or directly when creating or using the object."""

class EmptyMetadataFileError(Exception):
    """Identifies that required data is missing from a metadata file."""

class BanffPackageExecutionError(Exception):
    """Identifies an error that was experienced during the execution of a banff proc."""

class ProcedureReturnCodeError(Exception):
    """Identifies a non-zero return code from a built-in or user-defined procedure, indicating an error occured during execution."""

class UserDefinedPluginError(Exception):
    """Identifies an error in a User Defined Plugin caused by the user's code."""

class ProcessControlError(Exception):
    """Identifies an error stemming from the application of a Process Control."""
