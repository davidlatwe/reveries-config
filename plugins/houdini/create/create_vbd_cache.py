from avalon import houdini


class CreateVDBCache(houdini.Creator):
    """OpenVDB from Geometry ROP"""

    label = "VDB Cache"
    family = "reveries.vdbcache"
    icon = "qrcode"

    def __init__(self, *args, **kwargs):
        super(CreateVDBCache, self).__init__(*args, **kwargs)

        # Remove the `active`, we are checking the `bypass` flag of the nodes
        self.data.pop("active", None)

        # Set node type to create for output
        self.data["node_type"] = "geometry"

        # For user to confirm that this asset name is on demand, and
        # able to publish even current Avalon session is not in this
        # asset.
        self.data["assetConfirmed"] = False

    def process(self):
        instance = super(CreateVDBCache, self).process()

        file_path = "$HIP/pyblish/%s/%s.$F4.vdb" % (self.name, self.name)

        parms = {"sopoutput": file_path,
                 "initsim": True}

        if self.nodes:
            node = self.nodes[0]
            parms.update({"soppath": node.path()})

        instance.setParms(parms)
