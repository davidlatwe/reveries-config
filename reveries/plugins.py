
import os
import sys
import inspect
import types
import logging
import pyblish.api
import avalon.api

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

        # Save Context data
        #
        context_data_entry = ["comment", "user"]
        for entry in context_data_entry:
            key = "AVALON_CONTEXT_" + entry
            environment[key] = context.data[entry]

        # Save Instances' name and version
        #
        for ind, instance in enumerate(context):
            if not instance.data.get("publish_contractor") == self.name:
                continue

            if instance.data.get("publish") is False:
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
            environment[key] = instance.data["version_next"]

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


class PackageLoader(avalon.api.Loader):
    """Load representation into host application

    Arguments:
        context (dict): avalon-core:context-x.0

    """

    families = list()
    representations = list()

    def __init__(self, context):
        super(PackageLoader, self).__init__(context)
        self.package_path = self.fname
        self.fname = None  # Do not use

    def file_path(self, file_name):
        return os.path.join(self.package_path, file_name)


def message_box_error(title, message):
    from avalon.vendor.Qt import QtWidgets

    QtWidgets.QMessageBox.critical(None,
                                   title,
                                   message,
                                   QtWidgets.QMessageBox.Ok)


def message_box_warning(title, message, optional=False):
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


class PackageExtractor(pyblish.api.InstancePlugin):
    """Reveries' extractor base class.

    """

    families = []

    def process(self, instance):
        """
        """
        self._process(instance)
        self.extract()

    def _process(self, instance):
        self._active_representations = list()
        self._current_representation = None
        self._extract_to_publish_dir = False

        self.context = instance.context
        self.data = instance.data
        self.member = instance[:]
        self.fname = instance.data["subset"]

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

        if "auxiliaries" not in self.data:
            self.data["auxiliaries"] = list()

    def direct_publish(extractor):
        """Decorator, indicate the extractor will directly save to publish dir
        """
        def _direct_publish(self, *args, **kwargs):
            self._extract_to_publish_dir = True
            result = extractor(self, *args, **kwargs)
            self._extract_to_publish_dir = False

            return result

        return _direct_publish

    def extract(self):
        """
        """
        extract_methods = list()
        for repr_ in self._active_representations:
            method = getattr(self, "extract_" + repr_, None)
            if method is None:
                self.log.error("This extractor does not have the method to "
                               "extract {!r}".format(repr_))
            extract_methods.append((method, repr_))

        for method, repr_ in extract_methods:
            self._current_representation = repr_
            method()

    def file_name(self, extension, suffix=""):
        return "{subset}{suffix}.{ext}".format(subset=self.fname,
                                               suffix=suffix,
                                               ext=extension)

    def create_package(self, entry_fname):
        """Create representation dir

        This should only be called in actual extraction process.

        """
        staging_dir = self.data.get('stagingDir', None)

        if not staging_dir:
            if self._extract_to_publish_dir:
                staging_dir = self.data["publish_dir"]
            else:
                staging_dir = temp_dir(prefix="pyblish_tmp_")

            self.data['stagingDir'] = staging_dir

        repr_dir = os.path.join(staging_dir, self._current_representation)

        if os.path.isdir(repr_dir):
            self.log.warning("Representation dir existed, this should not "
                             "happen. Files may overwritten.")
        else:
            os.makedirs(repr_dir)

        data = {
            "entry_fname": entry_fname,
        }
        self._stage_package(data)

        return repr_dir

    def _stage_package(self, data):
        # Stage package for integration
        self.data["packages"][self._current_representation] = data

    def add_data(self, data):
        """
        """
        self.data["packages"][self._current_representation].update(data)


class DelegatablePackageExtractor(PackageExtractor):

    def process(self, instance):
        """
        """
        self._process(instance)

        use_contractor = self.data.get("use_contractor")
        accepted = self.context.data.get("contractor_accepted")
        on_delegate = use_contractor and not accepted

        if on_delegate:
            self.delegate()
        else:
            self.extract()

    def delegate(self):
        for repr_ in self._active_representations:
            self.log.info("Delegating representation {0} of {1}"
                          "".format(repr_, self.data["name"]))


def _get_errored_instances_from_context(context):

    instances = list()
    for result in context.data["results"]:
        if result["instance"] is None:
            # When instance is None we are on the "context" result
            continue

        if result["error"]:
            instances.append(result["instance"])

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

        errored_instances = _get_errored_instances_from_context(context)

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
