
import pyblish.api


class CollectRig(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["maya"]
    label = "Collect Rig"
    families = ["reveries.rig"]

    def get_controlsets(self, instance):
        from maya import cmds
        return [i for i in cmds.ls(instance, type="objectSet")
                if i == "ControlSet"]

    def get_outsets(self, instance):
        from maya import cmds
        return [i for i in cmds.ls(instance, type="objectSet")
                if i.endswith("OutSet")]  # Include other OutSets

    def process(self, instance):
        instance.data["controlSets"] = self.get_controlsets(instance)
        instance.data["outSets"] = self.get_outsets(instance)
