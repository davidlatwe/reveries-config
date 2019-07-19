
import avalon.maya

from reveries.maya.pipeline import put_instance_icon


class ArnoldStandInCreator(avalon.maya.Creator):
    """Arnold stand-in render proxy

    When exporting animated object, and wish to render with motion blur,
    you need to export with motionBlur as well.

    When exporting XGen, you also need to export Alembic for batch and
    ensure the motion blur settings in XGen output tab are all set.

    """

    label = "Arnold Stand-In"
    family = "reveries.standin"
    icon = "coffee"

    def process(self):

        # (NOTE) objectSet's 'motionBlur' attribute can affect object's
        #        motionBlur state in Arnold.

        self.data["staticCache"] = True

        return put_instance_icon(super(ArnoldStandInCreator, self).process())
