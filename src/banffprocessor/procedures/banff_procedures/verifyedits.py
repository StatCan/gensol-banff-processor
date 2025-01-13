import banff.exceptions
from banff import verifyed
from banff._log import log_levels

# Import must be absolute in order to ensure all modules reference the same global _c_handlers
import banffprocessor.processor_logger as plg
from banffprocessor.exceptions import BanffPackageExecutionError
from banffprocessor.metadata.models.verifyeditsspecs import Verifyeditsspecs
from banffprocessor.nls import _
from banffprocessor.procedures import factory
from banffprocessor.processor_data import ProcessorData

# Setup local log for processor module specifically
log_lcl = plg.get_processor_child_logger("verifyedits")

class VerifyEdits:
    """Implements the VerifyEdits Banff procedure as a `:class:banffprocessor.procedures.procedure_interface`."""

    @classmethod
    def execute(cls, processor_data: ProcessorData) -> int:
        """Execute the banff.verifyedits call, and returns the results."""
        # alias the param name to shorten references
        bp = processor_data
        job_step = bp.current_job_step
        verifyedit_specs: Verifyeditsspecs = bp.metaobjects.get_specs_obj(Verifyeditsspecs, job_step.specid)

        # Get the edit string
        proc_edits = None
        if(job_step.editgroupid):
            proc_edits = bp.metaobjects.get_edits_string(job_step.editgroupid)

        if(proc_edits is None):
            msg = _("VerifyEdits requires a set of edits to work but none were found for this job step.")
            log_lcl.exception(msg)
            raise BanffPackageExecutionError(msg)

        # Form our Banff call
        try:
            banff_call = verifyed(
                # Not supposed to provide these as False, only True or None
                accept_negative=job_step.acceptnegative,
                extremal=verifyedit_specs.extremal if verifyedit_specs else None,
                imply=verifyedit_specs.imply if verifyedit_specs else None,
                edits=proc_edits if proc_edits else None,
                # We want everything captured while an input param configures the handlers which indirectly filter.
                trace=log_levels.NOTSET,
                # Note that capture=None will supress console output in new version so use False or omit
                logger=log_lcl,
                _BP_c_log_handlers=plg.get_c_handlers(),
            )
        except banff.exceptions.ProcedureCError as e:
            msg = _("An error occured during execution of this procedure.")
            log_lcl.exception(msg)
            return e.return_code # Get the return code from the exception

        return banff_call.rc

def register(factory: factory) -> None:
    """Register this procedure class in the Banff processor procedure factory."""
    factory.register(["verifyedits", "verify_edits", "verifyed"], VerifyEdits)
