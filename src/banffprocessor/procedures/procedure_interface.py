from typing import Protocol

from banffprocessor.processor_data import ProcessorData


class ProcedureInterface(Protocol):
    """An Interface class for custom User Defined Procedures to implement in order to be used in a Banff Job."""

    @classmethod
    def execute(cls, processor_data: ProcessorData) -> int:
        """Perform the work in a procedure call (i.e. forms a banff call and executes it) and return
        the return code (0 for success and no errors, any non-0 value means one or more errors occured).
        """
        ...
