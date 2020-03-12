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
