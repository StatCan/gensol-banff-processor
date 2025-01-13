import banff.exceptions
from banff import donorimp
from banff._log import log_levels

# Import must be absolute in order to ensure all modules reference the same global _c_handlers
import banffprocessor.processor_logger as plg
from banffprocessor.exceptions import ProcessorInputParameterError
from banffprocessor.metadata.models.donorspecs import Donorspecs
from banffprocessor.nls import _
from banffprocessor.procedures import factory
from banffprocessor.processor_data import ProcessorData
from banffprocessor.util.dataset import table_empty

# Setup local log for processor module specifically
log_lcl = plg.get_processor_child_logger("donorimputation")

# Required Metadata Files: "donorspecs", "editgroups", "edits"
# Optional Metadata Files: "expressions", "varlists"

class DonorImputation:
    """Implements the DonorImputation Banff procedure as a `:class:banffprocessor.procedures.procedure_interface`."""

    output_tables: tuple[str] = ("outdonormap", "outmatching_fields")

    @classmethod
    def execute(cls, processor_data: ProcessorData) -> int:
        """Execute the banff.donorimp call, and returns the results."""
        # alias the param name to shorten references
        bp = processor_data
        job_step = bp.current_job_step
        donor_spec = bp.metaobjects.get_specs_obj(Donorspecs, job_step.specid)

        # errorNumber DI01
        if(job_step.editgroupid is None or not job_step.editgroupid):
            msg = _("No editgroupid present for seqno {} under job with "
                    "jobid {}. editgroupid is required for DonorImputation.").format(job_step.seqno,
                                                                                     job_step.jobid)
            log_lcl.exception(msg)
            raise ProcessorInputParameterError(msg)

        # Get the edit string
        proc_edits = bp.metaobjects.get_edits_string(job_step.editgroupid)
        if(not proc_edits):
            msg = _("No edits found in Edits table for editgroupid {} at seqno {} under job with jobid {}. "
                    "Edits are required for DonorImputation.").format(job_step.editgroupid, job_step.seqno, job_step.jobid)
            log_lcl.exception(msg)
            raise ProcessorInputParameterError(msg)

        proc_post_edits = bp.metaobjects.get_edits_string(donor_spec.posteditgroupid) if donor_spec.posteditgroupid else None
        mustmatch_varlist = bp.metaobjects.get_varlist_fieldids(donor_spec.mustmatchid) if donor_spec.mustmatchid else []

        # Imputed_File should always have data by this point, but we'll make sure to pass None
        # instead of an empty table to the banff call just to make sure we don't pass an empty table
        status_file = bp.get_dataset("status_file")
        imputed_file = bp.get_dataset("imputed_file")

        # Form our Banff call
        try:
            banff_call = donorimp(
                unit_id=bp.input_params.unit_id,
                by=" ".join(bp.by_varlist) if bp.by_varlist else None,
                must_match=" ".join(mustmatch_varlist) if mustmatch_varlist else None,
                rand_num_var=bp.input_params.randnumvar,
                random=True if donor_spec.random else None,
                seed=bp.input_params.seed,
                edits=proc_edits if proc_edits else None,
                post_edits=proc_post_edits if proc_post_edits else None,
                display_level=None,
                # Not supposed to provide these as False, only True or None
                accept_negative=job_step.acceptnegative,
                no_by_stats=bp.input_params.no_by_stats,
                prefill_by_vars=True,
                presort=True,
                min_donors=donor_spec.mindonors,
                percent_donors=donor_spec.pcentdonors,
                n=donor_spec.n,
                eligdon=donor_spec.eligdon,
                n_limit=donor_spec.nlimit,
                mrl=donor_spec.mrl,
                indata=imputed_file if imputed_file is not None and not table_empty(imputed_file) else None,
                instatus=status_file if status_file is not None and not table_empty(status_file) else None,
                exclude_where_indata=bp.metaobjects.get_expression(donor_spec.dataexclvar),
                outdata="pyarrow",
                outstatus="pyarrow",
                outdonormap="pyarrow", # Mandatory dataset
                outmatching_fields="pyarrow" if bp.output_required("outmatching_fields") else False,
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

        bp.outstatus = banff_call.outstatus
        bp.outdata = banff_call.outdata

        bp.save_proc_output(banff_call, cls.output_tables)

        return banff_call.rc

def register(factory: factory) -> None:
    """Register this procedure class in the Banff processor procedure factory."""
    factory.register(["donorimputation", "donorimp"], DonorImputation)
