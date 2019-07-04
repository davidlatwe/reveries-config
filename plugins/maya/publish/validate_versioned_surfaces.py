
import pyblish.api
from avalon.pipeline import AVALON_CONTAINER_ID
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectInvalid(MayaSelectInvalidInstanceAction):

    label = "Select Not Versioned"


class ValidateVersionedSurfaces(pyblish.api.InstancePlugin):
    """All surface node in scene should be part of versioned subset

    Should be containerized or instance that is going to be published

    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Has Versioned Surfaces"
    families = [
        # (NOTE) Exclude `reveries.imgseq` because this takes long time on
        #        big scene when publishing render.
        # "reveries.imgseq",
        "reveries.standin",
    ]

    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
    ]

    @classmethod
    def get_invalid(cls, instance):
        from reveries.maya import lib
        from maya import cmds

        containers = lib.lsAttr("id", AVALON_CONTAINER_ID)

        surfaces = cmds.ls(instance,
                           type="surfaceShape",
                           noIntermediate=True,
                           long=True)
        # Check on transform node
        transforms = set(cmds.listRelatives(surfaces,
                                            parent=True,
                                            fullPath=True) or [])
        has_versioned = set()
        # Is node being containerized ?
        for node in transforms:
            for set_ in cmds.listSets(object=node) or []:
                if set_ in containers:
                    has_versioned.add(node)
                    break

        not_containerized = transforms - has_versioned
        other_instances = [i for i in instance.context
                           if (i.data["family"] not in cls.families and
                               i.data.get("publish", True))]
        # Is node being publish ?
        for node in not_containerized:
            for inst in other_instances:
                if node in inst:
                    has_versioned.add(node)
                    break

        # Or hidden ?
        start = instance.data["startFrame"]
        end = instance.data["endFrame"]
        step = instance.data["byFrameStep"]

        not_versioned_visible = set()
        not_versioned = transforms - has_versioned
        for node in not_versioned:
            frame = start
            while frame < end:
                if lib.is_visible(node, time=frame):
                    not_versioned_visible.add(node)
                    break
                frame += step

        return list(not_versioned_visible)

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            self.log.warning("Surface node not versioned.")

            # Add log data, this entry will be written into database
            instance.data["hasUnversionedSurfaces"] = True

            for i in invalid:
                self.log.debug(i)
