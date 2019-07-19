
import pyblish.api

from maya import cmds
from reveries.plugins import context_process


class ValidateDefaultShadersConnections(pyblish.api.InstancePlugin):
    """Validate default shaders in the scene have their default connections.

    For example the lambert1 could potentially be disconnected from the
    initialShadingGroup. As such it's not lambert1 that will be identified
    as the default shader which can have unpredictable results.

    To fix the default connections need to be made again. See the logs for
    more details on which connections are missing.

    """

    order = pyblish.api.ValidatorOrder
    label = "Default Shader Connections"
    hosts = ["maya"]
    families = [
        "reveries.model",
        "reveries.look",
    ]

    # The default connections to check
    DEFAULTS = [
        ("initialShadingGroup.surfaceShader", "lambert1"),
        ("initialParticleSE.surfaceShader", "lambert1"),
        ("initialParticleSE.volumeShader", "particleCloud1")
    ]

    @context_process
    def process(self, context):

        invalid = list()
        for plug, input_node in self.DEFAULTS:
            inputs = cmds.listConnections(plug,
                                          source=True,
                                          destination=False) or None

            if not inputs or inputs[0] != input_node:
                self.log.error("{0} is not connected to {1}. "
                               "This can result in unexpected behavior. "
                               "Please reconnect to continue."
                               "".format(plug, input_node))
                invalid.append(plug)

        if invalid:
            raise RuntimeError("Invalid connections.")
