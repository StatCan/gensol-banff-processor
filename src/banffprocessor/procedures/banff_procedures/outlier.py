import banff.exceptions
from banff import outlier
from banff._log import log_levels

# Import must be absolute in order to ensure all modules reference the same global _c_handlers
import banffprocessor.processor_logger as plg
from banffprocessor.exceptions import ProcessorInputParameterError
from banffprocessor.metadata.models.outlierspecs import Outlierspecs
from banffprocessor.nls import _
from banffprocessor.procedures import factory
from banffprocessor.processor_data import ProcessorData
from banffprocessor.util.dataset import table_empty

# Setup local log for processor module specifically
log_lcl = plg.get_processor_child_logger("outlier")

# Required Metadata files = "outlierspecs"
# Optional Metdata files = "varlists"

class Outlier:
    """Implements the Outlier Banff procedure as a `:class:banffprocessor.procedures.procedure_interface`."""

    output_tables: tuple[str] = ("outlier_status", "outsummary")

    @classmethod
    def execute(cls, processor_data: ProcessorData) -> int:
        """Execute the banff.outlier call, and returns the results."""
        # alias the param name to shorten references
        bp = processor_data
        job_step = bp.current_job_step
        outlier_spec = bp.metaobjects.get_specs_obj(Outlierspecs, job_step.specid)

        varlist = []
        with_varlist = []
        if(outlier_spec.varid is not None):
            varlist = bp.metaobjects.get_varlist_fieldids(outlier_spec.varid)
        if(outlier_spec.withid is not None):
            with_varlist = bp.metaobjects.get_varlist_fieldids(outlier_spec.withid)

        # Choose the auxillary or historic file to use, depending on method
        # currently aux and historic files use the same argument in the banff proc call
        indata_hist_param = None
        # We only want to check for an extra data file if it was indicated in the metadata
        if(outlier_spec.numDataSets == 2):
            indata_aux = bp.get_dataset("indata_aux")
            indata_hist = bp.get_dataset("indata_hist")

            if(outlier_spec.method == "HISTORIC"):
                if(indata_hist is not None):
                    indata_hist_param = indata_hist
                elif(indata_aux is not None):
                    indata_hist_param = indata_aux
                else:
                    msg = _("Outlierspecs metadata table indicated two data sets for this step "
                            "so HISTORIC outlier method expects one of historic data file "
                            "or auxillary data file but neither were able to be loaded.")
                    log_lcl.exception(msg)
                    raise ProcessorInputParameterError(msg)
            elif(outlier_spec.method in {"RATIO", "SIGMAP"}):
                if(indata_aux is not None):
                    indata_hist_param = indata_aux
                elif(indata_hist is not None):
                    indata_hist_param = indata_hist
                else:
                    msg = _("Outlierspecs metadata table indicated two data sets for this step "
                            "so RATIO or SIGMAP outlier method expects one of auxillary data file "
                            "or historic data file but neither were able to be loaded.")
                    log_lcl.exception(msg)
                    raise ProcessorInputParameterError(msg)

        # Imputed_File should always have data by this point, but we'll make sure to pass None
        # instead of an empty table to the banff call just to make sure we don't pass an empty table
        imputed_file = bp.get_dataset("imputed_file")

        # Form our Banff call
        try:
            banff_call = outlier(
                unit_id=bp.input_params.unit_id,
                weight=outlier_spec.weight,
                by=" ".join(bp.by_varlist) if bp.by_varlist else None,
                var=" ".join(varlist) if varlist else None,
                with_var=" ".join(with_varlist) if with_varlist else None,
                no_by_stats=bp.input_params.no_by_stats,
                presort=True,
                # Not supposed to provide these as False, only True or None
                accept_negative=job_step.acceptnegative,
                accept_zero=outlier_spec.acceptzero,
                beta_e=outlier_spec.betae,
                beta_i=outlier_spec.betai,
                exponent=outlier_spec.exponent,
                mdm=outlier_spec.mdm,
                mei=outlier_spec.mei,
                mii=outlier_spec.mii,
                start_centile=outlier_spec.startcentile,
                min_obs=outlier_spec.minobs,
                method=outlier_spec.method,
                side=outlier_spec.side,
                sigma=outlier_spec.sigma,
                exclude_where_indata=bp.metaobjects.get_expression(outlier_spec.dataexclvar),
                indata=imputed_file if imputed_file is not None and not table_empty(imputed_file) else None,
                indata_hist=indata_hist_param,
                # Specify to get extra data in outstatus, used for validation in tests
                outlier_stats=True,
                outstatus="pyarrow",
                outstatus_detailed="pyarrow" if bp.output_required("outlier_status") else False,
                outsummary="pyarrow" if bp.output_required("outsummary") else False,
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

        # Will only have values if they were requested
        if(banff_call.outstatus_detailed):
            bp.set_dataset("outlier_status", banff_call.outstatus_detailed)
        if(banff_call.outsummary):
            bp.set_dataset("outsummary", banff_call.outsummary)

        return banff_call.rc

def register(factory: factory) -> None:
    """Register this procedure class in the Banff processor procedure factory."""
    factory.register("outlier", Outlier)
