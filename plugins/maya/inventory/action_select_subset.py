
import avalon.api
from maya import cmds


class SelectSubset(avalon.api.InventoryAction):

    label = "Select Subset"
    icon = "hand-o-down"
    color = "#d8d8d8"
    order = 99

    def process(self, containers):
        groups = list()

        for container in containers:
            if container.get("loader") == "LookLoader":
                continue

            groups.append(container["subsetGroup"])

        cmds.select(groups)
