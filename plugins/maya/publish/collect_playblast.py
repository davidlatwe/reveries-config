
import pyblish.api
from maya import cmds


class CollectPlayblast(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder - 0.299
    hosts = ["maya"]
    label = "Collect Playblast"
    families = [
        "reveries.imgseq.playblast"
    ]

    def process(self, instance):

        context = instance.context

        current_layer = cmds.editRenderLayerGlobals(query=True,
                                                    currentRenderLayer=True)
        layer_members = cmds.editRenderLayerMembers(current_layer,
                                                    query=True,
                                                    fullNames=True)

        member = instance[:]
        member += cmds.listRelatives(member,
                                     allDescendents=True,
                                     fullPath=True) or []

        instance.data.update({
            "startFrame": context.data["startFrame"],
            "endFrame": context.data["endFrame"],
            "byFrameStep": 1,
            "renderCam": cmds.ls(member, type="camera", long=True),
            "category": "Playblast",
        })

        # Push renderlayer members into instance,
        # for collecting dependencies
        instance += layer_members

        # Assign contractor
        if instance.data["deadlineEnable"]:
            instance.data["useContractor"] = True
            instance.data["publishContractor"] = "deadline.maya.script"
