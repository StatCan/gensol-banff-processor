import banff.exceptions
from banff import editstat
from banff._log import log_levels

# Import must be absolute in order to ensure all modules reference the same global _c_handlers
import banffprocessor.processor_logger as plg
from banffprocessor.nls import _
from banffprocessor.procedures import factory
from banffprocessor.processor_data import ProcessorData
from banffprocessor.util.dataset import table_empty

# Setup local log for processor module specifically
log_lcl = plg.get_processor_child_logger("editstats")

class EditStats:
    """Implements the EditStats Banff procedure as a `:class:banffprocessor.procedures.procedure_interface`."""

    output_tables: tuple[str] = ("outedit_applic", "outedit_status", "outglobal_status",
                                 "outk_edits_status", "outedits_reduced", "outvars_role")

    @classmethod
    def execute(cls, processor_data: ProcessorData) -> int:
        """Execute the banff.editstats call, and returns the results."""
        # alias the param name to shorten references
        bp = processor_data
        job_step = bp.current_job_step

        # Get the edit string
        proc_edits = None
        if(job_step.editgroupid):
            proc_edits = bp.metaobjects.get_edits_string(job_step.editgroupid)

        # Form the kwargs parameter dict to specify the tables we want
        optional_outputs = {}
        for table_name in cls.output_tables:
            # Make sure we default to False otherwise the file might still be created
            optional_outputs[table_name] = "pyarrow" if bp.output_required(table_name) else False

        # Imputed_File should always have data by this point, but we'll make sure to pass None
        # instead of an empty table to the banff call just to make sure we don't pass an empty table
        imputed_file = bp.get_dataset("imputed_file")

        try:
            # Form our Banff call
            banff_call = editstat(
                # Not supposed to provide these as False, only True or None
                accept_negative=job_step.acceptnegative,
                edits=proc_edits if proc_edits else None,
                by=" ".join(bp.by_varlist) if bp.by_varlist else None,
                indata=imputed_file if imputed_file and not table_empty(imputed_file) else None,
                **optional_outputs,
                presort=True,
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

        bp.save_proc_output(banff_call, cls.output_tables)

        return banff_call.rc

def register(factory: factory) -> None:
    """Register this procedure class in the Banff processor procedure factory."""
    factory.register(["editstats", "edit_stats", "editstat", "edit_stat"], EditStats)
