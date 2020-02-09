
import os
import nuke
import avalon.api
from avalon.nuke import pipeline, lib
from reveries.plugins import PackageLoader
from reveries.utils import get_representation_path_


class ScriptLoader(PackageLoader, avalon.api.Loader):

    label = "Load As Precomp"
    icon = "camera-retro"
    color = "#28EDC9"

    hosts = ["nuke"]

    families = [
        "reveries.write",
    ]

    representations = [
        "nkscript",
    ]

    def setup_precomp(self, precomp, representation):
        precomp["file"].setValue(
            os.path.join(
                self.package_path,
                representation["data"]["scriptName"],
            ).replace("\\", "/")
        )
        precomp["output"].setValue(representation["data"]["outputNode"])
        precomp["useOutput"].setValue(True)
        precomp["reading"].setValue(True)
        precomp["postage_stamp"].setValue(True)

    def load(self, context, name=None, namespace=None, options=None):

        representation = context["representation"]

        precomp = nuke.Node("Precomp")
        self.setup_precomp(precomp, representation)

        nodes = [precomp]

        asset = context["asset"]
        asset_name = asset["data"].get("shortName", asset["name"])
        families = context["subset"]["data"]["families"]
        family_name = families[0].split(".")[-1]
        namespace = namespace or "%s_%s" % (asset_name, family_name)
        pipeline.containerise(name=context["subset"]["name"],
                              namespace=namespace,
                              nodes=nodes,
                              context=context,
                              loader=self.__class__.__name__,
                              no_backdrop=True)

    def update(self, container, representation):

        parents = avalon.io.parenthood(representation)
        self.package_path = get_representation_path_(representation, parents)

        members = container["_members"]
        with lib.sync_copies(members):
            precomp = members[0]
            self.setup_precomp(precomp, representation)

        node = container["_node"]
        with lib.sync_copies([node], force=True):
            version, subset, asset, project = parents

            asset_name = asset["data"].get("shortName", asset["name"])
            families = subset["data"]["families"]  # avalon-core:subset-3.0
            family_name = families[0].split(".")[-1]

            update = {
                "name": subset["name"],
                "representation": str(representation["_id"]),
                "namespace": "%s_%s" % (asset_name, family_name)
            }
            pipeline.update_container(node, update)

    def remove(self, container):
        nodes = list(container["_members"])
        nodes.append(container["_node"])

        for node in nodes:
            for copy in lib.find_copies(node):
                nuke.delete(copy)
            nuke.delete(node)
