
import pyblish.api


class ValidateRenderSettings(pyblish.api.InstancePlugin):

    label = "Render Settings"
    order = pyblish.api.ValidatorOrder + 0.1
    hosts = ["maya"]
    families = [
        "reveries.imgseq.batchrender",
        "reveries.imgseq.turntable",
    ]

    def process(self, instance):
        file_name = instance.data["fileNamePrefix"]
        self.log.debug("Collected file name: %s" % file_name)

        assert not file_name == "", "File name prefix must set."

        outputs = instance.data["outputPaths"]
        for aov, path in outputs.items():
            self.log.debug("AOV: %s" % aov)
            self.log.debug("    %s" % path)
