
import pyblish.api
from reveries import plugins


class FixInvalidNonDefaults(plugins.RepairInstanceAction):

    label = "Set Default Value"
    symptom = "non_default_values"


class FixInvalidConnections(plugins.RepairInstanceAction):

    label = "Remove Inputs"
    symptom = "connections"


class FixInvalidVisibility(plugins.RepairInstanceAction):

    label = "Lock Visibility"
    symptom = "visibility"


class GetInvalidNonDefaults(plugins.MayaSelectInvalidInstanceAction):

    label = "Non Defaults"
    symptom = "non_default_values"


class GetInvalidConnections(plugins.MayaSelectInvalidInstanceAction):

    label = "Invalid Inputs"
    symptom = "connections"


class GetInvalidVisibility(plugins.MayaSelectInvalidInstanceAction):

    label = "Unlocked Visibility"
    symptom = "visibility"


class ValidateRigControllers(pyblish.api.InstancePlugin):
    """Validate rig controllers.

    Controls must have the transformation attributes on their default
    values of translate zero, rotate zero and scale one when they are
    unlocked attributes.

    Unlocked keyable attributes may not have any incoming connections. If
    these connections are required for the rig then lock the attributes.

    The visibility attribute must be locked.

    Note that `repair` will:
        - Lock all visibility attributes
        - Reset all default values for translate, rotate, scale
        - Break all incoming connections to keyable attributes

    """
    order = pyblish.api.ValidatorOrder + 0.11
    label = "Rig Controllers"
    hosts = ["maya"]
    families = [
        "reveries.rig"
    ]
    actions = [
        pyblish.api.Category("Select All"),
        plugins.MayaSelectInvalidInstanceAction,
        pyblish.api.Category("Select Each"),
        GetInvalidNonDefaults,
        GetInvalidConnections,
        GetInvalidVisibility,
        pyblish.api.Category("Fix All"),
        plugins.RepairInstanceAction,
        pyblish.api.Category("Fix Each"),
        FixInvalidNonDefaults,
        FixInvalidConnections,
        FixInvalidVisibility,
    ]

    dependencies = [
        "ValidateRigContents",
    ]

    # Default controller values
    CONTROLLER_DEFAULTS = {
        "translateX": 0,
        "translateY": 0,
        "translateZ": 0,
        "rotateX": 0,
        "rotateY": 0,
        "rotateZ": 0,
        "scaleX": 1,
        "scaleY": 1,
        "scaleZ": 1
    }

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError('{} failed, see log '
                               'information'.format(self.label))

    @classmethod
    def get_controls(cls, instance):
        from maya import cmds

        control_sets = instance.data["controlSets"]

        controls = cmds.sets(control_sets, query=True) or []
        assert controls, "Rig instance's 'ControlSet' is empty"

        return controls

    @classmethod
    def get_invalid(cls, instance):

        if not plugins.depended_plugins_succeed(cls, instance):
            raise Exception("Depended plugin failed. See error log.")

        # Validate all controls
        has_connections = cls.get_invalid_connections(instance)
        has_unlocked_vis = cls.get_invalid_visibility(instance)
        has_non_default_values = cls.get_invalid_non_default_values(instance)

        if has_connections:
            cls.log.error("Controls have input connections: "
                          "%s" % has_connections)

        if has_non_default_values:
            cls.log.error("Controls have non-default values: "
                          "%s" % has_non_default_values)

        if has_unlocked_vis:
            cls.log.error("Controls have unlocked visibility "
                          "attribute: %s" % has_unlocked_vis)

        invalid = []
        if (has_connections or
                has_unlocked_vis or
                has_non_default_values):
            invalid = set()
            invalid.update(has_connections)
            invalid.update(has_non_default_values)
            invalid.update(has_unlocked_vis)
            invalid = list(invalid)
            cls.log.error("Invalid rig controllers. See log for details.")

        return invalid

    @classmethod
    def get_invalid_visibility(cls, instance):
        from maya import cmds

        controls = cls.get_controls(instance)

        has_unlocked_vis = list()
        for control in controls:
            # check if visibility is locked
            plug = "{}.visibility".format(control)
            locked = cmds.getAttr(plug, lock=True)
            if not locked:
                has_unlocked_vis.append(control)

        return has_unlocked_vis

    @classmethod
    def get_invalid_connections(cls, instance):
        controls = cls.get_controls(instance)

        has_connections = list()
        for control in controls:
            if cls._get_connected_attributes(control):
                has_connections.append(control)

        return has_connections

    @classmethod
    def get_invalid_non_default_values(cls, instance):
        controls = cls.get_controls(instance)

        has_non_default_values = list()
        for control in controls:
            if cls._get_non_default_attrs(control):
                has_non_default_values.append(control)

        return has_non_default_values

    @classmethod
    def fix_invalid(cls, instance):
        from reveries.maya import capsule

        controls = cls.get_controls(instance)
        with capsule.undo_chunk(undo_on_exit=False):
            for control in controls:
                cls._fix_visibility(control)
                cls._fix_connections(control)
                cls._fix_non_default_values(control)

    @classmethod
    def fix_invalid_visibility(cls, instance):
        from reveries.maya import capsule

        controls = cls.get_controls(instance)
        with capsule.undo_chunk(undo_on_exit=False):
            for control in controls:
                cls._fix_visibility(control)

    @classmethod
    def fix_invalid_connections(cls, instance):
        from reveries.maya import capsule

        controls = cls.get_controls(instance)
        with capsule.undo_chunk(undo_on_exit=False):
            for control in controls:
                cls._fix_connections(control)

    @classmethod
    def fix_invalid_non_default_values(cls, instance):
        from reveries.maya import capsule

        controls = cls.get_controls(instance)
        with capsule.undo_chunk(undo_on_exit=False):
            for control in controls:
                cls._fix_non_default_values(control)

    @staticmethod
    def _get_connected_attributes(control):
        """Return attribute plugs with incoming connections.

        This will also ensure no (driven) keys on unlocked keyable attributes.

        Args:
            control (str): Name of control node.

        Returns:
            list: The invalid plugs

        """
        from maya import cmds

        attributes = cmds.listAttr(control, keyable=True, scalar=True) or []
        invalid = []
        for attr in attributes:
            plug = "{}.{}".format(control, attr)

            # Ignore locked attributes
            locked = cmds.getAttr(plug, lock=True)
            if locked:
                continue

            # Check for incoming connections
            if cmds.listConnections(plug, source=True, destination=False):
                invalid.append(plug)

        return invalid

    @classmethod
    def _get_non_default_attrs(cls, control):
        """Return attribute plugs with non-default values

        Args:
            control (str): Name of control node.

        Returns:
            list: The invalid plugs

        """
        from maya import cmds

        invalid = []
        for attr, default in cls.CONTROLLER_DEFAULTS.items():
            if cmds.attributeQuery(attr, node=control, exists=True):
                plug = "{}.{}".format(control, attr)

                # Ignore locked attributes
                locked = cmds.getAttr(plug, lock=True)
                if locked:
                    continue

                value = cmds.getAttr(plug)
                if value != default:
                    cls.log.warning("Control non-default value: "
                                    "%s = %s" % (plug, value))
                    invalid.append(plug)

        return invalid

    @classmethod
    def _fix_visibility(cls, control):
        from maya import cmds

        # Lock visibility
        attr = "{}.visibility".format(control)
        locked = cmds.getAttr(attr, lock=True)
        if not locked:
            cls.log.info("Locking visibility for %s" % control)
            cmds.setAttr(attr, lock=True)

    @classmethod
    def _fix_connections(cls, control):
        from maya import cmds

        # Remove incoming connections
        invalid_plugs = cls._get_connected_attributes(control)
        if invalid_plugs:
            for plug in invalid_plugs:
                cls.log.info("Breaking input connection to %s" % plug)
                source = cmds.listConnections(plug,
                                              source=True,
                                              destination=False,
                                              plugs=True)[0]
                cmds.disconnectAttr(source, plug)

    @classmethod
    def _fix_non_default_values(cls, control):
        from maya import cmds

        # Reset non-default values
        invalid_plugs = cls._get_non_default_attrs(control)
        if invalid_plugs:
            for plug in invalid_plugs:
                attr = plug.split(".")[-1]
                default = cls.CONTROLLER_DEFAULTS[attr]
                cls.log.info("Setting %s to %s" % (plug, default))
                cmds.setAttr(plug, default)
