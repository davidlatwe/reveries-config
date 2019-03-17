
import pyblish.api


class ValidateRenderFileNamePrefix(pyblish.api.InstancePlugin):
    """Ensure render setttings has been set correctly

        This plugin validate the rendering output file name prefix

    """

    label = "Render File Name Prefix"
    order = pyblish.api.ValidatorOrder + 0.2
    hosts = ["maya"]
    families = [
        "reveries.imgseq.render",
    ]

    @classmethod
    def get_invalid(cls, instance):
        """filename prefix must set and have tags"""
        prefix = instance.data["fileNamePrefix"] or ""
        cls.log.debug("Collected file name prefix: %s" % prefix)

        is_vray = instance.data["renderer"] == "vray"

        has_invalid = False

        if not prefix:
            has_invalid = True
            cls.log.error("File name prefix must set.")

        if "<Scene>" not in prefix:
            has_invalid = True
            cls.log.error("File name prefix must contain <Scene> tag.")

        has_renderlayer = instance.context.data["hasRenderLayers"]
        if has_renderlayer:
            tags = (["<Layer>", "<layer>", "%l"] if is_vray else
                    ["<RenderLayer>", "<Layer>", "%l"])

            if not any(t in prefix for t in tags):
                has_invalid = True
                cls.log.error("File name prefix must contain renderlayer "
                              "tag since the scene has renderlayers.")

        return has_invalid

    def process(self, instance):
        self.log.info("Validating filename prefix..")
        if self.get_invalid(instance):
            raise Exception("Render output filename prefix invalid.")
