
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
        "GPUCache",
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

        return container
