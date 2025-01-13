import banff.exceptions
from banff import massimpu
from banff._log import log_levels

# Import must be absolute in order to ensure all modules reference the same global _c_handlers
import banffprocessor.processor_logger as plg
from banffprocessor.exceptions import MetadataConstraintError
from banffprocessor.metadata.models.massimputationspecs import Massimputationspecs
from banffprocessor.nls import _
from banffprocessor.procedures import factory
from banffprocessor.processor_data import ProcessorData
from banffprocessor.util.dataset import table_empty

# Setup local log for processor module specifically
log_lcl = plg.get_processor_child_logger("massimputation")

class MassImputation:
    """Implements the MassImputation Banff procedure as a `:class:banffprocessor.procedures.procedure_interface`."""

    output_tables: tuple[str] = ("outdonormap",)

    @classmethod
    def execute(cls, processor_data: ProcessorData) -> int:
        """Execute the banff.massimpu call, and returns the results."""
        # alias the param name to shorten references
        bp = processor_data
        job_step = bp.current_job_step
        mass_spec = bp.metaobjects.get_specs_obj(Massimputationspecs, job_step.specid)

        mustimpute_varlist = bp.metaobjects.get_varlist_fieldids(mass_spec.mustimputeid)
        if(not mustimpute_varlist):
            msg = _("MassImputation requires a mustimputeid but one was not provided.")
            log_lcl.exception(msg)
            raise MetadataConstraintError(msg)

        mustmatch_varlist = bp.metaobjects.get_varlist_fieldids(mass_spec.mustmatchid) if mass_spec.mustmatchid else None

        # Imputed_File should always have data by this point, but we'll make sure to pass None
        # instead of an empty table to the banff call just to make sure we don't pass an empty table
        imputed_file = bp.get_dataset("imputed_file")

        # Form our Banff call
        try:
            banff_call = massimpu(
                # Not supposed to provide these as False, only True or None
                accept_negative=job_step.acceptnegative,
                no_by_stats=bp.input_params.no_by_stats,
                presort=True,
                random=True if mass_spec.random else None,
                mrl=mass_spec.mrl,
                percent_donors=mass_spec.pcentdonors,
                min_donors=mass_spec.mindonors,
                n_limit=mass_spec.nlimit,
                seed=bp.input_params.seed,
                unit_id=bp.input_params.unit_id,
                by=" ".join(bp.by_varlist) if bp.by_varlist else None,
                must_impute=" ".join(mustimpute_varlist),
                must_match=" ".join(mustmatch_varlist) if mustmatch_varlist else None,
                indata=imputed_file if imputed_file is not None and not table_empty(imputed_file) else None,
                outdata="pyarrow",
                outstatus="pyarrow",
                outdonormap="pyarrow", # Mandatory dataset
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

        # Set outdata and outstatus on processor_data so that our flags will make the updates to the originals
        bp.outstatus = banff_call.outstatus
        bp.outdata = banff_call.outdata

        bp.save_proc_output(banff_call, cls.output_tables)

        return banff_call.rc

def register(factory: factory) -> None:
    """Register this procedure class in the Banff processor procedure factory."""
    factory.register(["massimputation", "massimp"], MassImputation)
