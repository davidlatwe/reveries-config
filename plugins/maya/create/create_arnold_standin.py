
import avalon.maya

from reveries.maya.pipeline import put_instance_icon


class ArnoldStandInCreator(avalon.maya.Creator):
    """Arnold stand-in render proxy
    """

    label = "Arnold Stand-In"
    family = "reveries.standin"
    icon = "coffee"

    def process(self):

        self.data["staticCache"] = True

        return put_instance_icon(super(ArnoldStandInCreator, self).process())
