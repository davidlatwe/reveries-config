
import pyblish.api
from reveries.plugins import RepairInstanceAction


class ValidateLookHasRenderPartition(pyblish.api.InstancePlugin):
    """Ensure all shadingEngines are included in renderPartition

    All shadingEngine nodes' ".partition" attribute must connected
    to "renderPartition.sets".

    """

    order = pyblish.api.ValidatorOrder
    label = "Has Render Partition"
    hosts = ["maya"]
    families = [
        "reveries.look",
    ]
    actions = [
        pyblish.api.Category("Auto Fix"),
        RepairInstanceAction,
    ]

    DEFAULT_RENDER_PARTITION = "renderPartition.sets"

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        invalid = list()

        shading_engines = cmds.ls(instance, type="shadingEngine")
        for render_set in shading_engines:
            attr = render_set + ".partition"
            for conn in cmds.listConnections(attr,
                                             type="partition",
                                             plugs=True) or []:
                if conn.startswith(cls.DEFAULT_RENDER_PARTITION):
                    break
            else:
                invalid.append(render_set)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            self.log.error(
                "'%s' has shaders that has no render partition:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("%s has shaders that has no render "
                            "partition." % instance)

    @classmethod
    def fix_invalid(cls, instance):
        from maya import cmds

        for render_set in cls.get_invalid(instance):
            attr = render_set + ".partition"
            cmds.connectAttr(attr,
                             cls.DEFAULT_RENDER_PARTITION,
                             nextAvailable=True)
