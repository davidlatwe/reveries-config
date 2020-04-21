
import pyblish.api
from reveries import plugins


class MakeDrivesUnique(plugins.RepairInstanceAction):

    label = "Make Drives Unique"


class ValidateRenderAOVDriverUnique(pyblish.api.InstancePlugin):
    """Arnold AOV output driver should be unique

    If an AOV has multiple outputs and using same AOV driver, some
    of them may not generate any output due to Arnold says they are
    duplicated in rendering time, even filters are not the same.

    Fixing this is simple for most of the cases, since those AOVs
    outputs are most likely connected to `defaultArnoldDriver`.

    Just re-select a new driver from driver dropdown list in Render
    Settings window's AOVs tab will resolved the problem. (Not the
    one that has `<` and `>` surrounded)

    """

    label = "AOV Unique Driver"
    order = pyblish.api.ValidatorOrder + 0.2
    hosts = ["maya"]
    families = [
        "reveries.renderlayer",
    ]
    actions = [
        pyblish.api.Category("Select"),
        plugins.MayaSelectInvalidInstanceAction,
        # pyblish.api.Category("Fix It"),
        # MakeDrivesUnique,
        # (TODO) See comments below in `fix_invalid` and `set_override`
    ]

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds
        from reveries.maya import arnold

        invalid = list()

        renderlayer = instance.data["renderlayer"]
        aov_nodes = arnold.get_arnold_aov_nodes(renderlayer)

        for aov_node in aov_nodes:

            drivers = cmds.listConnections(aov_node + ".outputs[*].driver",
                                           source=True,
                                           destination=False)
            if not drivers:
                continue

            if not len(drivers) == len(set(drivers)):
                invalid.append(aov_node)

        return invalid

    def process(self, instance):
        from maya import cmds

        renderer = instance.data["renderer"]
        renderlayer = instance.data["renderlayer"]

        if renderer == "arnold":

            invalid = self.get_invalid(instance)
            if invalid:
                for aov_node in invalid:
                    aov_name = cmds.getAttr(aov_node + ".name")

                    self.log.error("AOV %s in renderLayer %s has non-unique "
                                   "driver." % (aov_name, renderlayer))

                raise Exception("AOV drivers is not unique.")

    @classmethod
    def fix_invalid(cls, instance):
        from maya import cmds
        from mtoa.ui import aoveditor
        from reveries.maya import lib

        interest_attrs = {
            # EXR
            "exrCompression": {},
            "halfPrecision": {},
            "preserveLayerName": {},
            "exrTiled": {},
            "autocrop": {},
            "append": {},
            "mergeAOVs": {},
            # PNG, JPEG
            "pngFormat": {"type": "string"},
            "outputPadded": {},
            "dither": {},
            "quality": {},
            # Advanced Output
            "prefix": {"type": "string"},
            "outputMode": {"type": "string"},
            "colorManagement": {"type": "string"},
            # Extra
            "aiUserOptions": {"type": "string"},
            "alphaTolerance": {},
            "depthTolerance": {},
            "alphaHalfPrecision": {},
            "depthHalfPrecision": {},
        }

        renderlayer = instance.data["renderlayer"]

        invalid = cls.get_invalid(instance)
        for aov_node in invalid:
            drivers = list()

            connections = cmds.listConnections(aov_node + ".outputs[*].driver",
                                               source=True,
                                               destination=False,
                                               connections=True)
            connections = iter(connections)
            for dst, src in zip(connections, connections):
                if src not in drivers:
                    drivers.append(src)
                    continue

                new = cmds.createNode("aiAOVDriver")
                type = cmds.getAttr(src + ".aiTranslator")
                cmds.setAttr(new + ".aiTranslator", type, type="string")

                # Coopy attributes
                for attr, args in interest_attrs.items():
                    origin = cmds.getAttr(src + "." + attr)
                    if lib.has_renderlayer_override(src, attr):
                        set_override(src, new, attr, renderlayer)
                        # (TODO) Set value to overrided renderlayer is not
                        #        implemented.
                    else:
                        cmds.setAttr(new + "." + attr, origin, **args)

                # Connect new driver to AOV node
                cmds.connectAttr(new + ".message", dst, force=True)

        aoveditor.refreshArnoldAOVTab()


def set_override(old, new, attr, renderlayer):
    from maya import cmds
    from reveries.maya import lib

    if not lib.is_using_renderSetup():
        cmds.editRenderLayerAdjustment(new + "." + attr, layer=renderlayer)
        # (TODO) Set value to overrided renderlayer is not
        #        implemented.
        return

    # RenderSetup
    # Add new node into collection (selector)
