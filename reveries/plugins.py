
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

    def __init__(self):
        self.log = logging.getLogger(self.name)

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


def repr_obj(name, ext, abs_embed=False):
    """Generate representation object for asset I/O plugins

    Arguments:
        name (str): Representation long name, also as representation dir name
        ext (str): The file ext of this Representation's entry file
        abs_embed (bool): Indicate this representation require directly write
            into final location, due to the absolute path of the representation
            components are embedded in entry file.

    """
    attrs = dict(
        __new__=lambda cls: str.__new__(cls, name),
        ext=ext,
        abs_embed=abs_embed,
    )
    Representation = type("Representation", (str,), attrs)
    return Representation()


class EntryFileLoader(avalon.api.Loader):

    def __init__(self, context):
        """Load representation into host application

        Arguments:
            context (dict): avalon-core:context-x.0

        """
        super(EntryFileLoader, self).__init__(context)
        self.repr_dir = self.fname

        repr_name = os.path.basename(self.repr_dir)
        try:
            index = self.representations.index(repr_name)
            representation = self.representations[index]
            # entry file name will be the same in every version
            self.entry_file = "{subset}.{representation.ext}".format(
                subset=context["subset"]["name"],
                representation=representation
            )
        except ValueError:
            if not self.representations == ["*"]:
                raise
            self.entry_file = ""

        self.update_entry_path()

    def update_entry_path(self, representation=None):
        if representation is not None:
            self.repr_dir = avalon.api.get_representation_path(representation)
        self.entry_path = os.path.join(self.repr_dir, self.entry_file)

    def update(self, container, representation):
        self.update_entry_path(representation)

        self.pendable_update(container, representation)


class BaseExtractor(pyblish.api.InstancePlugin):
    """Extractor base class.

    The extractor base class implements a "staging_dir" function used to
    generate a temporary directory for an instance to extract to.

    This temporary directory is generated through `tempfile.mkdtemp()`

    """

    active_representations = []

    extract_to_publish_dir = False

    context = None
    data = None
    member = None
    fname = None

    def pre_process(self, instance):
        self.context = instance.context
        self.data = instance.data
        self.member = instance[:]
        self.fname = instance.data["subset"]

        self.representation_check()

        if "files" not in self.data:
            self.data["files"] = list()

    def process(self, instance):
        """
        """
        self.pre_process(instance)
        self.dispatch()

    def representation_check(self):
        format_ = self.data.get("format")
        representations = self.representations[:]

        if format_ is None:
            self.log.debug("No specific format, extract all supported type "
                           "of representations.")
        else:
            try:
                index = representations.index(format_)
            except ValueError:
                msg = "{!r} not supported.".format(format_)
                raise RuntimeError(msg)
            else:
                representations = [representations[index]]

        abs_embed_count = 0
        for repr_ in representations:
            if not(hasattr(repr_, "ext") and hasattr(repr_, "abs_embed")):
                msg = "Require a Representation object to work."
                raise TypeError(msg)

            if repr_.abs_embed:
                abs_embed_count += 1

        self.active_representations = representations
        self.extract_to_publish_dir = bool(abs_embed_count)

    def dispatch(self):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def extract(self):
        """
        """
        extract_methods = list()
        for repr_ in self.active_representations:
            method = getattr(self, "extract_" + repr_, None)
            if method is None:
                self.log.error("This extractor does not have the method to "
                               "extract {!r}".format(repr_))
            extract_methods.append((method, repr_))

        for method, repr_ in extract_methods:
            method(repr_)

    @property
    def staging_dir(self):
        """Provide a temporary directory in which to store extracted files

        Upon calling this method the staging directory is stored inside
        the instance.data['stagingDir']
        """
        staging_dir = self.data.get('stagingDir', None)

        if not staging_dir:
            if self.extract_to_publish_dir:
                staging_dir = self.data["publish_dir"]
            else:
                staging_dir = temp_dir(prefix="pyblish_tmp_")

            self.data['stagingDir'] = staging_dir

        return staging_dir

    def extraction_dir(self, representation):
        """Create representation dir

        This should only be called in actual extraction process.

        """
        repr_dir = os.path.join(self.staging_dir, representation)
        if os.path.isdir(repr_dir):
            self.log.warning("Representation dir existed, this should not "
                             "happen. Files may overwritten.")
        else:
            os.makedirs(repr_dir)

        return repr_dir

    def extraction_fname(self, representation):
        """
        """
        return "{subset}.{repr.ext}".format(subset=self.fname,
                                            repr=representation)

    def stage_files(self, representation):
        """
        """
        self.data["files"].append(representation)


class DelegatableExtractor(BaseExtractor):

    delegating = False

    def process(self, instance):
        """
        """
        self.pre_process(instance)
        self.delegation_check()

        if self.delegating:
            self.pend()
        else:
            self.dispatch()

    def delegation_check(self):
        use_contractor = self.data.get("use_contractor")
        accepted = self.context.data.get("contractor_accepted")
        if use_contractor and not accepted:
            self.delegating = True
        else:
            self.delegating = False

    def pend(self):
        for repr_ in self.active_representations:
            self.log.info("Delegating representation {0} of {1}"
                          "".format(repr_, self.data["name"]))


def get_errored_instances_from_context(context):

    instances = list()
    for result in context.data["results"]:
        if result["instance"] is None:
            # When instance is None we are on the "context" result
            continue

        if result["error"]:
            instances.append(result["instance"])

    return instances


def get_errored_plugins_from_data(context):
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
        errored_instances = get_errored_instances_from_context(context)

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
        errored_plugins = get_errored_plugins_from_data(context)

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

        errored_instances = get_errored_instances_from_context(context)

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
