from avalon import houdini
from reveries import lib


class CreatePointCache(houdini.Creator):
    """Alembic ROP to pointcache"""

    label = "Point Cache"
    family = "reveries.pointcache"
    icon = "diamond"

    def __init__(self, *args, **kwargs):
        super(CreatePointCache, self).__init__(*args, **kwargs)

        # Remove the `active`, we are checking the `bypass` flag of the nodes
        self.data.pop("active", None)

        self.data.update({"node_type": "alembic"})

        self.data["deadlinePriority"] = 80
        self.data["deadlinePool"] = lib.get_deadline_pools()
        self.data["deadlineFramesPerTask"] = 1
        self.data["deadlineSuspendJob"] = False

    def process(self):
        instance = super(CreatePointCache, self).process()

        file_path = "$HIP/pyblish/%s/%s.abc" % (self.name, self.name)

        parms = {
            "use_sop_path": True,  # Export single node from SOP Path
            "build_from_path": False,  # Direct path of primitive in output
            "path_attrib": "path",  # Pass path attribute for output
            "prim_to_detail_pattern": lib.AVALON_ID,
            "format": 2,  # Set format to Ogawa
            "filename": file_path,
        }

        if self.nodes:
            node = self.nodes[0]
            parms.update({"sop_path": node.path()})

        instance.setParms(parms)

        # Lock any parameters in this list
        to_lock = ["prim_to_detail_pattern"]
        for name in to_lock:
            parm = instance.parm(name)
            parm.lock(True)
