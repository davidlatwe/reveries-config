
import avalon.api
import avalon.io
import avalon.maya
from maya import cmds

from reveries.maya.capsule import maintained_selection


class SwitchStandInToModel(avalon.api.InventoryAction):

    label = "Stand-In To Model"
    icon = "cubes"
    color = "#7BCD2E"

    @staticmethod
    def is_compatible(container):
        return container.get("loader") == "ArnoldAssLoader"

    def process(self, containers):

        _repr_cache = dict()
        standins = list()
        for container in containers:
            if not container.get("loader") == "ArnoldAssLoader":
                continue

            if not cmds.objExists(container["subsetGroup"]):
                continue

            asset_id = avalon.io.ObjectId(container["assetId"])
            if asset_id not in _repr_cache:
                asset_id = avalon.io.ObjectId(container["assetId"])
                asset = avalon.io.find_one({"_id": asset_id})
                representation = avalon.io.locate([
                    avalon.api.Session["AVALON_PROJECT"],
                    asset["name"],
                    "modelDefault",
                    -1,
                    "mayaBinary",
                ])
                _repr_cache[asset_id] = representation
            else:
                representation = _repr_cache[asset_id]

            if representation is None:
                continue

            subset_group = cmds.ls(container["subsetGroup"])[0]
            parent = cmds.listRelatives(subset_group, parent=True, path=True)
            matrix = cmds.xform(subset_group,
                                query=True,
                                matrix=True,
                                objectSpace=True)

            data = (
                parent[0] if parent else "",
                matrix,
                container,
                representation,
            )
            standins.append(data)

        switched_models = set()
        ModelLoader = next(Loader for Loader in
                           avalon.api.discover(avalon.api.Loader)
                           if Loader.__name__ == "ModelLoader")

        with maintained_selection():
            for parent, matrix, container, representation in standins:
                avalon.api.remove(container)
                container = avalon.api.load(ModelLoader, representation)
                subset_group = cmds.ls(container["subsetGroup"])[0]
                if parent:
                    cmds.parent(subset_group, parent)
                cmds.xform(subset_group,
                           matrix=matrix,
                           objectSpace=True)
                switched_models.add(container["objectName"])

        return switched_models
