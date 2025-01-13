import pandas as pd
import banffprocessor.processor_logger as plg
from banffprocessor.processor_data import ProcessorData

log_lcl = plg.get_processor_child_logger("incrementfield")

class IncrementField:

    @classmethod
    def execute(cls, processor_data: ProcessorData):
        instatus = processor_data.get_dataset("instatus", create_if_not_exist=True, ds_format="pandas")
        indata = processor_data.get_dataset("indata", create_if_not_exist=True, ds_format="pandas")

        # Normal dict method
        my_var1 = int(processor_data.current_uservars["var1"])
        
        outdata = pd.DataFrame()
        for index, rows in instatus.loc[instatus["status"].str.upper() == "ABCD"].iterrows():
            ident_to_update = rows[processor_data.input_params.unit_id]
            field_to_update = rows["fieldid"]

            # Find the record with the unit_id value we want
            # The final iloc[0] ensures we only get the first record, just in case
            my_rec = indata.loc[indata[processor_data.input_params.unit_id] == ident_to_update].iloc[0]
            # From the series we filtered down to, add my_var1 to the value already in the field
            # found in field_to_update
            my_rec[field_to_update] += my_var1

            # convert the above series to_frame and transpose it before adding it to outdata
            outdata = pd.concat([outdata, my_rec.to_frame().T])

        # To get imputed_file updated we need to produce an outdata file
        processor_data.outdata = outdata

        # Indicate there were no errors
        return 0

def register(factory):
    factory.register("incrementfield", IncrementField)
