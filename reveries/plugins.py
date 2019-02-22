
import os
import sys
import inspect
import types
import logging
import json
import shutil

import pyblish.api
import avalon.api
import avalon.io

from .vendor import six
from .utils import temp_dir, deep_update
from . import CONTRACTOR_PATH


class BaseContractor(object):
    """Publish delegation contractor base class
    """

    name = ""

    def __init__(self):
        self.log = logging.getLogger(self.name)
        self.__cached_context = None

    def fulfill(self):
        raise NotImplementedError

    def _parse_context(self, context):
        if self.__cached_context is not None:
            return self.__cached_context

        # Save Session
        #
        environment = dict({
            # This will trigger `userSetup.py` on the slave
            # such that proper initialisation happens the same
            # way as it does on a local machine.
            # TODO(marcus): This won't work if the slaves don't
            # have accesss to these paths, such as if slaves are
            # running Linux and the submitter is on Windows.
            "PYTHONPATH": os.getenv("PYTHONPATH", ""),
        }, **avalon.api.Session)

        # Save Context data from source
        #
        context_data_entry = [
            "comment",
            "user",
        ]
        for entry in context_data_entry:
            key = "AVALON_CONTEXT_" + entry
            environment[key] = context.data[entry]

        self.__cached_context = environment
        return environment

    def assemble_environment(self, instance):
        """Compose submission required environment variables for instance

        Return:
            environment (dict): A set of contract variables, return `None` if
                instance is not assigning to this contractor or publish is
                disabled.

        """
        if instance.data.get("publish") is False:
            return
        if instance.data.get("useContractor") is False:
            return
        if not instance.data.get("publishContractor") == self.name:
            return

        context = instance.context
        index = context.index(instance)
        environment = self._parse_context(context).copy()

        # Save Instances' name and version
        #
        # instance subset name
        key = "AVALON_DELEGATED_SUBSET_%d" % index
        environment[key] = instance.data["subset"]
        #
        # instance subset version
        #
        # This should prevent version bump when re-running publish with
        # same params.
        #
        key = "AVALON_DELEGATED_VERSION_NUM_%d" % index
        environment[key] = instance.data["versionNext"]

        return environment


def parse_contract_environment(context):
    """Assign delegated instances via parsing the environment
    """
    assignment = dict()
    os_environ = os.environ.copy()

    AVALON_CONTEXT_ = "AVALON_CONTEXT_"
    AVALON_DELEGATED_SUBSET_ = "AVALON_DELEGATED_SUBSET_"
    AVALON_DELEGATED_VERSION_NUM_ = "AVALON_DELEGATED_VERSION_NUM_"

    for key in os_environ:

        # Context
        if key.startswith(AVALON_CONTEXT_):
            # Read Context data
            #
            entry = key[len(AVALON_CONTEXT_):]
            context.data[entry] = os_environ[key]

        # Instance
        if key.startswith(AVALON_DELEGATED_SUBSET_):
            # Read Instances' name and version
            #
            num_key = key.replace(AVALON_DELEGATED_SUBSET_,
                                  AVALON_DELEGATED_VERSION_NUM_)
            subset_name = os_environ[key]
            version_num = int(os_environ[num_key])

            # Assign instance
            assignment[subset_name] = version_num

            print("Assigned subset {0!r}\n\tVer. Num: {1!r}"
                  "".format(subset_name, version_num))

    print("Found {} delegated instances.".format(len(assignment)))

    # Update context
    context.data["contractorAccepted"] = True
    context.data["contractorAssignment"] = assignment


def find_contractor(contractor_name=""):
    """
    """
    for fname in os.listdir(CONTRACTOR_PATH):
        # Ignore files which start with underscore
        if fname.startswith("_"):
            continue

        mod_name, mod_ext = os.path.splitext(fname)
        if not mod_ext == ".py":
            continue

        abspath = os.path.join(CONTRACTOR_PATH, fname)
        if not os.path.isfile(abspath):
            continue

        module = types.ModuleType(mod_name)
        module.__file__ = abspath

        try:
            with open(abspath) as f:
                six.exec_(f.read(), module.__dict__)

        except Exception as err:
            print("Skipped: \"%s\" (%s)", mod_name, err)
            continue

        for name in dir(module):
            if not name.startswith("Contractor"):
                continue

            # It could be anything at this point
            cls = getattr(module, name)

            if not inspect.isclass(cls):
                continue

            if (hasattr(cls, "assemble_environment") and
                    hasattr(cls, "fulfill") and
                    hasattr(cls, "name")):

                if cls.name == contractor_name:

                    # Store reference to original module, to avoid
                    # garbage collection from collecting it's global
                    # imports, such as `import os`.
                    sys.modules[mod_name] = module

                    return cls
    return None


def create_dependency_instance(dependent,
                               name,
                               family,
                               members,
                               optional=False,
                               category=None):
    """Create dependency instance from dependent instance

    Creating instance for unpublished or stray (not containerized) assets,
    which have dependency relation with current existed instances while
    publishing.

    Example use case, publishing *look* with unpublished textures in Maya.

    Arguments:
        dependent (pyblish.api.Instance): dependent instance
        name (str): dependency instance name and subset name
        family (str): dependency instance's family
        members (list): dependency instance's member
        optional (bool, optional): can be opt-out or not, default False
        category (str, optional): dependency instance's visual category

    """
    if category is None:
        category = family + " (stray)"

    pregenerated_version_id = avalon.io.ObjectId()
    dependent.data["futureDependencies"][name] = pregenerated_version_id

    context = dependent.context

    instance = context.create_instance(name)
    instance[:] = members

    instance.data["id"] = dependent.data["id"]
    instance.data["family"] = family
    instance.data["asset"] = dependent.data["asset"]
    instance.data["subset"] = name
    instance.data["active"] = True
    instance.data["optional"] = optional
    instance.data["category"] = category
    instance.data["pregeneratedVersionId"] = pregenerated_version_id
    # For dependency tracking
    instance.data["dependencies"] = dict()
    instance.data["futureDependencies"] = dict()

    instance.data["objectName"] = dependent.data["objectName"]

    # Move to front, because dependency instance should be integrated before
    # dependent instance
    context.pop()
    context.insert(0, instance)

    return instance


class PackageLoader(object):
    """Load representation into host application

    Arguments:
        context (dict): avalon-core:context-x.0

    """

    def __init__(self, context):
        super(PackageLoader, self).__init__(context)
        self.package_path = self.fname
        self.fname = None  # Do not use

    def file_path(self, file_name):
        return os.path.join(self.package_path, file_name)


def message_box_error(title, message):
    """Prompt error message window"""
    from avalon.vendor.Qt import QtWidgets

    QtWidgets.QMessageBox.critical(None,
                                   title,
                                   message,
                                   QtWidgets.QMessageBox.Ok)


def message_box_warning(title, message, optional=False):
    """Prompt warning dialog with option"""
    from avalon.vendor.Qt import QtWidgets

    opt_btn = QtWidgets.QMessageBox.NoButton
    if optional:
        opt_btn = QtWidgets.QMessageBox.Cancel

    respond = QtWidgets.QMessageBox.warning(None,
                                            title,
                                            message,
                                            QtWidgets.QMessageBox.Ok,
                                            opt_btn)
    if optional:
        return respond == QtWidgets.QMessageBox.Ok


def context_process(process):
    """Decorator, an workaround for pyblish/pyblish-base#250

    This will make instance plugin process only run once, just like
    context plugin.

    And instead of passing `instance` arg, this will change to pass `context`
    to the `process`.

    """

    def _context_process(self, instance):
        context = instance.context
        processed_tag = "_" + self.__class__.__name__ + "_processed_"

        if context.data.get(processed_tag):
            self.log.info("Operated on context level, skipping.")
            return
        # Mark as validated
        context.data[processed_tag] = True

        result = process(self, context)

        return result

    return _context_process


def skip_stage(extractor):
    """Decorator, indicate the extractor will directly save to publish dir

    This will make `PackageExtractor.create_package()` return representation's
    versioned dir in publish space.

    And the `instance.data["stagingDir"]` will be set to versioned dir instead
    of random dir in temp folder. So there should be no file/dir copy while
    intergation since the representation already exists in final destination.

    """

    def _skip_stage(self, *args, **kwargs):
        self._extract_to_publish_dir = True
        result = extractor(self, *args, **kwargs)
        self._extract_to_publish_dir = False

        return result

    return _skip_stage


class PackageExtractor(pyblish.api.InstancePlugin):
    """Reveries' extractor base class

    * This extractor extracts representation as one package(dir), not single
      file.

    * This extractor can extract multiple representations that defined in
      attribute `representations`.

        - If the instance data has `"extractType"` value, then only that type
          of representation will be extracted, instead of extracting all
          supported representations.

        - You MUST implement representation extract method with this function
          nameing: `extract_<representationName>`. For example, if you have
          "mayaAscii" in representations list, then the subclass MUST have
          a method called `extract_mayaAscii`.

    * This extractor will lock version by the context data entry
      `"sourceFingerprint"`.

        - The data `"sourceFingerprint"` is a workfile hashing or any other
          feature data that able to identify the workfile change. This should
          be collected via other collector plugin.

        - Before extraction process started, this extractor will create a
          version dir in publish space, and bind that version dir with current
          workfile's fingerprint.

        - This normally won't happen in production, but if the version dir
          exists, and the fingerprint does not matched, version will bumped
          and create a new version dir to retry (only retry 3 times).
          This will happen if multiple artist publishing same subset with long
          extraction time, or bugs that cause publish fail during extraction.

        - If the version dir exists, and the fingerprint matched, the pre-
          existed content in that version dir will be removed.

        - This ensures the version number of the subset will get, after this
          publish session been completed, no matter what happened during
          long extraction time.

    Example usage:

        ```python

        class ExtractMyWork(PackageExtractor):
            order = pyblish.api.ExtractorOrder
            hosts = ["maya"]
            families = ["reveries.work"]
            representations = [
                "mayaAscii",
                "Alembic",
            ]

            def extract_mayaAscii(self):
                entry_file = self.file_name("ma")
                package_path = self.create_package()
                entry_path = os.path.join(package_path, entry_file)
                self.add_data({"some": "data"})

            def extract_Alembic(self):
                ...

        ```

    Attributes:
        context (pyblish.api.Context): Current pyblish context object
        data (dict): Current pyblish instance data
        member (list): Current pyblish instance members
        representations (list): Names of representations that can be extracted

    """

    families = []
    representations = []

    metadata = ".fingerprint.json"

    def extract(self):
        """Multi-representation extraction process

        Override this method if any pre-extraction job or context is needed.
        For example:

            ```python

            def extract(self):
                # Some pre-extraction job
                self.extra_attr = somthing
                # Pre-extraction context
                with pre_extraction_context:
                    super(MyExtractor, self).extract()

            ```

        """
        extract_methods = list()
        for repr_ in self._active_representations:
            method = getattr(self, "extract_" + repr_, None)
            if method is None:
                msg = ("This extractor does not have the method to "
                       "extract {!r}".format(repr_))
                self.log.error(msg)
                raise AttributeError(msg)

            extract_methods.append((method, repr_))

        for method, repr_ in extract_methods:
            self._current_representation = repr_
            method()

    def process(self, instance):
        """Extractor's main process

        This should NOT be re-implemented.

        """
        self._process(instance)
        self._acquire_version_dir()
        self.extract()

    def _process(self, instance):
        """Pre-extraction process
        """
        self.context = instance.context
        self.data = instance.data
        self.member = instance[:]

        self._active_representations = list()
        self._current_representation = None
        self._extract_to_publish_dir = False
        self._subset_doc = avalon.io.find_one({
            "type": "subset",
            "parent": self.context.data["assetDoc"]["_id"],
            "name": self.data["subset"],
        })

        project = instance.context.data["projectDoc"]
        self._publish_dir_template = project["config"]["template"]["publish"]
        self._publish_dir_key = {"root": avalon.api.registered_root(),
                                 "project": avalon.Session["AVALON_PROJECT"],
                                 "silo": avalon.Session["AVALON_SILO"],
                                 "asset": avalon.Session["AVALON_ASSET"],
                                 "subset": self.data["subset"],
                                 "version": None}

        extract_type = self.data.get("extractType")

        if extract_type is None:
            self.log.debug("No specific extraction type, extract all "
                           "supported type of representations.")
            self._active_representations = self.representations

        elif extract_type in self.representations:
            self._active_representations = [extract_type]

        else:
            msg = "{!r} not supported. This is a bug.".format(extract_type)
            raise RuntimeError(msg)

        if "packages" not in self.data:
            self.data["packages"] = dict()  # representations' data
        if "files" not in self.data:
            self.data["files"] = list()
        if "hardlinks" not in self.data:
            self.data["hardlinks"] = list()

    def _get_next_version(self):
        """Get current subset instance's next version number"""
        version = None
        version_number = 1  # assume there is no version yet, we start at `1`
        if self._subset_doc is not None:
            version = avalon.io.find_one({"type": "version",
                                          "parent": self._subset_doc["_id"]},
                                         {"name": True},
                                         sort=[("name", -1)])

        # if there is a subset there ought to be version
        if version is not None:
            version_number += version["name"]

        return version_number

    def _acquire_version_dir(self, version_locked=False):
        """Get a version dir which binded to current workfile
        """
        version_dir_template = os.path.dirname(self._publish_dir_template)

        def format_version_dir(version_number):
            self._publish_dir_key["version"] = version_number
            version_dir = version_dir_template.format(**self._publish_dir_key)
            # Clean the path
            version_dir = os.path.abspath(os.path.normpath(version_dir))

            return version_dir

        def is_version_matched(version_dir):
            """Does the fingerprint in this version match with workfile ?"""
            metadata_path = os.path.join(version_dir, self.metadata)
            # Load fingerprint from version dir
            with open(metadata_path, "r") as fp:
                metadata = json.load(fp)

            return metadata == self.context.data["sourceFingerprint"]

        def create_version_dir(version_dir):
            """Create a version named dir and dump workfile fingerprint"""
            os.makedirs(version_dir)
            metadata_path = os.path.join(version_dir, self.metadata)
            # Save workfile fingerprint to version dir
            with open(metadata_path, "w") as fp:
                json.dump(self.context.data["sourceFingerprint"], fp, indent=4)

        def clean_version_dir(version_dir):
            """Remove all content from the version dir, except fingerprint"""
            dir_content = os.listdir(version_dir)
            dir_content.remove(self.metadata)

            for item in dir_content:
                item_path = os.path.join(version_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                elif os.path.isfile(item_path):
                    os.remove(item_path)

        # Check
        max_retry_time = 3
        retry_time = 0
        version = self._get_next_version()

        while True:
            if retry_time > max_retry_time:
                msg = "Critical Error: Version Dir retry times exceeded."
                self.log.critical(msg)
                raise Exception(msg)

            elif retry_time:
                self.log.debug("Retry Time: {}".format(retry_time))

            # Bump version
            version_number = version + retry_time
            self.log.debug("Trying Version: {}".format(version_number))
            version_dir = format_version_dir(version_number)
            self.log.debug("Version Dir: {}".format(version_dir))

            if os.path.isdir(version_dir):
                if is_version_matched(version_dir):
                    # This version dir match the current workfile, remove
                    # previous extracted stuff.
                    self.log.debug("Cleaning version dir.")
                    clean_version_dir(version_dir)
                    break

                elif version_locked:
                    # This should not happend.
                    # If the version is locked, the workfile should never
                    # changed.
                    msg = ("Critical Error: Version locked but version dir is "
                           "not available ('sourceFingerprint' not match), "
                           "this is a bug.")
                    self.log.critical(msg)
                    raise Exception(msg)

                else:
                    # Version dir has been created, but the `sourceFingerprint`
                    # not matched because the workfile has changed.
                    # Try next version.
                    pass

            else:
                self.log.debug("Creating version dir.")
                create_version_dir(version_dir)
                break

            retry_time += 1

        self.data["versionNext"] = version_number
        self.data["versionDir"] = version_dir
        self.data["publishDirElem"] = (self._publish_dir_key,
                                       self._publish_dir_template)

        self.log.debug("Next version: {}".format(version_number))
        self.log.debug("Version dir: {}".format(version_dir))

        return version_dir

    def file_name(self, extension, suffix=""):
        """Convenient method for composing file name with default format"""
        return "{subset}{suffix}.{ext}".format(subset=self.data["subset"],
                                               suffix=suffix,
                                               ext=extension)

    def create_package(self):
        """Create representation stage dir

        Register and create a staging directory for extraction usage later on.

        MUST call this in every representation's extraction process.

        The default staging directory is generated by `tempfile.mkdtemp()` with
        "pyblish_tmp_" prefix, but if the extraction method get decorated with
        `skip_stage`, the staging directory will be the publish directory.

        Return:
            repr_dir (str): staging directory

        """
        staging_dir = self.data.get("stagingDir", None)

        if not staging_dir:
            if self._extract_to_publish_dir:
                staging_dir = self.data["versionDir"]
            else:
                staging_dir = temp_dir(prefix="pyblish_tmp_")

            self.data["stagingDir"] = staging_dir

        repr_dir = os.path.join(staging_dir, self._current_representation)

        if os.path.isdir(repr_dir):
            self.log.warning("Representation dir existed, this should not "
                             "happen. Files may overwritten.")
        else:
            os.makedirs(repr_dir)

        return repr_dir

    def add_data(self, data):
        """Add(Update) data to representation

        Arguments:
            data (dict): Additional representation data

        """
        if self._current_representation not in self.data["packages"]:
            self.data["packages"][self._current_representation] = dict()

        deep_update(self.data["packages"][self._current_representation], data)

    def add_file(self, src, dst):
        """Add file to copy queue

        Arguments:
            src (str): Source file path
            dst (str): The path that file needs to be copied to

        """
        self.data["files"].append((src, dst))

    def add_hardlink(self, src, dst):
        """Add file to hardlink queue

        Arguments:
            src (str): Source file path
            dst (str): The path that file needs to be hardlinked to

        """
        self.data["hardlinks"].append((src, dst))


class DelegatablePackageExtractor(PackageExtractor):
    """Reveries' delegatable extractor base class

    This class inherited `PackageExtractor`, and re-implemented the `process`
    method and stuff that enables the ability to skip or run the extraction
    via context and instance data flags.

    If instance data has `"useContractor"` entry and set to `True`, then this
    instance will be delegated.

    If the context data has `"contractorAccepted"` entry and set to `True`,
    which indicate that this publish session is running in contractor, and
    the delegated instance will be extracted.

    The usage is just the same as `PackageExtractor`.

    """

    def process(self, instance):
        """Delegatable extractor's main process

        This should NOT be re-implemented.

        """
        self._process(instance)

        use_contractor = self.data.get("useContractor")
        accepted = self.context.data.get("contractorAccepted")
        on_delegate = use_contractor and not accepted

        # Skip extraction if the instance is going to be delegated

        if on_delegate:
            # The active representations of this instance will be delegated
            # to contractor for remote extraction.
            # Bind with a version dir and skip current extraction.
            self._acquire_version_dir()
            for repr_ in self._active_representations:
                self.log.info("Delegating representation {0} of {1}"
                              "".format(repr_, self.data["name"]))
        else:
            version_locked = False
            if accepted:
                version_locked = True
                self.log.debug("Version Locked.")
            self._acquire_version_dir(version_locked)
            self.extract()

    def _get_next_version(self):
        if self.context.data.get("contractorAccepted"):
            # version lock if publish process has been delegated.
            return self.data["versionNext"]
        else:
            return super(DelegatablePackageExtractor, self)._get_next_version()


def _get_errored_instances_from_context(context, include_warning=False):

    instances = list()
    for result in context.data["results"]:
        if result["instance"] is None:
            # When instance is None we are on the "context" result
            continue

        if result["error"]:
            instances.append(result["instance"])

        if include_warning:
            for record in result["records"]:
                if record.levelname == "WARNING":
                    instances.append(result["instance"])
                    break

    return instances


def _get_errored_plugins_from_data(context):
    """Get all failed validation plugins

    Args:
        context (object):

    Returns:
        list of plugins which failed during validation

    """

    plugins = list()
    results = context.data.get("results", [])
    for result in results:
        if result["success"] is True:
            continue
        plugins.append(result["plugin"])

    return plugins


class OnSymptomAction(pyblish.api.Action):
    """Action baseclass that able to work with validation plugin via `symptom`

    The action will try to find the corresponded class method in Plugin by the
    `symptom` and `_prefix` attribute in Action class.

    """
    label = None
    on = None
    icon = None
    _prefix = None
    symptom = ""

    def _get_action(self, plugin):
        symptom = ("_" + self.symptom) if self.symptom else ""
        action_name = self._prefix + symptom
        if not hasattr(plugin, action_name):
            raise RuntimeError("Plug-in does not have {!r} method."
                               "".format(action_name))

        return getattr(plugin, action_name)


_FIX = "fix_invalid"
_GET = "get_invalid"


class RepairInstanceAction(OnSymptomAction):
    """Repair instances

    To process the repairing this requires a `fix(instance)` classmethod
    is available on the plugin.

    """
    label = "Repair"
    on = "failed"
    icon = "wrench"

    _prefix = _FIX
    symptom = ""

    def process(self, context, plugin):

        action = self._get_action(plugin)

        # Get the errored instances
        self.log.info("Finding failed instances..")
        errored_instances = _get_errored_instances_from_context(context)

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(errored_instances, plugin)
        for instance in instances:
            action(instance)


class RepairContextAction(OnSymptomAction):
    """Repair context

    To process the repairing this requires a `fix()` classmethod
    is available on the plugin.

    """
    label = "Repair Context"
    on = "failed"
    icon = "wrench"

    _prefix = _FIX
    symptom = ""

    def process(self, context, plugin):

        action = self._get_action(plugin)

        # Get the errored instances
        self.log.info("Finding failed instances..")
        errored_plugins = _get_errored_plugins_from_data(context)

        # Apply pyblish.logic to get the instances for the plug-in
        if plugin in errored_plugins:
            self.log.info("Attempting fix ...")
            action(context)


class SelectInvalidInstanceAction(OnSymptomAction):
    """Select invalid nodes from instance

    To retrieve the invalid nodes this assumes a static `get_invalid()`
    method is available on the plugin.

    """
    label = "Select invalid"
    on = "failed"
    icon = "search"

    _prefix = _GET
    symptom = ""

    def process(self, context, plugin):

        action = self._get_action(plugin)

        errored_instances = _get_errored_instances_from_context(
            context, include_warning=True)

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(errored_instances, plugin)

        # Get the invalid nodes for the plug-ins
        self.log.info("Finding invalid nodes..")
        invalid = list()

        for instance in instances:
            invalid_ = action(instance)

            if invalid_:
                if isinstance(invalid_, (list, tuple)):
                    invalid.extend(invalid_)
                elif isinstance(invalid_, dict):
                    invalid.extend(invalid_.keys())
                else:
                    self.log.warning("Plug-in returned to be invalid, "
                                     "but has no selectable nodes.")

        if invalid:
            invalid = list(set(invalid))
            self.log.info("Selecting invalid nodes: %s" % ", ".join(invalid))
            self.select(invalid)
        else:
            self.log.info("No invalid nodes found.")
            self.deselect()

    def select(self, invalid):
        raise NotImplementedError

    def deselect(self):
        raise NotImplementedError


class SelectInvalidContextAction(OnSymptomAction):
    """Select invalid nodes from context

    To retrieve the invalid nodes this assumes a static `get_invalid()`
    method is available on the plugin.

    """
    label = "Select invalid"
    on = "failed"
    icon = "search"

    _prefix = _GET
    symptom = ""

    def process(self, context, plugin):

        action = self._get_action(plugin)

        # Get the invalid nodes for the plug-ins
        self.log.info("Finding invalid nodes..")
        invalid = action(context)

        if invalid:
            if isinstance(invalid, (list, tuple)):
                pass
            elif isinstance(invalid, dict):
                invalid = list(invalid.keys())
            else:
                self.log.warning("Plug-in returned to be invalid, "
                                 "but has no selectable nodes.")

            self.log.info("Selecting invalid nodes: %s" % ", ".join(invalid))
            self.select(invalid)

        else:
            self.log.info("No invalid nodes found.")
            self.deselect()

    def select(self, invalid):
        raise NotImplementedError

    def deselect(self):
        raise NotImplementedError
