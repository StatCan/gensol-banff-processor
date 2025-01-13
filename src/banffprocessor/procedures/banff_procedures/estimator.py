"""Wrap Banff Estimator Procedure in Banff Processor Procedure."""

import banff.exceptions
import pyarrow as pa
from banff import estimato
from banff._log import log_levels

# Import must be absolute in order to ensure all modules reference the same global _c_handlers
import banffprocessor.processor_logger as plg
from banffprocessor.exceptions import EmptyMetadataFileError
from banffprocessor.metadata.models import estimators
from banffprocessor.metadata.models.estimatorspecs import Estimatorspecs
from banffprocessor.nls import _
from banffprocessor.procedures import factory
from banffprocessor.processor_data import ProcessorData
from banffprocessor.util.dataset import table_empty

# Setup local log for processor module specifically
log_lcl = plg.get_processor_child_logger("estimator")

# Required Metadata Files: "estimators", "estimatorspecs"
# Optional Metadata Files: "algorithms", "expressions", "varlists"

class Estimator:
    """Implements the Estimator Banff procedure as a `:class:banffprocessor.procedures.procedure_interface`."""

    output_tables: tuple[str] = ("outacceptable", "outest_ef", "outest_lr", "outest_parm", "outrand_err")

    @classmethod
    def execute(cls, processor_data: ProcessorData) -> int:
        """Execute the banff.outlier call, and returns the results."""
        # alias the param name to shorten references
        bp = processor_data
        job_step = bp.current_job_step
        estimator_spec = bp.metaobjects.get_specs_obj(Estimatorspecs, job_step.specid)

        # Get the estimators to use
        proc_estimators = bp.metaobjects.get_estimators(estimator_spec.estimatorid)

        # Check that the list is not empty
        if(not proc_estimators):
            msg = _("No Estimators were found under EstimatorID: {} for jobID: {} "
                    "and seqno: {}").format(estimator_spec.estimatorid, job_step.jobid, job_step.seqno)
            log_lcl.exception(msg)
            raise EmptyMetadataFileError(msg)

        fl_ac = True  # flag to control if outacceptable is requested
        fl_ef = False # flag to control if outestef is requested
        fl_lr = False  # flag to control if outestlr is requested
        fl_re = False # flag to control if outrand_err is requested

        # list of custom algorithms provided in the Algorithms.xml metadata file
        # We are fetching the Algorithms objects that apply to the current job step
        # below anyways, so add them to a list to convert to a dataset after, rather
        # than converting the entire list of Algorithms objects, even the ones we don't need
        proc_algorithms = []

        for est in proc_estimators:
            if(est.randomerror):
                fl_re = True

            est_algo_name = est.algorithmname.upper()

            estimator_type = estimators.builtin_estimators().get(est_algo_name)
            if estimator_type is None:
                est_algo = bp.metaobjects.get_algorithm(est_algo_name)
                if(est_algo):
                    proc_algorithms.append(est_algo)
                    estimator_type = est_algo.type

            # Determine whether to request the data set containing the report on the calculation of « beta » coefficients (LR=Linear Regression).
            if(estimator_type == "LR"):
                fl_lr = True
             # Determine whether to request the data set containing the report on the calculation of averages (EF=Estimator Function).
            elif (estimator_type == "EF"):
                fl_ef = True

        # proc_estimators must now be converted to a pyarrow table.
        # As the list is already sorted on seqno by the metaobjects method
        # used to retrieve it, we don't need to sort the resulting dataset
        estimators_ds = pa.Table.from_pylist([e.to_dict() for e in proc_estimators])
        estimators_ds = estimators_ds.drop_columns(["seqno", "estimatorid"])

        # Algorithms list convert to pyarrow table
        algorithms_ds = None
        if(proc_algorithms):
            algorithms_ds = pa.Table.from_pylist([e.to_dict() for e in proc_algorithms])

        # Imputed_File should always have data by this point, but we'll make sure to pass None
        # instead of an empty table to the banff call just to make sure we don't pass an empty table
        imputed_file = bp.get_dataset("imputed_file")
        status_file = bp.get_dataset("status_file")
        indata_hist = bp.get_dataset("indata_hist")
        instatus_hist = bp.get_dataset("instatus_hist")

        # Form our Banff call
        try:
            banff_call = estimato(
                unit_id=bp.input_params.unit_id,
                by=" ".join(bp.by_varlist) if bp.by_varlist else None,
                seed=bp.input_params.seed,
                verify_specs=None,
                # Not supposed to provide these as False, only True or None
                accept_negative=job_step.acceptnegative,
                no_by_stats=bp.input_params.no_by_stats,
                prefill_by_vars=True,
                presort=True,
                indata=imputed_file if imputed_file is not None and not table_empty(imputed_file) else None,
                instatus=status_file if status_file is not None and not table_empty(status_file) else None,
                indata_hist=indata_hist,
                inalgorithm=algorithms_ds,
                inestimator=estimators_ds,
                instatus_hist=instatus_hist,
                exclude_where_indata=bp.metaobjects.get_expression(estimator_spec.dataexclvar),
                exclude_where_indata_hist=bp.metaobjects.get_expression(estimator_spec.histexclvar),
                outstatus="pyarrow",
                outdata="pyarrow",
                # Make sure we default to False otherwise the file might still be created
                outacceptable="pyarrow" if bp.output_required("outacceptable") and fl_ac else False,
                outest_ef="pyarrow" if bp.output_required("outest_ef") and fl_ef else False,
                outest_lr="pyarrow" if bp.output_required("outest_lr") and fl_lr else False,
                outest_parm="pyarrow" if bp.output_required("outest_parm") else False,
                outrand_err="pyarrow" if bp.output_required("outrand_err") and fl_re else False,
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

        # Set outstatus and outdata on processor_data so that our flags
        # will make the update to the originals
        bp.outstatus = banff_call.outstatus
        bp.outdata = banff_call.outdata

        bp.save_proc_output(banff_call, cls.output_tables)

        return banff_call.rc

def register(factory: factory) -> None:
    """Register this procedure class in the Banff processor procedure factory."""
    factory.register("estimator", Estimator)
