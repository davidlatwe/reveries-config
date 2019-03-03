
import avalon.io
import avalon.maya
from reveries.maya import lib
from reveries.maya.pipeline import put_instance_icon
from reveries.plugins import message_box_error


error__invalid_name = """
{!r} is not a valid render subset name, a render subset name
should starts with one of these variation name:
{}
"""

avalon_instance_id = "pyblish.avalon.instance"


class RenderCreator(avalon.maya.Creator):
    """Create image sequence from rendering or playblast

    Extract image sequence for each renderlayer.

    No matter it's rendering or playblast, no need to select camera or
    pick one into objectSet, just set one camera to be renderabled for
    each renderlayer.

    """

    label = "Render"
    family = "reveries.imgseq"
    icon = "film"

    defaults = [
        "render",
        "lookdev",
        "playblast",
    ]

    def process(self):
        from maya import cmds

        # Build pipeline render settings

        project = avalon.io.find_one({"type": "project"},
                                     projection={"data": True})
        deadline = project["data"]["deadline"]["maya"]
        variant = None

        for var in self.defaults:
            prefix = "imgseq" + var
            if self.data["subset"].lower().startswith(prefix):
                priority = deadline["priorities"][var]
                variant = var
                break

        if variant is None:
            msg = error__invalid_name.format(self.data["subset"],
                                             ", ".join(self.defaults))
            message_box_error("Invalid Subset Name", msg)
            raise RuntimeError(msg)

        # Check existed
        instance = lib.lsAttrs({"id": avalon_instance_id,
                                "family": self.family})
        if instance:
            # Update data
            avalon.maya.lib.imprint(instance[0], self.data, upsert=True)
            cmds.rename(instance[0], self.data["subset"])
            return

        self.data["deadlineEnable"] = not variant == "playblast"
        self.data["deadlinePriority"] = priority
        self.data["deadlinePool"] = ["none"] + deadline["pool"]
        self.data["deadlineGroup"] = deadline["group"]

        self.data["renderType"] = variant
        self.data["publishOnLock"] = not variant == "render"
        self.data["publishOrder"] = 999

        instance = super(RenderCreator, self).process()

        # (TODO) Currently, force using Deadline to render
        if not variant == "playblast":
            cmds.setAttr(instance + ".deadlineEnable", lock=True)

        cmds.setAttr(instance + ".publishOnLock", lock=True)

        return put_instance_icon(instance)
