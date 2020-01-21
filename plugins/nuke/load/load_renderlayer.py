
import os
import nuke
import avalon.api
from avalon.nuke import pipeline, lib
from reveries.plugins import PackageLoader
from reveries.utils import get_representation_path_


class RenderLayerLoader(PackageLoader, avalon.api.Loader):

    label = "Load RenderLayer"
    icon = "camera-retro"
    color = "#28EDC9"

    hosts = ["nuke"]

    families = ["reveries.renderlayer"]

    representations = [
        "renderLayer",
    ]

    def set_path(self, read, aov_name, file_name):
        read["file"].setValue(
            os.path.join(
                self.package_path,
                aov_name,  # AOV name
                file_name,
            ).replace("\\", "/")
        )

    def set_range(self, read, start, end):
        read["first"].setValue(start)
        read["last"].setValue(end)
        read["origfirst"].setValue(start)
        read["origlast"].setValue(end)

    def set_format(self, read, resolution):
        w, h = resolution
        for format in nuke.formats():
            if format.width() == w and format.height() == h:
                read["format"].setValue(format.name())
                break

    def load(self, context, name=None, namespace=None, options=None):

        representation = context["representation"]

        nodes = list()

        for name, data in representation["data"]["sequence"].items():
            read = nuke.Node("Read")
            nodes.append(read)

            self.set_path(read, aov_name=name, file_name=data["fname"])
            self.set_format(read, data["resolution"])
            self.set_range(read, start=data["seqStart"], end=data["seqEnd"])

            # Mark aov name
            lib.set_avalon_knob_data(read, {("aov", "AOV"): name})

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
        read_nodes = dict()

        parents = avalon.io.parenthood(representation)
        self.package_path = get_representation_path_(representation, parents)

        for node in container["_members"]:
            if node.Class() == "Read":
                data = lib.get_avalon_knob_data(node)
                read_nodes[data["aov"]] = node
                break

        with lib.sync_copies(list(read_nodes.values())):
            for name, data in representation["data"]["sequence"].items():
                read = read_nodes.get(name)
                if not read:
                    continue

                self.set_path(read, aov_name=name, file_name=data["fname"])
                self.set_format(read, data["resolution"])
                self.set_range(read,
                               start=data["seqStart"],
                               end=data["seqEnd"])

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
