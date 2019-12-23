
import avalon.io
import avalon.maya
from reveries.maya.pipeline import put_instance_icon


class RenderCreator(avalon.maya.Creator):
    """Submit Mayabatch renderlayers to Deadline"""

    label = "Render"
    family = "reveries.renderglobals"
    icon = "film"

    def __init__(self, *args, **kwargs):
        super(RenderCreator, self).__init__(*args, **kwargs)

        # We won't be publishing this one
        self.data["id"] = "avalon.renderglobals"

        # We don't need subset or asset attributes
        self.data.pop("subset", None)
        self.data.pop("asset", None)
        self.data.pop("active", None)

        # Build pipeline render settings
        project = avalon.io.find_one({"type": "project"},
                                     projection={"data": True})
        deadline = project["data"]["deadline"]["maya"]

        self.data["deadlinePriority"] = deadline["priorities"]["render"]
        self.data["deadlinePool"] = ["none"] + deadline["pool"]
        self.data["deadlineFramesPerTask"] = 1
        self.data["deadlineSuspendJob"] = False

    def process(self):
        from maya import cmds

        # Return if existed
        exists = cmds.ls("renderglobalsDefault")
        assert len(exists) <= 1, (
            "More than one renderglobal exists, this is a bug"
        )

        if exists:
            instance = exists[0]
            cmds.warning("%s already exists." % instance)
        else:
            instance = put_instance_icon(super(RenderCreator, self).process())

        return instance
