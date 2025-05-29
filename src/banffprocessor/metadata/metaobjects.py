import inspect # noqa: I001
import operator

from pathlib import Path
from typing import Any
from xml.parsers.expat import ExpatError

import duckdb

import banffprocessor.processor_logger as plg
from banffprocessor.exceptions import EmptyMetadataFileError, MetadataConstraintError

from banffprocessor.metadata import models
from banffprocessor.nls import _
from banffprocessor.metadata.models.metadataclass import MetadataClass
from banffprocessor.metadata.models.algorithms import Algorithms
from banffprocessor.metadata.models.editgroups import Editgroups
from banffprocessor.metadata.models.edits import Edits
from banffprocessor.metadata.models.estimators import Estimators
from banffprocessor.metadata.models.expressions import Expressions
from banffprocessor.metadata.models.jobs import Jobs
from banffprocessor.metadata.models.processcontrols import ProcessControls, ProcessControlType
from banffprocessor.metadata.models.processoutputs import ProcessOutputs
from banffprocessor.metadata.models.uservars import Uservars
from banffprocessor.metadata.models.varlists import Varlists
from banffprocessor.metadata.models.weights import Weights

log_lcl = plg.get_processor_child_logger("metadata")

class MetaObjects:
    """Container class for collections of metadata objects."""

    # The total number of job steps in the validated job sequence
    total_job_steps: int
    # The set of unique proc names in the validated job sequence
    job_proc_names: set[str]

    @property
    def dbconn(self) -> duckdb.DuckDBPyConnection | None:
        """The currently connected database used to store metadata objects.

        :return: The duckdbpyconnection currently being used to store metadata objects.
        :rtype: duckdb.DuckDBPyConnection | None
        """
        return self._dbconn

    #Current implementation is based on a simple dictionary.
    #- Keys are the name of the object type (which for metadata objects is the filename
    #    with no extension and a capitalized first character, i.e. donorspecs.xml -> Donorspecs)
    #- Values are lists of objects with the same type as the key name, where each
    #    object should be one line or entry in the corresponding metadata table or file

    def __init__(self, metadata_folder: str | Path | None = None, job_id: str | None = None,
                 dbconn: duckdb.DuckDBPyConnection | None = None) -> None:
        """Construct a MetaObjects object.

        :param metadata_folder: The directory to load metadata files from, defaults to None
        :type metadata_folder: str | Path | None, optional
        :param job_id: The job_id to be run and whose job steps to validate, defaults to None
        :type job_id: str | None, optional
        :attribute total_job_steps: Used for tracking progress when performing execute()
        :type total_job_steps: int
        :raises FileNotFoundError: If the required Jobs metadata file cannot be found
        :raises EmptyMetadataFileError: If the required Jobs metadata file is empty
        :raises ExpatError: If there is an issue while reading the XML data from file
        """
        self.meta_dict = {}
        self.module_to_class = {}
        self._dbconn = dbconn
        if self._dbconn is None:
            self._dbconn = duckdb.connect(database=":memory:")
            self._is_private_connection = True
        else:
            self._is_private_connection = False

        self.total_job_steps = None

        # Build a list of classes that inherit from the MetadataClass in the metdata.models sub-module
        for mod_name in models.__all__:
            # Get the module itself and get its underlying class if it is a sub-class
            # of the MetadataClass super-class (also skipping MetadataClass itself)
            mod_tuple = inspect.getmembers(getattr(models, mod_name),
                                            predicate=lambda o: inspect.isclass(o) and
                                            issubclass(o, MetadataClass) and
                                            o != MetadataClass)
            if(mod_tuple):
                # module names should already be lower case but just in case
                self.module_to_class[mod_name.casefold()] = mod_tuple[0][1]
        self.initialize_metadata()

        if(metadata_folder):
            # Grab the list of metadata files from the metadata folder
            metadata_files = Path(metadata_folder).glob("*.xml")

            # Currently loads all metadata files including Jobs entries and then
            # expects the main processor loop to perform the jobid filter to get the list it needs.
            # Alternatively we could perform that filter on load from file if we need the
            # extra memory and there's no need for jobs entries under other jobids
            for file in metadata_files:
                try:
                    metadata_module_name = file.stem.casefold()
                    if(metadata_module_name in self.module_to_class):
                        # If the filename is the name of a metadata class, remove the
                        # class reference itself from our map
                        cls = self.module_to_class.get(metadata_module_name)
                        self.load_xml_file(file, cls)
                    else:
                        # If the file has a name that doesn't correspond with a metadata
                        # class, just skip it and log
                        msg = _("The following metadata file did not correspond to any existing "
                                "metadata model and was skipped: {}.").format(file.name)
                        log_lcl.info(msg)
                        continue
                except EmptyMetadataFileError:
                    msg = _("Provided metadata file {} contains no valid entries.").format(file.name)
                    log_lcl.exception(msg)
                    raise
                except ExpatError:
                    msg = _("Unable to read XML in {} metadata file.").format(file.name)
                    log_lcl.exception(msg)
                    raise

            if(Jobs.get_record_count(dbconn=self._dbconn) == 0):
                msg = _("Required Jobs metadata not found or unable to be read.")
                log_lcl.exception(msg)
                raise MetadataConstraintError(msg)

            self.job_proc_names, self.total_job_steps = self.validate_job_sequence(job_steps=self.meta_dict[Jobs.__name__], job_id=job_id)
            self.check_constraints()
            self.display_load_summary()

    def __del__(self) -> None:
        self.cleanup_metadata()
        if self._is_private_connection:
            self._dbconn.close()

    def load_xml_file(self, metadata_file: Path, cls: type[MetadataClass]) -> None:
        """Load the metadata found in `metadata_file` into this class:`src.banffprocessor.metadata.MetaObjects` object.

        The new entry added will have a key of the `cls` name and value of a collection of objects
        of type `cls`.

        :param metadata_file: The path of the XML file to load
        :type metadata_file: pathlib.Path
        :param cls: The metadata object type to load the file into
        :type cls: type[:class:`src.banffprocessor.metadata.MetadataClass`]
        :raises EmptyMetadataFileError: If the metadata file does not contain any valid entries
        :raises MetadataConstraintError: If an entry in the metadata file contains values
            that violate the constraints on the object type being loaded
        """
        metafile_dict = cls.load_xml(metadata_file)
        meta_objs = []
        for index, entry in enumerate(metafile_dict[cls.__name__.casefold()], start=1):
            try:
                new_obj = cls(**entry, dbconn=self._dbconn)
                meta_objs.append(new_obj)
            except MetadataConstraintError as e:
                log_lcl.exception()
                msg = _("Metadata constraint violated while processing {} on entry {}").format(metadata_file.name, index)
                log_lcl.exception(msg)
                raise MetadataConstraintError(msg) from e

        # Add list of metadata objects to our collection
        self.add_objects_of_single_type(meta_objs)

    def add_objects_of_single_type(self, objects: list["MetadataClass"]) -> None:
        """Add a list of metadata objects all of the same type to the MetaObjects collection which can be retrieved using their type.

        Only one list per object type can be added; if a second is added it will overwrite the original list stored under that type.

        :param objects: The list of metadata objects to load
        :type objects: list[:class:`src.banffprocessor.metadata.MetadataClass`]
        :raises ValueError: If `objects` is empty or `None`
        :raises TypeError: If `objects` contains objects of more than one type
        """
        if(not objects):
            msg = _("'objects' list is empty.")
            log_lcl.exception(msg)
            raise ValueError(msg)

        objects_type = type(objects[0])
        if(not all(isinstance(obj, objects_type) for obj in objects)):
            msg = _("All objects in 'objects' list must be the same type.")
            log_lcl.exception(msg)
            raise TypeError(msg)

        if(objects_type == ProcessControls):
            objects = MetaObjects._load_process_control_dict(objects)

        self.meta_dict[objects_type.__name__] = objects

    @staticmethod
    def validate_job_sequence(job_steps: list["Jobs"], job_id: str | None = None) -> tuple[set[str], int]:
        """Iterate through `job_steps` and validates the sequence of all steps and process blocks contained/referenced in the job with `job_id`.

        If `job_id` is not provided, the first job found in `job_steps` will be used as the starting point.
        Returns a list of the unique proc names contained in the job sequence.

        :param job_steps: A collection of Jobs metadata objects
        :type job_steps: list[Jobs]
        :param job_id: The job_id to be run and whose job steps to validate, defaults to None
        :type job_id: str | None, optional
        :raises MetadataConstraintError: If a job step of process "JOB" has a specid pointing
            to a job_id that does not exist in the current Jobs metadata collection
        :raises MetadataConstraintError: If a cycle exists in the graph of job_steps (i.e. a
            step points to a process block which points back to the calling block, thus creating
            an infinite loop)
        :return: A set of the unique proc names contained in the job sequence and the total number
            of job steps across the entire job.
        :rtype: tuple[set[str], int]
        """
        jobs_by_block = {}
        root_id = job_id
        # Group our jobs by jobid to separate each job block
        for job in job_steps:
            if(not root_id):
                # If no job_id was provided we assume the first set of steps is the root job
                root_id = job.jobid

            if(job.jobid in jobs_by_block):
                jobs_by_block[job.jobid].append(job)
            else:
                jobs_by_block[job.jobid] = [job]

        # Sort each block on seqno
        for block in jobs_by_block.values():
            block.sort(key=operator.attrgetter("seqno"))

        unique_proc_names = set()
        current_blocks = []
        total_step_count = 0

        class BinaryNode:
            def __init__(self, job: Jobs) -> None:
                self.left = None
                self.right = None
                self.data = job

        def add_block_to_graph(block_job_id: str, parent_node: BinaryNode = None) -> None:
            # Keep track of the blocks that are currently in sequence to avoid cycles
            current_blocks.append(block_job_id)

            if(block_job_id not in jobs_by_block):
                msg = _("No job steps were found with job_id {}.").format(block_job_id)
                log_lcl.exception(msg)
                raise MetadataConstraintError(msg)

            prev_node = parent_node
            # Iterate over the job and build our graph out from there
            for step in jobs_by_block[block_job_id]:
                new_node = BinaryNode(step)

                # Every new node increases the step count
                #NOTE: Can just take a total graph node count at the end if using a proper graphing library
                nonlocal total_step_count
                total_step_count += 1

                # If we aren't the root we need to add an edge to the last node
                if(prev_node):
                    if(prev_node.left):
                        prev_node.right = new_node
                    else:
                        prev_node.left = new_node

                prev_node = new_node

                # Save a list of all unique process names in the list of visited job steps
                nonlocal unique_proc_names
                unique_proc_names.add(step.process)

                if(step.process == "job"):
                    # If we revisit a block that we've already added in the current sequence,
                    # we have found a cycle
                    if(step.specid in current_blocks):
                        msg = _("The Jobs sequence rooted at job_id {} contains a "
                                "cycle caused by job_id {} at seqno {}. As this will result "
                                "in an infinite loop the job must be rewritten to remove the "
                                "cycle.").format(root_id, block_job_id, step.seqno)
                        log_lcl.exception(msg)
                        raise MetadataConstraintError(msg)
                    # Otherwise recursively add this block (and its sub-blocks) to the graph
                    add_block_to_graph(step.specid, parent_node=prev_node)

            # The block is completely processed, it may now be re-visited without cycling
            current_blocks.remove(block_job_id)

        add_block_to_graph(root_id)

        #NOTE: Preferably just return a graph containing all nodes which reference a jobs object
        # then the graph f'ns can be used to get this info indirectly
        return unique_proc_names, total_step_count

    @staticmethod
    def _load_process_control_dict(controls: list[ProcessControls]) -> dict[str, Any]:
        """Load a list of :class:`src.banffprocessor.metadata.ProcessControls` to a
        dict mapping controlids to dicts mapping targetfile names to the operations to
        perform on them, which are dicts of the operation type to the ProcessControls
        object with the control value.

        {
            "controlid1234": {
                "indata": {
                    ProcessControlType.ROW_FILTER: [ProcessControls1, ProcessControls2],
                    ProcessControlType.COLUMN_FILTER: [ProcessControls3, ProcessControls4],
                },
            },
        }

        :param controls: List of :class:`src.banffprocessor.metadata.ProcessControls` objects
            to add to a dictionary
        :type controls: list[ProcessControls]
        :return: The dictionary containing the categorized mappings of `controls`
        :rtype: dict[str, Any]
        """
        control_dict = {}
        for control in controls:
            if control.controlid in control_dict:
                file_to_type = control_dict[control.controlid]
            else:
                file_to_type = {}
                control_dict[control.controlid] = file_to_type

            if control.targetfile in file_to_type:
                type_to_control = file_to_type[control.targetfile]
            else:
                type_to_control = {}
                file_to_type[control.targetfile] = type_to_control

            if control.parameter in type_to_control:
                type_to_control[control.parameter].append(control)
            else:
                type_to_control[control.parameter] = [control]

        return control_dict

    def get_objects_of_type(self, cls: type[MetadataClass]) -> list[MetadataClass] | dict[str, Any]:
        """Get the list of metadata objects of type `cls`.

        If no objects are found, an empty list is returned.

        :param cls: The class reference of the object type to fetch
        :type cls: type[:class:`src.banffprocessor.metadata.MetadataClass`]
        :return: A list of all type `cls` objects found in this `MetaObjects` object or a special
            dictionary if objects are of type :class:`src.banffprocessor.metadata.ProcessControls`
        :rtype: list[:class:`src.banffprocessor.metadata.MetadataClass`] | dict[str, Any]
        """
        if(cls.__name__ not in self.meta_dict):
            return []
        return self.meta_dict[cls.__name__]

    def get_job_steps(self, jobid: str | None) -> list[Jobs]:
        """Get and returns the list of Jobs objects with `jobid` sorted in ascending order of their seqno.

        If no objects are found under the `jobid` an empty list is returned.

        :param jobid: The class reference of the object type to fetch
        :type jobid: str | None
        :return: A list of the :class:`src.banffprocessor.metadata.Jobs` objects
            with jobid `jobid`
        :rtype: list[:class:`src.banffprocessor.metadata.Jobs`]
        """
        if(not jobid or Jobs.__name__ not in self.meta_dict):
            return []

        return sorted([x for x in self.meta_dict[Jobs.__name__] if x.jobid == jobid],
                      key=operator.attrgetter("seqno"))

    def get_specs_obj(self, cls: type[MetadataClass], specid: str) -> MetadataClass:
        """Get and return the object of type `cls` with the specid `specid`.

        Only one result should be found for the specified `specid` as it is effectively
        a primary key for its metadata table. If no object is found for the specid
        `None` is returned.

        :param cls: The metadata object type to search for
        :type cls: type[:class:`src.banffprocessor.metadata.MetadataClass`]
        :param specid: The specid to match on objects of type `cls`
        :type specid: str
        :raises MetadataConstraintError: If multiple :class:`src.banffprocessor.metadata.MetadataClass`
            objects are found under `specid`
        :return: The object with type `cls` and specid `specid` or `None` if
            not found
        :rtype: :class:`src.banffprocessor.metadata.MetadataClass`
        """
        if(not specid or cls.__name__ not in self.meta_dict):
            return None

        spec_objs = [x for x in self.meta_dict[cls.__name__] if x.specid == specid]

        # SpecID should be essentially a primary key in a Spec table (can be repeated in Jobs table)
        if(len(spec_objs) > 1):
            msg = _("Multiple entries using same specid ({}) in {} table. "
                    "SpecIDs must be unique in Spec tables.").format(specid, cls.__name__)
            log_lcl.exception(msg)
            raise MetadataConstraintError

        return (spec_objs[0] if spec_objs else None)

    def get_varlist_fieldids(self, varid: str | None) -> list[str]:
        """Given a list of varlist objects gets and returns the list of fieldids of the varlist
        objects associated with the specified varid and sorts it on seqno.

        If no variables are found under the varid, an empty list is returned.

        :param varid: the ID to filter the varlists on
        :type varid: str | None
        :return: A list of varlist objects with varid `varid` sorted on their `seqno` and
            an empty list if no objects are found
        :rtype: list[str]
        """
        if(not varid):
            return []

        varlists = self.get_objects_of_type(Varlists)
        return [y.fieldid for y in sorted([x for x in varlists if x.varlistid == varid],
                                          key=operator.attrgetter("seqno"))]

    def get_edits_string(self, editgroupid: str) -> str:
        """Get and return a string containing the list of edits in the :class:`src.banffprocessor.metadata.Edits`
        objects associated with the specified `editgroupid`.

        The string is formed by concatenating the formed edit strings from the edits objects
        with a semi-colon and space as well as prepending each edit with its modifier (if present)
        and a colon and space. If no edits are found under the `editgroupid`, an empty string is returned.

        i.e. "PASS: a > b; FAIL: c + d <= e; f - g = h;"

        :param editgroupid: the ID to filter the :class:`src.banffprocessor.metadata.Editgroups` on
        :type editgroupid: str
        :return: The semi-colon separated list of formed edits as a single string, empty
            if no edits were found
        :rtype: str
        """
        if(not editgroupid):
            return ""

        editgroups = self.get_objects_of_type(Editgroups)
        edits = self.get_objects_of_type(Edits)
        edits_list = [x.edit for x in edits if x.editid in
                        [y.editid for y in editgroups if y.editgroupid == editgroupid]
                     ]

        return " ".join(edits_list)

    def get_weights_string(self, weightid: str) -> str:
        """Get and return a string containing the list of weights in the
        :class:`src.banffprocessor.metadata.Weights` objects
        associated with the specified `weightid` sorted in descending order by weight,
        and formed by concatenating the formed weight strings from the objects with a
        semi-colon and space.

        If no :class:`src.banffprocessor.metadata.Weights` are found under the `weightid`,
        an empty string is returned.

        i.e. "field1=9.0; field2=7.0; field3=5.0;"

        :param weightid: the ID to filter the :class:`src.banffprocessor.metadata.Weights` on
        :type weightid: str
        :return: The semi-colon separated list of formed weights as a single string, empty
            if no :class:`src.banffprocessor.metadata.Weights` were found
        :rtype: str
        """
        if(not weightid):
            return ""

        weights = self.get_objects_of_type(Weights)
        weight_string_list = [y.weight_string for y in
                              sorted([x for x in weights if x.weightid == weightid],
                                     key=operator.attrgetter("weight"), reverse=True)
                             ]

        return " ".join(weight_string_list)

    def get_expression(self, exprid: str) -> str:
        """Get the expression string associated with the specified `exprid`.

        :param exprid: The identifier of the Expression to get.
        :type exprid: str
        :return: The `expressions` field value of the Expression object fetched.
        :rtype: str
        """
        return Expressions.get_expression(exprid, dbconn=self._dbconn)

    def get_estimators(self, estid: str) -> list[Estimators]:
        """Get and return the list of :class:`src.banffprocessor.metadata.Estimators` objects
        associated with the specified `estid` and sorted by their `seqno`.

        If no variables are found under the `estid`, an empty list is returned.

        :param estid: the ID to filter the :class:`src.banffprocessor.metadata.Estimators` on
        :type estid: str
        :return: A list of :class:`src.banffprocessor.metadata.Estimators` objects or an
            empty list if no :class:`src.banffprocessor.metadata.Estimators` are found under
            the `estid`
        :rtype: list[:class:`src.banffprocessor.metadata.Estimators`]
        """
        if(not estid):
            return []

        estimators = self.get_objects_of_type(Estimators)
        return sorted([x for x in estimators if x.estimatorid == estid], key=operator.attrgetter("seqno"))

    def get_user_vars_dict(self, specid: str, process: str) -> dict[str,str]:
        """Get Uservars objects identified by the `specid` and `process` and return a dict mapping
        the Uservars `var` to its `value`.

        :param specid: The specid identifying Uservars to fetch.
        :type specid: str
        :param process: The process value of the Uservars to fetch.
        :type process: str
        :return: A dictionary mapping the fetched Uservars `var` field to their `value`
        :rtype: dict[str,str]
        """
        return Uservars.uservars_to_dict(specid, process, dbconn=self._dbconn)

    def get_algorithm(self, algorithmname: str) -> Algorithms | None:
        """Get and return the :class:`src.banffprocessor.metadata.Algorithms` object associated with the specified `algorithmname`.

        :param algorithmname: The algorithmname of the :class:`src.banffprocessor.metadata.Algorithms`
            object to retrieve
        :return: The :class:`src.banffprocessor.metadata.Algorithms` object with the specified
            `algorithmname`
        :rtype: :class:`src.banffprocessor.metadata.Algorithms` | None
        """
        if(not algorithmname):
            return None

        algorithms = self.get_objects_of_type(Algorithms)
        algo = next((x for x in algorithms if x.algorithmname.upper() == algorithmname.upper()), None)
        if algo is None:
            # If is key is provided and not found, we should return an error.
            msg = _("The following value was not found: {} = '{}'.").format("algorithms.algorithm_name", algorithmname)
            raise ValueError(msg)
        return algo

    def get_process_controls(self, controlid: str) -> dict[str, dict[ProcessControlType, list[ProcessControls]]]:
        """Get and return a mapping of targetfile names to a dict of `parameter` values to
        their list of :class:`src.banffprocessor.metadata.ProcessControls` objects associated
        with the specified `controlid`.

        The lists are sorted on the enum value of the `parameter`
        field to ensure that a regular list traversal will always pass over controls in
        the order that they should be applied to the `target_file`.
        If no variables are found under the `controlid`, an empty dict is returned.

        i.e.
        {
            "indata": {
                ProcessControlType.ROW_FILTER: [ProcessControls1, ProcessControls2],
                ProcessControlType.COLUMN_FILTER: [ProcessControls3, ProcessControls4],
            },
        }

        :param controlid: the ID to filter the :class:`src.banffprocessor.metadata.ProcessControls` on
        :type controlid: str
        :return: A dict of target file names mapped to dicts of
            :class:`src.banffprocessor.metadata.ProcessControlType` mapped to lists of
            :class:`src.banffprocessor.metadata.ProcessControls` of that type for
            that targetfile, or an empty list if no records are found under the `controlid`
        :rtype: dict[str, :class:`src.banffprocessor.metadata.ProcessControls`]
        """
        if(not controlid):
            return {}

        controls = self.get_objects_of_type(ProcessControls)
        if(controlid not in controls):
            return {}

        return controls[controlid]

    def get_process_outputs(self, process: str) -> list[str]:
        """Get and return the list of output_name strings for `process`.
        If no objects are found under `process` an empty list is returned.

        :param process: The name of the process value to retrieve records of
        :type process: str
        :return: A list of the output_name attributes of the
            :class:`banffprocessor.metadata.ProcessOutputs` objects with process `process`
        :rtype: list[str]
        """
        if(not process or ProcessOutputs.__name__ not in self.meta_dict):
            return []

        return [x.output_name for x in self.meta_dict[ProcessOutputs.__name__] if x.process == process.casefold()]

    def initialize_metadata(self) -> None:
        """Perform the initialize() method on each metadata class type loaded to this object."""
        for cls in self.module_to_class.items():
            cls[1].initialize(dbconn=self._dbconn)

    def cleanup_metadata(self) -> None:
        """Perform the cleanup() method on each metadata class type loaded to this object."""
        for cls in self.module_to_class.items():
            cls[1].cleanup(dbconn=self._dbconn)

    def check_constraints(self) -> None:
        """Perform the check_constraints method on each metadata class type loaded to this object."""
        for cls in self.module_to_class.items():
            cls[1].check_constraints(dbconn=self._dbconn)

    def display_load_summary(self) -> None:
        """Display a summary of the Metadata files that were loaded to memory."""
        border_string = "="*100
        summary = "\n" + border_string
        summary += _("\n Metadata Load Summary \n")
        summary += border_string + "\n"
        for cls in self.module_to_class.items():
            summary += f"   {cls[0].capitalize() : <30} {cls[1].get_record_count(dbconn=self._dbconn)  : >10} \n"
        summary += border_string + "\n"
        log_lcl.info(summary)
        summary.format()
