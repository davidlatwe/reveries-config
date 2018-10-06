
import avalon.api


class SetsLoader(avalon.api.Loader):

    label = "Add Sets"
    order = -10
    icon = "leaf"
    color = "green"

    hosts = ["maya"]

    families = [
        "reveries.model",
        "reveries.pointcache",
        "reveries.setdress",
    ]

    representations = [
        "mayaBinary",
        "Alembic",
        "SetDress",
    ]

    def load(self, context, name, namespace, options):

        import avalon.api
        import avalon.maya
        from reveries.maya.plugins import ReferenceLoader

        representation = context["representation"]

        available_loaders = avalon.api.discover(avalon.api.Loader)
        Loaders = avalon.api.loaders_from_representation(available_loaders,
                                                         representation)

        Loader = next(L for L in Loaders if issubclass(L, ReferenceLoader))
        loader = Loader(context)

        container = loader.load(context, name, namespace, options)

        self._place_set(container)

        return container

    def _place_set(self, container):
        from maya import cmds
        from reveries.maya.plugins import parse_group_from_container

        group = parse_group_from_container(container)
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
