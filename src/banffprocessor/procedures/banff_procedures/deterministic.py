import banff.exceptions
from banff import determin
from banff._log import log_levels

# Import must be absolute in order to ensure all modules reference the same global _c_handlers
import banffprocessor.processor_logger as plg
from banffprocessor.nls import _
from banffprocessor.procedures import factory
from banffprocessor.processor_data import ProcessorData
from banffprocessor.util.dataset import table_empty

# Setup local log for processor module specifically
log_lcl = plg.get_processor_child_logger("deterministic")

# Required Metadata Files: "editgroups", "edits"
# Optional Metadata Files = "varlists"

class Deterministic:
    """Implements the Deterministic Banff procedure as a `:class:banffprocessor.procedures.procedure_interface`."""

    @classmethod
    def execute(cls, processor_data: ProcessorData) -> int:
        """Execute the banff.determin call, and returns the results."""
        # alias the param name to shorten references
        bp = processor_data
        job_step = bp.current_job_step

        # Get the edit strings by concatenating the edits we need filtered on the editgroupid
        proc_edits = None
        if(job_step.editgroupid):
            proc_edits = bp.metaobjects.get_edits_string(job_step.editgroupid)

        # Imputed_File should always have data by this point, but we'll make sure to pass None
        # instead of an empty table to the banff call just to make sure we don't pass an empty table
        status_file = bp.get_dataset("status_file")
        imputed_file = bp.get_dataset("imputed_file")

        # Form our Banff call
        try:
            banff_call = determin(
                # Not supposed to provide these as False, only True or None
                accept_negative=job_step.acceptnegative,
                no_by_stats=bp.input_params.no_by_stats,
                prefill_by_vars=True,
                presort=True,
                edits=proc_edits if proc_edits else None,
                unit_id=bp.input_params.unit_id,
                by=" ".join(bp.by_varlist) if bp.by_varlist else None,
                indata=imputed_file if imputed_file is not None and not table_empty(imputed_file) else None,
                instatus=status_file if status_file is not None and not table_empty(status_file) else None,
                outdata="pyarrow",
                outstatus="pyarrow",
                # We want everything captured while an input param configures the handlers
                # which indirectly filter.
                trace=log_levels.NOTSET,
                # Note that capture=None will supress console output in new version so use False or omit
                logger=log_lcl,
                _BP_c_log_handlers=plg.get_c_handlers(),
            )
        except banff.exceptions.ProcedureCError as e:
            msg = _("An error occured during execution of this procedure.")
            log_lcl.exception(msg)
            return e.return_code # Get the return code from the exception

        # set datasets on processor_data so that our flags will make the update to the originals
        bp.outstatus = banff_call.outstatus
        bp.outdata = banff_call.outdata

        return banff_call.rc

def register(factory: factory) -> None:
    """Register this procedure class in the Banff processor procedure factory."""
    factory.register("deterministic", Deterministic)
