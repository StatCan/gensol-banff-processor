import banffprocessor.processor_logger as plg
from banffprocessor.processor_data import ProcessorData

class CreateNewFile:
    
    @classmethod
    def execute(cls, processor_data) -> int:
        # Creating a logger for this step
        log_lcl = plg.get_processor_child_logger("create_new_file")
        
        try:
            # Log the should-be-filtered indata file
            log_lcl.info(processor_data.indata.to_pandas())
            # Get the filename we will save the filtered version under
            new_filename = processor_data.current_uservars["filename"]
            # Add a new dataset entry with set_dataset, will be saved during save_output()
            # as long as we don't include "indata" or "instatus" in the name
            processor_data.set_dataset(new_filename, processor_data.indata.select(processor_data.indata.column_names))
            return 0      
        except Exception as e:
            # If an error occurs, printing the error to the log and returning a non-zero return code
            log_lcl.exception(e)
            return 1

# Providing a function so that the processor can register this class in the procedure factory
def register(factory):
    factory.register("create_new_file", CreateNewFile)
