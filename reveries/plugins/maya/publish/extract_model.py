import pyblish.api


class ExtractModel(pyblish.api.InstancePlugin):
    """Produce a stripped down Maya file from instance

    This plug-in takes into account only nodes relevant to models
    and discards anything else, especially deformers along with
    their intermediate nodes.

    """

    families = ["reveries.model"]
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract Model"

    def process(self, instance):
        import os
        from maya import cmds
        from avalon import maya
        from reveries.maya import lib, context

        dirname = lib.temp_dir()
        filename = "{name}.mb".format(**instance.data)

        path = os.path.join(dirname, filename)

        # Perform extraction
        self.log.info("Performing extraction..")
        with context.no_display_layers(instance.data["hierarchy"]):
            with context.assign_shader(instance.data["meshes"],
                                       shadingEngine="initialShadingGroup"):
                with maya.maintained_selection(), maya.without_extension():
                    self.log.info("Extracting %s" % str(list(instance)))
                    cmds.select(instance, noExpand=True)
                    cmds.file(path,
                              force=True,
                              typ="mayaBinary",
                              exportSelected=True,
                              preserveReferences=False,
                              # Shader assignment is the responsibility of
                              # riggers, for animators, and lookdev, for
                              # rendering.
                              shader=False,
                              # Construction history inherited from collection
                              # This enables a selective export of nodes
                              # relevant to this particular plug-in.
                              constructionHistory=False)

        # Store reference for integration
        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"].append(filename)
        instance.data["stagingDir"] = dirname

        self.log.info("Extracted {instance} to {path}".format(**locals()))
