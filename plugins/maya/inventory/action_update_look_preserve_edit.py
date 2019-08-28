
import avalon.api

from avalon.tools.sceneinventory import app


class UpdateLookPreserveEdit(avalon.api.InventoryAction):

    label = "Update Preserve Edit"
    icon = "pencil"
    color = "#ffbb66"
    order = 200

    @staticmethod
    def is_compatible(container):
        return container.get("loader") == "LookLoader"

    def process(self, containers):
        items = list()

        for container in containers:
            if self.is_compatible(container):
                container["_preserveRefEdit"] = True

            items.append(container)

        app.window.view.show_version_dialog(items)
