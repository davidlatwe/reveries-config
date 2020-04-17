
import pyblish.api
from reveries import plugins


class RepairInvalid(plugins.RepairInstanceAction):

    label = "Reset To Default"


class ValidateShapeRenderStats(pyblish.api.Validator):
    """Ensure all render stats are set to the default values."""

    label = "Shape Render Stats"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    families = [
        "reveries.model",
    ]
    actions = [
        pyblish.api.Category("Select"),
        plugins.MayaSelectInvalidInstanceAction,
        pyblish.api.Category("Fix"),
        RepairInvalid,
    ]

    defaults = {
        "castsShadows": 1,
        "receiveShadows": 1,
        "motionBlur": 1,
        "primaryVisibility": 1,
        "smoothShading": 1,
        "visibleInReflections": 1,
        "visibleInRefractions": 1,
        "doubleSided": 1,
        "opposite": 0,
    }

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        # It seems the "surfaceShape" and those derived from it have
        # `renderStat` attributes.
        shapes = cmds.ls(instance, long=True, type="surfaceShape")
        invalid = []
        for shape in shapes:
            for attr, default_value in cls.defaults.iteritems():
                if cmds.attributeQuery(attr, node=shape, exists=True):
                    value = cmds.getAttr("{}.{}".format(shape, attr))
                    if value != default_value:
                        invalid.append(shape)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Shapes with non-default renderStats "
                             "found: {0}".format(invalid))

    @classmethod
    def fix_invalid(cls, instance):
        from maya import cmds

        for shape in cls.get_invalid(instance):
            for attr, default_value in cls.defaults.iteritems():

                if cmds.attributeQuery(attr, node=shape, exists=True):
                    plug = "{0}.{1}".format(shape, attr)
                    value = cmds.getAttr(plug)
                    if value != default_value:
                        cmds.setAttr(plug, default_value)
