
import os
import sys
import inspect
import types
import logging
import pyblish.api
import avalon.api

from avalon.vendor import six

from ..utils import temp_dir
from .. import CONTRACTOR_PATH


log = logging.getLogger(__name__)


PENDING_SUFFIX = "..Pending.."


class BaseContractor(object):

    def __init__(self):
        self.log = logging.getLogger(self.name)

    def assemble_environment(self, context):
        """Include critical variables with submission
        """
        environment = dict({
            # This will trigger `userSetup.py` on the slave
            # such that proper initialisation happens the same
            # way as it does on a local machine.
            # TODO(marcus): This won't work if the slaves don't
            # have accesss to these paths, such as if slaves are
            # running Linux and the submitter is on Windows.
            "PYTHONPATH": os.getenv("PYTHONPATH", ""),
        }, **avalon.api.Session)

        # Write instances' name and version
        for ind, instance in enumerate(context):
            if not instance.data.get("publish_contractor") == self.name:
                continue

            # instance subset name
            key = "AVALON_DELEGATED_SUBSET_%d" % ind
            environment[key] = instance.data["name"]
            # instance subset version next (for monitor eye debug)
            key = "AVALON_DELEGATED_VERSION_NUM_%d" % ind
            environment[key] = instance.data["version_next"]
            #
            # instance subset version object id
            #
            # This should prevent version bump when re-running publish with
            # same params.
            #
            key = "AVALON_DELEGATED_VERSION_ID_%d" % ind
            environment[key] = instance.data["version_id"]

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


def loader_error_box(title, message):
    from avalon.vendor.Qt import QtWidgets

    log.error(message)
    QtWidgets.QMessageBox.critical(None,
                                   title,
                                   message,
                                   QtWidgets.QMessageBox.Ok)


def loader_warning_box(title, message, optional=False):
    from avalon.vendor.Qt import QtWidgets

    log.warning(message)

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
    """
    name: Representation long name
    ext: The file ext of this Representation's entry file
    """
    attrs = dict(
        __new__=lambda cls: str.__new__(cls, name),
        ext=ext,
        abs_embed=abs_embed,
    )
    Representation = type("Representation", (str,), attrs)
    return Representation()


def pendable_reprs(reprs_prarms):
    reprs = []
    for prarms in reprs_prarms:
        reprs.append(repr_obj(*prarms))
        reprs.append(repr_obj(prarms[0] + PENDING_SUFFIX,
                              prarms[1]))

    return reprs


class EntryFileLoader(avalon.api.Loader):

    def __init__(self, context):
        """Load representation into host application

        Arguments:
            context (dict): avalon-core:context-x.0

        """
        super(EntryFileLoader, self).__init__(context)
        self.repr_dir = self.fname

        repr_name = os.path.basename(self.fname)
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

    def update_entry_path(self):
        self.entry_path = os.path.join(self.fname, self.entry_file)


class PendableLoader(EntryFileLoader):

    def is_pending(self):
        if self.repr_dir.endswith(PENDING_SUFFIX):
            title = "File Pending"
            message = "Pending, wait publish process to complete."
            loader_warning_box(title, message)
            return True
        return False

    def load(self, context, name=None, namespace=None, data=None):
        if self.is_pending():
            return
        self.pendable_load(context, name, namespace, data)

    def update(self, container, representation):
        self.fname = avalon.api.get_representation_path(representation)
        self.update_entry_path()

        if self.is_pending():
            return
        self.pendable_update(container, representation)

    def switch(self, container, representation):
        self.fname = avalon.api.get_representation_path(representation)
        self.update_entry_path()

        if self.is_pending():
            return
        self.pendable_switch(container, representation)

    def pendable_load(self, context, name, namespace, data):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def pendable_update(self, container, representation):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def pendable_switch(self, container, representation):
        """To be implemented by subclass"""
        raise RuntimeError("Loader '{}' does not support 'switch'".format(
            self.label
        ))


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
            # give a fake path
            self.data['stagingDir'] = "/delegating"
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
            # Integrator will not and should not create any dir or copy any
            # file when the representation is on pending
            self.stage_files(repr_ + PENDING_SUFFIX)
