import banff.exceptions
from banff import errorloc
from banff._log import log_levels

# Import must be absolute in order to ensure all modules reference the same global _c_handlers
import banffprocessor.processor_logger as plg
from banffprocessor.exceptions import ProcessorInputParameterError
from banffprocessor.metadata.models.errorlocspecs import Errorlocspecs
from banffprocessor.nls import _
from banffprocessor.procedures import factory
from banffprocessor.processor_data import ProcessorData
from banffprocessor.util.dataset import table_empty

# Setup local log for processor module specifically
log_lcl = plg.get_processor_child_logger("errorloc")

# Required Metadata Files: "editgroups", "edits", "errorlocspecs"
# Optional Metadata Files: "varlists", "weights"

class Errorloc:
    """Implements the Errorloc Banff procedure as a `:class:banffprocessor.procedures.procedure_interface`."""

    output_tables: tuple[str] = ("outreject")

    @classmethod
    def execute(cls, processor_data: ProcessorData) -> int:
        """Execute the banff.errorloc call, and returns the results."""
        # alias the param name to shorten references
        bp = processor_data
        job_step = bp.current_job_step
        errorloc_spec = bp.metaobjects.get_specs_obj(Errorlocspecs, job_step.specid)

        # errorNumber EL01
        if(not job_step.editgroupid):
            msg = _("No editgroupid present for seqno {} under job with jobid {}. "
                    "An editgroupid is required for Errorloc.").format(job_step.seqno, job_step.jobid)
            log_lcl.exception(msg)
            raise ProcessorInputParameterError(msg)

        # Get the edit/weights strings by concatenating the edits/weights
        # we need filtered on the editgroupid/weightid
        proc_edits = bp.metaobjects.get_edits_string(job_step.editgroupid)
        if(not proc_edits):
            msg = _("No edits found in Edits table for editgroupid {} at seqno {} under job with jobid {}. "
                    "Edits are required for Errorloc.").format(job_step.editgroupid, job_step.seqno,
                                                               job_step.jobid)
            log_lcl.exception(msg)
            raise ProcessorInputParameterError(msg)

        proc_weights = bp.metaobjects.get_weights_string(errorloc_spec.weightid) if errorloc_spec.weightid else None

        # Imputed_File should always have data by this point, but we'll make sure to pass None
        # instead of an empty table to the banff call just to make sure we don't pass an empty table
        imputed_file = bp.get_dataset("imputed_file")
        status_file = bp.get_dataset("status_file")

        # Form our Banff call
        try:
            banff_call = errorloc(
                unit_id=bp.input_params.unit_id,
                by=" ".join(bp.by_varlist) if bp.by_varlist else None,
                rand_num_var=bp.input_params.randnumvar,
                edits=proc_edits if proc_edits else None,
                weights=proc_weights if proc_weights else None,
                cardinality=errorloc_spec.cardinality,
                time_per_obs=errorloc_spec.timeperobs,
                seed=bp.input_params.seed,
                display_level=None,
                # Not supposed to provide these as False, only True or None
                accept_negative=job_step.acceptnegative,
                no_by_stats=bp.input_params.no_by_stats,
                prefill_by_vars=True,
                presort=True,
                indata=imputed_file if imputed_file is not None and not table_empty(imputed_file) else None,
                instatus=status_file if status_file is not None and not table_empty(status_file) else None,
                outstatus="pyarrow",
                outreject="pyarrow",
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

        # set outstatus as we want to update status_file
        bp.outstatus = banff_call.outstatus

        # outreject needs to exist as a dataset in processor_data before calling update_file_all
        # It is also the only real exception to the saving of non-cumulative tables
        bp.set_dataset("outreject", banff_call.outreject)
        bp.update_file_all("outreject", "outreject_all")

        # Usually 'outreject' is updated with the new 'outreject' by concatenating the new records.
        # But in the specific case of Errorloc, 'outreject' should just be the result from this
        # Errorloc run, and it should overwrite the existing 'outreject' (called "outreject" but
        # used as inreject for the next proc, if required)

        return banff_call.rc

def register(factory: factory) -> None:
    """Register this procedure class in the Banff processor procedure factory."""
    factory.register("errorloc", Errorloc)
