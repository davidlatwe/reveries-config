
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
from .utils import temp_dir
from . import CONTRACTOR_PATH


class BaseContractor(object):

    name = ""

    def __init__(self):
        self.log = logging.getLogger(self.name)

    def fulfill(self):
        raise NotImplementedError

    def assemble_environment(self, context):
        """Include critical variables with submission
        """

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

        # Save Instances' name and version
        #
        for ind, instance in enumerate(context):
            if instance.data.get("publish") is False:
                continue

            if instance.data.get("useContractor") is False:
                continue

            if not instance.data.get("publishContractor") == self.name:
                continue

            # instance subset name
            key = "AVALON_DELEGATED_SUBSET_%d" % ind
            environment[key] = instance.data["name"]
            #
            # instance subset version
            #
            # This should prevent version bump when re-running publish with
            # same params.
            #
            key = "AVALON_DELEGATED_VERSION_NUM_%d" % ind
            environment[key] = instance.data["versionNext"]

        return environment


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
    """

    def _skip_stage(self, *args, **kwargs):
        self._extract_to_publish_dir = True
        result = extractor(self, *args, **kwargs)
        self._extract_to_publish_dir = False

        return result

    return _skip_stage


class PackageExtractor(pyblish.api.InstancePlugin):
    """Reveries' extractor base class.

    """

    families = []

    metadata = ".fingerprint.json"

    def process(self, instance):
        """
        """
        self._process(instance)
        self._get_version_dir()
        self.extract()

    def _process(self, instance):
        self._active_representations = list()
        self._current_representation = None
        self._extract_to_publish_dir = False
        self._version_locked = False

        self.context = instance.context
        self.data = instance.data
        self.member = instance[:]
        self.subset_doc = avalon.io.find_one({
            "type": "subset",
            "parent": self.data["assetDoc"]["_id"],
            "name": self.data["subset"],
        })

        project = instance.context.data["projectDoc"]

        self._publish_path = project["config"]["template"]["publish"]

        self._publish_key = {"root": avalon.api.registered_root(),
                             "project": avalon.api.Session["AVALON_PROJECT"],
                             "silo": avalon.api.Session["AVALON_SILO"],
                             "asset": avalon.api.Session["AVALON_ASSET"],
                             "subset": self.data["subset"],
                             "version": None}

        format_ = self.data.get("format")

        if format_ is None:
            self.log.debug("No specific format, extract all supported type "
                           "of representations.")
            self._active_representations = self.representations

        elif format_ in self.representations:
            self._active_representations = [format_]

        else:
            msg = "{!r} not supported. This is a bug.".format(format_)
            raise RuntimeError(msg)

        if "packages" not in self.data:
            self.data["packages"] = dict()

        if "files" not in self.data:
            self.data["files"] = list()

        if "hardlinks" not in self.data:
            self.data["hardlinks"] = list()

    def _get_version(self):
        version = None
        version_number = 1  # assume there is no version yet, we start at `1`
        if self.subset_doc is not None:
            version = avalon.io.find_one({"type": "version",
                                          "parent": self.subset_doc["_id"]},
                                         {"name": True},
                                         sort=[("name", -1)])

        # if there is a subset there ought to be version
        if version is not None:
            version_number += version["name"]

        return version_number

    def _get_version_dir(self):
        """
        """

        # Lacking the representation, extract version dir instead
        version_dir_template = os.path.dirname(self._publish_path)

        def format_version_dir(version_number):
            self._publish_key["version"] = version_number
            version_dir = version_dir_template.format(**self._publish_key)
            # Clean the path
            version_dir = os.path.abspath(os.path.normpath(version_dir))

            return version_dir

        # Check
        max_retry_time = 3
        retry_time = 0
        version = self._get_version()

        while True:
            if retry_time > max_retry_time:
                msg = "Critical Error: Version Dir retry times exceeded."
                self.log.critical(msg)
                raise Exception(msg)

            elif retry_time:
                self.log.debug("Retry Time: {}".format(retry_time))

            version_number = version + retry_time
            self.log.debug("Trying Version: {}".format(version_number))

            version_dir = format_version_dir(version_number)
            self.log.debug("Version Dir: {}".format(version_dir))

            if os.path.isdir(version_dir):
                if self._verify_version_dir(version_dir):
                    self.log.debug("Cleaning version dir.")
                    self._clean_version_dir(version_dir)
                    break

                elif self._version_locked:
                    msg = ("Critical Error: Version locked but version dir is "
                           "not available ('sourceFingerprint' not match), "
                           "this is a bug.")
                    self.log.critical(msg)
                    raise Exception(msg)

            else:
                self.log.debug("Booking version dir.")
                self._book_version_dir(version_dir)
                break

            retry_time += 1

        self.data["publishDirElem"] = (self._publish_key, self._publish_path)
        self.data["versionNext"] = version_number
        self.data["versionDir"] = version_dir

        self.log.debug("Next version: {}".format(version_number))
        self.log.debug("Version dir: {}".format(version_dir))

        return version_dir

    def _verify_version_dir(self, version_dir):
        metadata_path = os.path.join(version_dir, self.metadata)
        with open(metadata_path, "r") as fp:
            metadata = json.load(fp)

        return metadata == self.context.data["sourceFingerprint"]

    def _book_version_dir(self, version_dir):
        os.makedirs(version_dir)
        metadata_path = os.path.join(version_dir, self.metadata)
        with open(metadata_path, "w") as fp:
            json.dump(self.context.data["sourceFingerprint"], fp, indent=4)

    def _clean_version_dir(self, version_dir):
        dir_content = os.listdir(version_dir)
        dir_content.remove(self.metadata)

        for item in dir_content:
            item_path = os.path.join(version_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            elif os.path.isfile(item_path):
                os.remove(item_path)

    def extract(self):
        """
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

    def file_name(self, extension, suffix=""):
        return "{subset}{suffix}.{ext}".format(subset=self.data["subset"],
                                               suffix=suffix,
                                               ext=extension)

    def create_package(self, entry_fname):
        """Create representation dir

        This should only be called in actual extraction process.

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

        repr_data = {
            "entry_fname": entry_fname,
        }
        # Stage package for integration
        self.data["packages"][self._current_representation] = repr_data

        return repr_dir

    def add_data(self, data):
        """
        """
        self.data["packages"][self._current_representation].update(data)


class DelegatablePackageExtractor(PackageExtractor):

    def process(self, instance):
        """
        """
        self._process(instance)

        use_contractor = self.data.get("useContractor")
        accepted = self.context.data.get("contractorAccepted")
        on_delegate = use_contractor and not accepted

        if on_delegate:
            self._get_version_dir()
            self._delegate()
        else:
            if accepted:
                self._version_locked = True
                self.log.debug("Version Locked.")
            self._get_version_dir()
            self.extract()

    def _get_version(self):
        # get version
        if self.context.data.get("contractorAccepted"):
            # version lock if publish process has been delegated.
            return self.data["versionNext"]
        else:
            return super(DelegatablePackageExtractor, self)._get_version()

    def _delegate(self):
        for repr_ in self._active_representations:
            self.log.info("Delegating representation {0} of {1}"
                          "".format(repr_, self.data["name"]))


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


class RepairInstanceAction(pyblish.api.Action):
    """Repair instances

    To process the repairing this requires a `fix(instance)` classmethod
    is available on the plugin.

    """
    label = "Repair"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "wrench"  # Icon from Awesome Icon

    def process(self, context, plugin):

        if not hasattr(plugin, "fix"):
            raise RuntimeError("Plug-in does not have fix method.")

        # Get the errored instances
        self.log.info("Finding failed instances..")
        errored_instances = _get_errored_instances_from_context(context)

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(errored_instances, plugin)
        for instance in instances:
            plugin.fix(instance)


class RepairContextAction(pyblish.api.Action):
    """Repair context

    To process the repairing this requires a `fix()` classmethod
    is available on the plugin.

    """
    label = "Repair Context"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "wrench"  # Icon from Awesome Icon

    def process(self, context, plugin):

        if not hasattr(plugin, "fix"):
            raise RuntimeError("Plug-in does not have fix method.")

        # Get the errored instances
        self.log.info("Finding failed instances..")
        errored_plugins = _get_errored_plugins_from_data(context)

        # Apply pyblish.logic to get the instances for the plug-in
        if plugin in errored_plugins:
            self.log.info("Attempting fix ...")
            plugin.fix(context)


class SelectInvalidAction(pyblish.api.Action):
    """Select invalid nodes from instance

    To retrieve the invalid nodes this assumes a static `get_invalid()`
    method is available on the plugin.

    """
    label = "Select invalid"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "search"  # Icon from Awesome Icon

    symptom = ""

    def process(self, context, plugin):

        errored_instances = _get_errored_instances_from_context(
            context, include_warning=True)

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(errored_instances, plugin)

        invalid_getter_name = "get_invalid"
        if self.symptom:
            invalid_getter_name = "get_invalid_" + self.symptom

        if not hasattr(plugin, invalid_getter_name):
            raise RuntimeError("Plug-in does not have {!r} method."
                               "".format(invalid_getter_name))

        invalid_getter = getattr(plugin, invalid_getter_name)

        # Get the invalid nodes for the plug-ins
        self.log.info("Finding invalid nodes..")
        invalid = list()
        for instance in instances:
            invalid_nodes = invalid_getter(instance)
            if invalid_nodes:
                if isinstance(invalid_nodes, (list, tuple)):
                    invalid.extend(invalid_nodes)
                elif isinstance(invalid_nodes, dict):
                    invalid.extend(invalid_nodes.keys())
                else:
                    self.log.warning("Plug-in returned to be invalid, "
                                     "but has no selectable nodes.")

        # Ensure unique (process each node only once)
        invalid = list(set(invalid))

        if invalid:
            self.log.info("Selecting invalid nodes: %s" % ", ".join(invalid))
            self.select(invalid)
        else:
            self.log.info("No invalid nodes found.")
            self.deselect()

    def select(self, invalid):
        raise NotImplementedError

    def deselect(self):
        raise NotImplementedError
