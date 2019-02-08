
import pyblish.api
import avalon.maya


MODEL_LOADER = "ModelLoader"


class CollectRig(pyblish.api.InstancePlugin):
    """Collect rig related data
    """

    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["maya"]
    label = "Collect Rig"
    families = ["reveries.rig"]

    def process(self, instance):
        from maya import cmds

        loaded_models = list()
        namespace_allowed = list()

        for container in avalon.maya.ls():
            # Find loaded model via Loader cls name
            if not container["loader"] == MODEL_LOADER:
                continue

            group = container["subsetGroup"]
            members = cmds.sets(container["objectName"], query=True)
            namespace_allowed += cmds.ls(members,
                                         long=True,
                                         referencedNodes=True)
            namespace_allowed.append(group)
            loaded_models.append(group)

        instance.data["loadedModels"] = loaded_models
        instance.data["namespaceAllowed"] = namespace_allowed
