
import contextlib
import pyblish.api


class ExtractLightSet(pyblish.api.InstancePlugin):
    """Export lights for rendering"""

    label = "Extract LightSet"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.lightset"]

    def process(self, instance):
        from maya import cmds
        from avalon import maya
        from reveries import utils
        from reveries.maya import capsule

        staging_dir = utils.stage_dir()
        filename = "%s.ma" % instance.data["subset"]
        outpath = "%s/%s" % (staging_dir, filename)

        instance.data["repr.LightSet._stage"] = staging_dir
        instance.data["repr.LightSet._files"] = [filename]
        instance.data["repr.LightSet.entryFileName"] = filename

        # Extract lights
        #
        self.log.info("Extracting lights..")

        # From texture extractor
        child_instances = instance.data.get("childInstances", [])
        try:
            texture = next(chd for chd in child_instances
                           if chd.data["family"] == "reveries.texture")
        except StopIteration:
            file_node_attrs = dict()
        else:
            file_node_attrs = texture.data.get("fileNodeAttrs", dict())

        with contextlib.nested(
            maya.maintained_selection(),
            capsule.attribute_values(file_node_attrs),
            capsule.no_refresh(),
        ):
            cmds.select(instance,
                        replace=True,
                        noExpand=True)

            cmds.file(outpath,
                      options="v=0;",
                      type="mayaAscii",
                      force=True,
                      exportSelected=True,
                      preserveReferences=False,
                      constructionHistory=False,
                      channels=True,  # allow animation
                      constraints=False,
                      shader=False,
                      expressions=True)
