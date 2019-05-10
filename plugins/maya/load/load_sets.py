
import avalon.api


class SetsLoader(avalon.api.Loader):
    """(Deprecated)"""

    label = "Add Sets"
    order = 90
    icon = "leaf"
    color = "gray"

    hosts = ["maya"]

    families = [
        "reveries.model",
        "reveries.pointcache",
        "reveries.setdress",
    ]

    representations = [
        "mayaBinary",
        "Alembic",
        "setPackage",
    ]

    def load(self, context, name, namespace, options):
        raise DeprecationWarning("This loader has been deprecated.")

    def _place_set(self, container):
        from maya import cmds

        group = container["subsetGroup"]
        location = self._camera_coi()

        if location is not None:
            for attr, value in zip((".tx", ".ty", ".tz"), location):
                cmds.setAttr(group + attr, value)

        cmds.select(group)

    def _camera_coi(self):
        import math
        from maya import cmds
        from reveries.maya.lib import parse_active_camera

        try:
            camera = parse_active_camera()
        except RuntimeError:
            return None

        COI = cmds.camera(camera, query=True, worldCenterOfInterest=True)

        if any(math.isnan(val) for val in COI):
            return None

        return COI
