# Note that importing the Processor class directly leads to circular import (from banffprocessor.processor import Processor)
import banffprocessor.processor as bpp

# Import must be absolute in order to ensure all modules reference the same global _c_handlers
import banffprocessor.processor_logger as plg
from banffprocessor.nls import _
from banffprocessor.procedures import factory
from banffprocessor.processor_data import ProcessorData

# Setup local log for processor module specifically
log_lcl = plg.get_processor_child_logger("jobproc")

class JobProc:
    """Implements the execution of a new process block as a `:class:banffprocessor.procedures.procedure_interface`."""

    @classmethod
    def execute(cls, processor_data: ProcessorData) -> int:
        """Execute a process block indicated by the "JOB" process for a particular job step."""
        # Jobid of the calling block
        curr_jobid = processor_data.input_params.job_id
        # Jobid for the block being called
        sub_jobid = processor_data.current_job_step.specid

        msg = _("Beginning execution of job {} from job {} at seqno {}").format(
            sub_jobid, curr_jobid, processor_data.current_job_step.seqno)
        log_lcl.info(msg)

        # Call a new instance of the Banff Processor
        # Supplying parameters directly, instead of an input file
        my_bp = bpp.Processor(initial_data=processor_data.get_new_block_copy())

        my_bp.execute()
        my_bp.save_outputs()

        # Bring all of the sub-block's datasets in our dataset collection
        processor_data.update_with_block_result(my_bp.processor_data)

        # Copy over the custom_outputs list, which should hold the expected output tables for the
        # last job step of the process block. This will let the processor know it needs to update
        # and not discard the outputs from our block, since the ProcessOutputs metadata is set
        # on the proc that ran in the job block, not the job step that calls the block.
        processor_data.custom_outputs = my_bp.processor_data.custom_outputs.copy()

        msg = _("Job {} complete.").format(sub_jobid)
        log_lcl.info(msg)

        my_bp = None

        return 0

def register(factory: factory) -> None:
    """Register this procedure class in the Banff processor procedure factory."""
    factory.register("job", JobProc)
