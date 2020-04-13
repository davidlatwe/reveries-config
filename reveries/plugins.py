
import os
import pyblish.api
import avalon.api
import avalon.io


def depended_plugins_succeed(plugin, instance):
    """Lookup context for depended plugins results

    Args:
        plugin (pyblish.api.Plugin): pyblish plugin object
        instance (pyblish.plugin.Instance): pyblish Instance object

    Returns:
        (bool): True if all depended plugins has succeed, else False

    """
    dependencies = getattr(plugin, "dependencies", None)
    if not dependencies:
        plugin.log.warning("No depended plugins.")
        return True

    succeed = True

    for result in instance.context.data["results"]:
        if result["instance"] is None:
            continue
        if result["instance"].id != instance.id:
            continue

        previous = result["plugin"].__name__
        success = result["success"]

        if previous in dependencies and not success:
            plugin.log.error("Depended plugin failed: %s" % previous)
            succeed = False

    return succeed


def create_dependency_instance(dependent,
                               name,
                               family,
                               members,
                               optional=False,
                               sublabel=None,
                               data=None):
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
        sublabel (str, optional): Additional description

    """
    category = dependent.data.get("category",
                                  dependent.data["family"])
    label = "%s (%s)" % (dependent.data["subset"],
                         sublabel or family.split(".", 1)[-1])

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
    instance.data["label"] = label
    instance.data["pregeneratedVersionId"] = pregenerated_version_id
    # For dependency tracking
    instance.data["dependencies"] = dict()
    instance.data["futureDependencies"] = dict()

    instance.data["objectName"] = dependent.data["objectName"]

    if "childInstances" not in dependent.data:
        dependent.data["childInstances"] = list()
    dependent.data["childInstances"].append(instance)
    instance.data["isDependency"] = True

    if data is not None:
        instance.data.update(data)

    # Move to front, because dependency instance should be integrated before
    # dependent instance
    context.pop()
    context.insert(context.index(dependent), instance)

    return instance


class PackageLoader(object):
    """Load representation into host application

    Arguments:
        context (dict): avalon-core:context-x.0

    """

    def __init__(self, context):
        # Complete override `avalon.api.Load.__init__`

        template = context["project"]["config"]["template"]["publish"]

        data = {
            key: value["name"]
            for key, value in context.items()
        }

        representation = context["representation"]
        repr_root = representation["data"].get("reprRoot")
        root = repr_root or avalon.api.registered_root()

        data["root"] = root
        data["silo"] = context["asset"]["silo"]

        package_path = template.format(**data)
        self.package_path = package_path
        # Keep Avalon `api.Loader` default attribute `fname`
        self.fname = package_path

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


# Decorator
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


def get_errored_instances_from_context(context, include_warning=False):

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
        self.log.debug("Finding failed instances..")
        errored_instances = get_errored_instances_from_context(context)

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
        errored_plugins = get_errored_plugins_from_data(context)

        # Apply pyblish.logic to get the instances for the plug-in
        if plugin in errored_plugins:
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

        errored_instances = get_errored_instances_from_context(
            context, include_warning=True)

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(errored_instances, plugin)

        # Get the invalid nodes for the plug-ins
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
            self.select(invalid)
        else:
            self.log.info("No invalid nodes found.")
            self.deselect()

    def select(self, invalid):
        raise NotImplementedError("Should be implemented in subclass.")

    def deselect(self):
        raise NotImplementedError("Should be implemented in subclass.")


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
        invalid = action(context)

        if invalid:
            if isinstance(invalid, (list, tuple)):
                pass
            elif isinstance(invalid, dict):
                invalid = list(invalid.keys())
            else:
                self.log.warning("Plug-in returned to be invalid, "
                                 "but has no selectable nodes.")
            self.select(invalid)

        else:
            self.log.info("No invalid nodes found.")
            self.deselect()

    def select(self, invalid):
        raise NotImplementedError("Should be implemented in subclass.")

    def deselect(self):
        raise NotImplementedError("Should be implemented in subclass.")


class MayaSelectInvalidInstanceAction(SelectInvalidInstanceAction):

    def select(self, invalid):
        from maya import cmds
        cmds.select(invalid, replace=True, noExpand=True)

    def deselect(self):
        from maya import cmds
        cmds.select(deselect=True)


class MayaSelectInvalidContextAction(SelectInvalidContextAction):
    """ Select invalid nodes in context"""

    def select(self, invalid):
        from maya import cmds
        cmds.select(invalid, replace=True, noExpand=True)

    def deselect(self):
        from maya import cmds
        cmds.select(deselect=True)


class HoudiniSelectInvalidInstanceAction(SelectInvalidInstanceAction):

    def select(self, invalid):
        self.deselect()
        for node in invalid:
            node.setSelected(True)

    def deselect(self):
        import hou
        hou.clearAllSelected()


class HoudiniSelectInvalidContextAction(SelectInvalidContextAction):
    """ Select invalid nodes in context"""

    def select(self, invalid):
        self.deselect()
        for node in invalid:
            node.setSelected(True)

    def deselect(self):
        import hou
        hou.clearAllSelected()
