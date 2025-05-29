import json
from enum import Enum
from pathlib import Path

from banff._log import log_levels

import banffprocessor.processor_logger as plg
from banffprocessor.exceptions import ProcessorInputParameterError
from banffprocessor.nls import _
from banffprocessor.util.case_insensitive_enum_meta import CaseInsensitiveEnumMeta

log_lcl = plg.get_processor_child_logger("processor_input")

## Specified in and loaded from main program input json file ##
class ProcessorInput:
    """Holds input parameters from a user's JSON input file used to configure a Banff Processor job."""

    def __init__(self, job_id: str,
                 unit_id: str | None = None, input_folder: str | Path | None = None,
                 indata_filename: str | Path | None = None,
                 auxdata_filename: str | Path | None = None, indata_aux_filename: str | Path | None = None,
                 histdata_filename: str | Path | None = None, indata_hist_filename: str | Path | None = None,
                 histstatus_filename: str | Path | None = None, instatus_hist_filename: str | Path | None = None,
                 instatus_filename: str | Path | None = None, user_plugins_folder: str | Path | None = None,
                 metadata_folder: str | Path | None = None, process_output_type: str | int | None = None,
                 seed: int | None = None, no_by_stats: str | bool | None = None,
                 randnumvar: str | None = None, save_format: list[str] | None = None,
                 output_folder: str | Path | None = None, log_level: int | None = None,
                 ) -> None:
        """Construct a ProcessorInput object.

        :param job_id: The job_id of the job to run.
        :type job_id: str
        :param unit_id: The unit_id for the job to run. Not required for UDPs, VerifyEdits,
            EditStats, or 'Job' procedures but required for all other procs. Defaults to None
        :type unit_id: str, optional
        :param input_folder: The directory containing the JSON file used to create this object, and/or
            the directory containing the input data and status files as well as sub-directories for
            /metadata and /plugins. Also used to create the subdirectory /out for output files, if
            no `output_folder` is provided as a part of the provided arguments.
        :type input_folder: str | Path
        :param indata_filename: The filename of the indata file which is required in almost
            all cases, defaults to None
        :type indata_filename: str | Path | None, optional
        :param auxdata_filename: The filename of the auxillary data file, defaults to None. This field
            is an alias for `indata_aux_filename`, they represent the same value.
        :type auxdata_filename: str | Path | None, optional
        :param indata_aux_filename: The filename of the auxillary data file, defaults to None
        :type indata_aux_filename: str | Path | None, optional
        :param histdata_filename: The filename of the historical data file, defaults to None. This field
            is an alias for `indata_hist_filename`, they represent the same value.
        :type histdata_filename: str | Path | None, optional
        :param indata_hist_filename: The filename of the auxillary data file, defaults to None
        :type indata_hist_filename: str | Path | None, optional
        :param histstatus_filename: The filename of the historical status file, defaults to None. This field
            is an alias for `instatus_hist_filename`, they represent the same value.
        :type histstatus_filename: str | Path | None, optional
        :param instatus_hist_filename: The filename of the auxillary data file, defaults to None
        :type instatus_hist_filename: str | Path | None, optional
        :param instatus_filename: The filename of the instatus file, defaults to None
        :type instatus_filename: str | Path | None, optional
        :param user_plugins_folder: The directory where the user defined plugin modules for this job
            are located, defaults to None
        :type user_plugins_folder: str | Path | None, optional
        :param metadata_folder: The directory where the metadata files for this job are located,
            defaults to None
        :type metadata_folder: str | Path | None, optional
        :param process_output_type: Specifies a level which determines the types of output files
            that will be saved/produced, defaults to None
        :type process_output_type: str | int | None, optional
        :param seed: _description_, defaults to None
        :type seed: int | None, optional
        :param no_by_stats: _description_, defaults to None
        :type no_by_stats: str | bool | None, optional
        :param randnumvar: _description_, defaults to None
        :type randnumvar: str | None, optional
        :param save_format: _description_, defaults to None
        :type save_format: list[str] | None, optional
        :param output_folder: _description_, defaults to None
        :type output_folder: str | Path | None, optional
        :param log_level: _description_, defaults to None
        :type log_level: str | None, optional
        :raises ProcessorInputParameterError: If no valid `job_id` or `unit_id` is provided
        :raises ProcessorInputParameterError: If the `save_format` parameter is provided in
            an improper format
        """
        # input_folder is technically not required if the user provides explicit locations
        # for their metadata files and their output folder
        if(not input_folder and not (metadata_folder and output_folder)):
            msg = _("Input parameter input_folder must be provided unless both "
                "metadata_folder and output_folder are provided.")
            log_lcl.exception(msg)
            raise ValueError(msg)

        # NOT FOUND IN ACTUAL INPUT JSON FILE, VALUE SHOULD BE THE FOLDER THE FILE IS FOUND IN
        # this folder is used as a default file location if the path to a required file was
        # not explicitly defined in any of the other input parameters such as indata_filename
        self.input_folder = get_path_val(input_folder)

        def abs_path(file_or_dir: Path | str | None, param_name: str) -> Path | None:
            """Convert file_or_dir to an absolute path.

            If file_or_dir is a non-absolute path it is treated as relative to the input_folder and
            the final path will begin with input_folder.

            :param file_or_dir: The filepath to convert.
            :type file_or_dir: str | Path | None
            :param param_name: The name of the parameter being processed (for error reporting)
            :type param_name: str
            :return: file_or_dir as represented by a Path object.
            :rtype: Path | None
            """
            file_or_dir = get_path_val(file_or_dir)
            if(not file_or_dir):
                return None

            output_parents = False
            if(not file_or_dir.is_absolute()):
                if(self.input_folder):
                    file_or_dir = (self.input_folder / file_or_dir).resolve()
                    # Specifically for output_folder, if given as relative path,
                    # we want to create any parent folders of the final output directory
                    # if it doesn't yet exist. If output_folder is given as abolute
                    # we DON'T want to create the parent folders, only the final output directory.
                    output_parents = True
                else:
                    msg = _("Input folder was not given but {} is a relative path.").format(param_name)
                    log_lcl.exception(msg)
                    raise ProcessorInputParameterError(msg)

            if(not file_or_dir.exists()):
                if(param_name == "output_folder"):
                    try:
                        file_or_dir.mkdir(parents=output_parents)
                    except FileNotFoundError as e:
                        msg = _("Parent folders in input parameter filepath output_folder: {} could not be "
                                "found so output folder could not be created.").format(str(file_or_dir))
                        log_lcl.exception(msg)
                        raise ProcessorInputParameterError(msg) from e
                else:
                    msg = _("Filepath in input parameter {}: {} is not accesible or does "
                            "not exist.").format(param_name, str(file_or_dir))
                    log_lcl.exception(msg)
                    raise ProcessorInputParameterError(msg)

            return file_or_dir

        # Optional alternate save location for output files
        self.output_folder = abs_path(output_folder, "output_folder")
        if(not self.output_folder):
            # Create output folder if one wasn't provided
            self.output_folder = self.input_folder / "out"
            if not self.output_folder.exists():
                self.output_folder.mkdir()

        # Optional alternate folder location of metadata files
        self.metadata_folder = abs_path(metadata_folder, "metadata_folder")
        # Load all of our metadata
        if(not self.metadata_folder):
            # The user may or may not have opted for a sub-folder
            meta_path = self.input_folder / "metadata"
            # If no specific metadata folder is given, check for a "metadata" subfolder in the
            # input_folder. If this doesn't exist just use the input_folder
            self.metadata_folder = meta_path if meta_path.exists() else self.input_folder

        # Optional alternate folder location of user program files
        self.user_plugins_folder = abs_path(user_plugins_folder, "user_plugins_folder")
        # Check if the user provided a custom folder path
        if(not self.user_plugins_folder and self.input_folder):
            # If not see if their plugins are in a "plugins" subfolder in the input folder
            plugins_path = self.input_folder / "plugins"
            if(plugins_path.exists()):
                self.user_plugins_folder = plugins_path

        self.job_id = get_string_param_value(job_id)
        if(self.job_id is None):
            msg = _("No valid job_id found in processor_input file.")
            log_lcl.exception(msg)
            raise ProcessorInputParameterError(msg)

        self.unit_id = get_string_param_value(unit_id)

        # Allowed to be none in the case of a job only performing "Verifyedits"
        # Also should allow either just filename or a full filepath
        # If just a filename is provided, file will be searched for in the input_folder
        # otherwise the full filepath is used for loading the file into a dataframe
        self.indata_filename = abs_path(indata_filename, "indata_filename")

        # statusAll may be provided for input to any procs that require an instatus
        # parameter, if there is no statusAll file created by any prior procs in the job
        self.instatus_filename = abs_path(instatus_filename, "instatus_filename")

        if(indata_aux_filename):
            self.indata_aux_filename = abs_path(indata_aux_filename, "indata_aux_filename")
        else:
            self.indata_aux_filename = abs_path(auxdata_filename, "auxdata_filename")

        if(indata_hist_filename):
            self.indata_hist_filename = abs_path(indata_hist_filename, "indata_hist_filename")
        else:
            self.indata_hist_filename = abs_path(histdata_filename, "histdata_filename")

        if(instatus_hist_filename):
            self.instatus_hist_filename = abs_path(instatus_hist_filename, "instatus_hist_filename")
        else:
            self.instatus_hist_filename = abs_path(histstatus_filename, "histstatus_filename")

        # Output type option to allow users to specify the level of information
        # recorded and output from their respective procs
        try:
            self.process_output_type = None
            if(isinstance(process_output_type, str)):
                self.process_output_type = ProcessOutputType[process_output_type]
            elif(isinstance(process_output_type, int)):
                self.process_output_type = ProcessOutputType(process_output_type)
            elif(process_output_type is not None):
                raise ValueError
        except (KeyError, ValueError) as e:
            msg = _("ProcessorInput process_output_type field contains an unrecognized value.")
            raise ProcessorInputParameterError(msg) from e

        # Boolean properties so we don't have to import ProcessOutputType
        # every place we want to check these
        self.output_custom = (self.process_output_type == ProcessOutputType.CUSTOM)
        self.output_all = (self.process_output_type == ProcessOutputType.ALL)

        # Seed value to be used in Banff procs that allow the seed option.
        # Useful for comparing results between multiple runs.
        self.seed = int(seed) if seed is not None else None

        # TIME - display the time for each seqno
        self.time = True

        # TIMESTORE - Creates the jobInfoRecords dataset which contains the start,
        # end, and elapsed amount of time of each sequence run by the Banff Processor.
        self.time_store = True

        # no_by_stats - Determines if the no_by_stats parameter is set to True for each standard Banff Procedure
        # The input may be passed in as a boolean or a string, for example true, 'true' or 'True'
        if no_by_stats is None or str(no_by_stats).casefold() == "false":
            # The no_by_stats parameter cannot be set to false in the procedures, it is either True or None
            self.no_by_stats = None
        elif str(no_by_stats).casefold() == "true":
            self.no_by_stats = True
        else:
            msg = _("Invalid value in processor_input file: no_by_stats must be true, false or not specified.")
            log_lcl.exception(msg)
            raise ProcessorInputParameterError(msg)

        self.randnumvar = get_string_param_value(randnumvar)

        # Optional param used to override the output file format which by default
        # uses the same type as the input file
        if(save_format is not None):
            if(isinstance(save_format, list)):
                # Only save a value if it's a list with items in it
                self.save_format = save_format if save_format else None
            else:
                msg = _("save_format parameter of the input JSON file must be a list "
                        "of supported file extensions or be excluded or empty.")
                log_lcl.exception(msg)
                raise ProcessorInputParameterError(msg)
        else:
            self.save_format = None

        # Determines if we should create the INFO and/or DEBUG log files
        if(log_level is None or log_level == 1):
            # Default option
            self.log_level = log_levels.INFO
        elif(log_level < 1):
            # does not create any file handlers
            self.log_level = None
        elif(log_level > 1):
            self.log_level = log_levels.DEBUG

    @classmethod
    def from_file(cls, filepath: str | Path) -> "ProcessorInput":
        """Initialize a :class:`src.banffprocessor.processor_input.ProcessorInput` object from a JSON file.

        :param filepath: the full path to the JSON file containing the input parameters
            required to run the processor.
        :type filepath: str | Path
        :raises ProcessorInputParameterError: If the `filepath` does not contain a valid
            directory or JSON filename
        :raises FileNotFoundError: If the file at `filepath` is not able to be found
        :return: The object loaded from the parameters in the JSON file
        :rtype: :class:`src.banffprocessor.processor_input.ProcessorInput`
        """
        filepath = Path(filepath)

        if(not filepath.is_absolute() or not filepath.is_file()):
            msg = _("Filepath is not properly configured. "
                    "Make sure that you use the full filepath of the input JSON file.")
            log_lcl.exception(msg)
            raise ProcessorInputParameterError(msg)
        if(filepath.suffix.casefold() != ".json"):
            msg = _("input_filepath is not a JSON file. The input file parameters "
                    "must be passed as the full filepath of the input JSON file.")
            log_lcl.exception(msg)
            raise ProcessorInputParameterError(msg)

        # Load input variables from json file found in processing folder
        try:
            with filepath.open() as json_input_params:
                json_input = json.load(json_input_params)
                # Build the object and return
                return cls(input_folder=filepath.parent, **json_input)
        except FileNotFoundError as e:
            msg = _("Unable to find JSON input file under input filepath {}").format(filepath)
            log_lcl.exception(msg)
            raise FileNotFoundError(msg) from e

def get_string_param_value(parameter_to_check: str | None) -> str | None:
    """Process string values from the parameter file.

    :param parameter_to_check: The string value to process
    :type parameter_to_check: str | None
    :return: `None` if `parameter_to_check` is `None`, empty or only whitespace
        and the original string with whitespace trimmed from beginning and end if not
    :rtype: str | None
    """
    if parameter_to_check is None or parameter_to_check == "" or str(parameter_to_check).isspace():
        return None
    # Otherwise apply the strip function just in case
    return str(parameter_to_check).strip()

def get_path_val(fpath: str | Path | None) -> Path | None:
    """Return the Path representation of `fpath` or None if `fpath` is None or empty.

    :param fpath: The filepath to convert
    :type fpath: str | Path | None
    :return: The Path representation of `fpath`
    :rtype: Path | None
    """
    if(isinstance(fpath, str)):
        fpath = get_string_param_value(fpath)
    return Path(fpath) if fpath else None

class ProcessOutputType(Enum, metaclass=CaseInsensitiveEnumMeta):
    """Represents the different sets of outputs the processor should be creating for a job."""

    MINIMAL = 1
    ALL = 2
    CUSTOM = 3
