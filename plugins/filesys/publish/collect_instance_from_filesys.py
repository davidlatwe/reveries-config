
import pyblish.api


class CollectInstancesFromFilesys(pyblish.api.ContextPlugin):
    """Create instances from filesys module workspace
    """

    label = "Collect Instances From Filesys"
    order = pyblish.api.CollectorOrder - 0.2
    hosts = ["filesys"]

    def process(self, context):
        from reveries import filesys

        # (NOTE) Currently workfile collect is not supported.
        context.data["currentMaking"] = ":unknown:"

        for name, data in filesys.iter_instances():
            instance = context.create_instance(name)
            instance[:] = data.get("members", [])
            instance.data.update(data)
