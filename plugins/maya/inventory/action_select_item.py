
import avalon.api
import random


class SelectItem(avalon.api.InventoryAction):

    label = "Lucky Pick"
    icon = "heart"
    color = "#d8d8d8"

    def process(self, containers):
        container = random.choice(containers)

        return [container["objectName"]]
