
import pyblish.api
import avalon.api as api
from avalon.vendor import requests
from reveries.plugins import context_process


class ValidateDeadlineConnection(pyblish.api.InstancePlugin):
    """Validate Deadline Web Service is running"""

    label = "Validate Deadline Web Service"
    order = pyblish.api.ValidatorOrder
    families = [
        "reveries.animation",
        "reveries.pointcache",
        "reveries.imgseq",
    ]

    @context_process
    def process(self, context):

        if not context.data.get("requireDeadline"):
            self.log.debug("No instance require deadline.")
            return

        AVALON_DEADLINE = api.Session.get("AVALON_DEADLINE",
                                          "http://localhost:8082")

        assert AVALON_DEADLINE is not None, "Requires AVALON_DEADLINE"

        # Check response
        response = requests.get(AVALON_DEADLINE)
        assert response.ok, "Response must be ok"
        assert response.text.startswith("Deadline Web Service "), (
            "Web service did not respond with 'Deadline Web Service'"
        )
