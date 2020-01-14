import pyblish.api


class CollectAvalonInstances(pyblish.api.ContextPlugin):
    """Gather instances by pre-defined attribute

    This collector takes into account assets that are marked with a
    unique identifier.

    Identifier:
        id (str): "pyblish.avalon.instance"

    """

    order = pyblish.api.CollectorOrder - 0.3
    hosts = ["nuke"]
    label = "Avalon Instances"

    def process(self, context):
        from avalon.nuke import lib

        for node in lib.lsattr("avalon:id",
                               value="pyblish.avalon.instance"):
            try:
                if not node["avalon:active"].value():
                    continue
            except NameError:
                # node has no active switch
                pass

            node_name = node.fullName()
            data = lib.get_avalon_knob_data(node)
            data["objectName"] = node_name

            # Create the instance
            self.log.info("Creating instance for {}".format(node_name))
            instance = context.create_instance(data["subset"])
            instance[:] = [node]
            instance.data.update(data)

        return context
