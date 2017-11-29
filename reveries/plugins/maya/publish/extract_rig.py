import pyblish.api


class ExtractRig(pyblish.api.InstancePlugin):
    """Extract rig as Maya Ascii"""

    label = "Extract Rig (Maya ASCII)"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.rig"]

    def process(self, instance):
        import os
        from maya import cmds
        from avalon import maya
        from reveries.maya import lib

        # Define extract output file path
        dirname = lib.temp_dir()
        filename = "{0}.ma".format(instance.name)
        path = os.path.join(dirname, filename)

        # Perform extraction
        self.log.info("Performing extraction..")
        with maya.maintained_selection():
            cmds.select(instance, noExpand=True)
            cmds.file(path,
                      force=True,
                      typ="mayaAscii",
                      exportSelected=True,
                      preserveReferences=False,
                      channels=True,
                      constraints=True,
                      expressions=True,
                      constructionHistory=True)

        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"].append(filename)

        self.log.info("Extracted instance '%s' to: %s" % (instance.name, path))
