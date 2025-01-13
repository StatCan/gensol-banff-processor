"""Register and unregister ProcedureInterface instances with the Banff Processor."""
from banffprocessor.nls import _
from banffprocessor.procedures.procedure_interface import ProcedureInterface

procedure_classes: dict[str, type[ProcedureInterface]] = {}

def register(procedure_name: str | list[str], cls: type[ProcedureInterface]) -> None:
    """Register plugin class `cls` under `procedure_name`.

    :param procedure_name: The name to register the procedure under
    :type procedure_name: str
    :param cls: The class reference to register
    :type cls: type[ProcedureInterface]
    """
    if(isinstance(procedure_name, str)):
        procedure_name = [procedure_name]

    for name in procedure_name:
        procedure_classes[name.casefold()] = cls

def unregister(to_remove: str) -> None:
    """Unregister the plugin class found under `procedure_name`.

    :param procedure_name: The name of the procedure to unregister
    :type procedure_name: str
    """
    procedure_classes.pop(to_remove.casefold(), None)

def get_procedure(procedure_name: str) -> type[ProcedureInterface]:
    """Get a Procedure class under a specified name.

    :param procedure_name: The name of the procedure to fetch
    :type procedure_name: str
    :raises ValueError: If `procedure_name` is not found
    :return: The class reference registered under `procedure_name`
    :rtype: type[ProcedureInterface]
    """
    try:
        cls = procedure_classes[procedure_name.casefold()]
    except KeyError:
        msg = _("Unknown Procedure name {!r}").format(procedure_name)
        raise ValueError(msg) from None

    return cls
