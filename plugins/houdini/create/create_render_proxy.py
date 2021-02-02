from avalon import houdini
from reveries import lib


class CreateArnoldStandIn(houdini.Creator):
    """Alembic ROP to pointcache"""

    label = "Arnold Stand-In"
    family = "reveries.standin"
    icon = "coffee"

    def __init__(self, *args, **kwargs):
        super(CreateArnoldStandIn, self).__init__(*args, **kwargs)

        # Remove the `active`, we are checking the `bypass` flag of the nodes
        self.data.pop("active", None)

        self.data.update({"node_type": "arnold"})

        # For user to confirm that this asset name is on demand, and
        # able to publish even current Avalon session is not in this
        # asset.
        self.data["overSessionAsset"] = False

        self.data["deadlinePriority"] = 80
        self.data["deadlinePool"] = lib.get_deadline_pools()
        self.data["deadlineFramesPerTask"] = 1
        self.data["deadlineSuspendJob"] = False

    def process(self):
        instance = super(CreateArnoldStandIn, self).process()

        file_path = "$HIP/pyblish/%s/%s.$F4.ass" % (self.name, self.name)

        parms = {
            "ar_ass_export_enable": True,
            "ar_ass_file": file_path,
            "camera": "",
            "vobject": "",
            "alights": "",
            "ar_ass_expand_procedurals": True,
            "ar_ass_export_options": False,
            "ar_ass_export_lights": False,
            "ar_ass_export_cameras": False,
            "ar_ass_export_drivers": False,
            "ar_ass_export_filters": False,
        }

        instance.setParms(parms)


class CreateRedshiftProxy(houdini.Creator):
    """Alembic ROP to pointcache"""

    label = "Redshift Proxy"
    family = "reveries.rsproxy"
    icon = "coffee"

    def __init__(self, *args, **kwargs):
        super(CreateRedshiftProxy, self).__init__(*args, **kwargs)

        # Remove the `active`, we are checking the `bypass` flag of the nodes
        self.data.pop("active", None)

        # For user to confirm that this asset name is on demand, and
        # able to publish even current Avalon session is not in this
        # asset.
        self.data["overSessionAsset"] = False

        self.data["deadlinePriority"] = 80
        self.data["deadlinePool"] = lib.get_deadline_pools()
        self.data["deadlineFramesPerTask"] = 1
        self.data["deadlineSuspendJob"] = False

    def process(self):
        import hou

        selection = hou.selectedNodes()
        if not selection:
            raise RuntimeError("No selected nodes.")

        sample_node = selection[0]
        path = sample_node.path()

        if path.startswith("/obj/"):
            self.data.update({"node_type": "Redshift_ROP"})
            self.process_obj()

        elif path.startswith("/stage/"):
            self.data.update({"node_type": "usdrender"})
            self.process_usd(path)

        else:
            raise RuntimeError("Unsupported path: %s" % path)

    def process_obj(self):
        instance = super(CreateRedshiftProxy, self).process()

        file_path = "$HIP/pyblish/%s/%s.$F4.rs" % (self.name, self.name)

        parms = {
            "RS_archive_enable": True,
            "RS_archive_file": file_path,
            "RS_archive_exportConn": True,
        }

        instance.setParms(parms)

    def process_usd(self, stage_path):
        # IMPORTANT
        # Here we have complete override `houdini.Creator.process`
        #
        import hou
        from avalon.houdini import lib as hou_lib

        # Build `usdrender` with `rendersettings` that is solely for
        # publishing this proxy.

        out = hou.node("/out")

        lop_net = out.createNode("lopnet", node_name="lopnet_%s" % self.name)
        lop_net.moveToGoodPosition()

        usd_render = out.createNode("usdrender", node_name=self.name)
        usd_render.move(lop_net.position())
        usd_render.shiftPosition((0, -1))  # move to the bottom of lop_net

        box = out.createNetworkBox()
        box.setComment("Publish %s" % self.name)
        box.addItem(lop_net)
        box.addItem(usd_render)
        box.fitAroundContents()

        # LOP subnet

        fetch = lop_net.createNode("fetch")
        camera = lop_net.createNode("camera")  # redshift must have a cam
        settings = lop_net.createNode(
            "rendersettings", node_name="rendersettings_%s" % self.name)

        camera.setNextInput(fetch)
        settings.setNextInput(camera)
        camera.moveToGoodPosition()
        settings.moveToGoodPosition()

        file_path = "$HIP/pyblish/%s/%s.$F4.rs" % (self.name, self.name)

        fetch.setParms({
            "loppath": stage_path,
        })
        settings.setParms({
            "xn__redshiftglobal%s" % k: v
            for k, v in {
                "RS_archive_enable_control_n4bg": "set",
                "RS_archive_enable_mrbg": True,
                # although we have override the output path in `usdrender`
                # node below, we still need to set this attribute, or
                # the proxy cannot be load by Maya with error message like:
                # "Invalid descriptor 'PIC2' (Expected 'REDSHIFT')."...
                "RS_archive_fileName_control_w7bg": "set",
                "RS_archive_fileName_vubg": file_path,
                "RS_archive_exportConn_control_5bcg": "set",
                "RS_archive_exportConn_4xbg": True,
            }.items()
        })
        usd_render.setParms({
            "loppath": settings.path(),
            "renderer": "HdRedshiftRendererPlugin",
            "rendersettings": settings.parm("primpath").eval(),
            "outputimage": file_path,
            "soho_foreground": True,
        })

        self.nodes[:] = [
            usd_render,
            settings,
        ]

        usd_render.setSelected(True)
        instance = usd_render
        hou_lib.imprint(instance, self.data)

        return instance
