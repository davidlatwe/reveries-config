
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
        from maya import cmds

        representation = context["representation"]

        available_loaders = avalon.api.discover(avalon.api.Loader)
        Loaders = avalon.api.loaders_from_representation(available_loaders,
                                                         representation)

        Loader = next(L for L in Loaders if issubclass(L, ReferenceLoader))
        loader = Loader(context)

        asset = context['asset']
        namespace = namespace or avalon.maya.lib.unique_namespace(
            asset["name"] + "_",
            prefix="_" if asset["name"][0].isdigit() else "",
            suffix="_",
        )

        options.update({"post_process": False, "useSelection": True})
        container = loader.load(context, name, namespace, options)

        cmds.addAttr(container, longName="sourceLoader", dataType="string")

        cmds.setAttr(container + ".sourceLoader",
                     cmds.getAttr(container + ".loader"),
                     type="string")
        cmds.setAttr(container + ".loader",
                     self.__class__.__name__,
                     type="string")

        return container

    def _get_source_loader(self, container):

        import avalon.api

        for Loader in avalon.api.discover(avalon.api.Loader):
            if Loader.__name__ == container["sourceLoader"]:
                return Loader

    def update(self, container, representation):

        import avalon.pipeline

        Loader = self._get_source_loader(container)
        context = avalon.pipeline.get_representation_context(representation)
        loader = Loader(context)

        return loader.update(container, representation)

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):

        import avalon.pipeline

        Loader = self._get_source_loader(container)
        representation = container["representation"]
        context = avalon.pipeline.get_representation_context(representation)
        loader = Loader(context)

        return loader.remove(container)
