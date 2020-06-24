
import avalon.api


class RenderCreator(avalon.api.Creator):
    """Publish Render sequences"""

    label = "Render"
    family = "reveries.renderlayer"
    icon = "film"

    def process(self):
        from reveries import filesys

        creator_data = filesys.pop_data("renderCreatorData")
        if not creator_data:
            raise Exception("No render creator data given.")

        name = self.data["subset"]
        data = self.data
        data.update(creator_data)

        data["subsetGroup"] = "Renders"
        data["category"] = self.data["asset"]
        data["dependencies"] = dict()
        data["futureDependencies"] = dict()

        filesys.put_instance(name, data)
