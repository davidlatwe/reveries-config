
import pyblish.api
from maya import cmds
from reveries.plugins import context_process


class CollectPlayblast(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder - 0.299
    hosts = ["maya"]
    label = "Collect Playblast"
    families = [
        "reveries.imgseq.playblast"
    ]

    @context_process
    def process(self, context):

        original = None
        # Remove dummy `imgseq.playblast` instances
        for instance in list(context):
            if self.families[0] in instance.data.get("families", []):

                original = instance.data.get("objectName")

                context.remove(instance)
        assert original is not None, "This is a bug."

        current_layer = cmds.editRenderLayerGlobals(query=True,
                                                    currentRenderLayer=True)
        layer_members = cmds.editRenderLayerMembers(current_layer, query=True)
        layer_members = cmds.ls(layer_members, long=True)
        layer_members += cmds.listRelatives(layer_members,
                                            allDescendents=True,
                                            fullPath=True) or []

        member = cmds.sets(original, query=True)
        member += cmds.listRelatives(member,
                                     allDescendents=True,
                                     fullPath=True) or []

        data = {
            "objectName": original,
            "startFrame": context.data["startFrame"],
            "endFrame": context.data["endFrame"],
            "byFrameStep": 1,
            "renderCam": cmds.ls(member, type="camera"),
        }

        get = (lambda a: cmds.getAttr(original + "." + a, asString=True))
        data.update({k: get(k) for k in [
            "asset",
            "subset",
            "renderType",
            "deadlineEnable",
            "deadlinePool",
            "deadlineGroup",
            "deadlinePriority",
        ]})

        data["category"] = "Playblast"
        data["family"] = "reveries.imgseq"
        data["families"] = self.families[:]

        # For dependency tracking
        data["dependencies"] = dict()
        data["futureDependencies"] = dict()

        instance = context.create_instance(data["subset"])
        instance.data.update(data)

        # Push renderlayer members into instance,
        # for collecting dependencies
        instance += list(set(layer_members))

        # Assign contractor
        if instance.data["deadlineEnable"]:
            instance.data["useContractor"] = True
            instance.data["publishContractor"] = "deadline.maya.script"
