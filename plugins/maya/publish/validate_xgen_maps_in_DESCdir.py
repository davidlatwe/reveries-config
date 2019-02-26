
import pyblish.api
import reveries.maya.xgen.legacy as xgen


class ValidateXGenMapsInDESC(pyblish.api.InstancePlugin):
    """All maps should be saved in folder under ${DESC}

    All map file path should be like:
        `${DESC}/something/map`

    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "XGen Maps In ${DESC}"
    families = [
        "reveries.xgen.legacy",
    ]

    @classmethod
    def get_invalid(cls, instance):

        invalid = list()

        for desc in instance.data["xgenDescriptions"]:
            for path, parents in xgen.parse_description_maps(desc):
                if not path.startswith("${DESC}"):
                    invalid.append((parents, path))

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            for i in invalid:
                self.log.error(i)
            raise Exception("These attribute map does not saved under "
                            "${DESC}.")
