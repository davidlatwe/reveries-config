
import avalon.api

from avalon.tools.sceneinventory import app


class ForceUpdateHierarchy(avalon.api.InventoryAction):

    label = "SetDress Force Update"
    icon = "tree"
    color = "#ffbb66"
    order = 200

    @staticmethod
    def is_compatible(container):
        return container.get("loader") == "SetDressLoader"

    def process(self, containers):
        items = list()

        for container in containers:
            if self.is_compatible(container):
                container["_force_update"] = True

            items.append(container)

        app.window.view.show_version_dialog(items)
