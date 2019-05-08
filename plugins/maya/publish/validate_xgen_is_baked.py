
import pyblish.api
import reveries.maya.xgen.legacy as xgen


class ValidateXGenIsBaked(pyblish.api.InstancePlugin):
    """XGen Legacy descriptions should be baked in bake step
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "All Descriptions Baked"
    families = [
        "reveries.xgen.legacy",
    ]

    @classmethod
    def get_invalid(cls, instance):
        invalid = list()

        for palette in instance.data["xgenPalettes"]:
            for description in xgen.list_descriptions(palette):

                active_mods = xgen.list_fx_modules(description, activated=True)
                for fxm in active_mods:
                    typ = xgen.get_fx_module_type(palette, description, fxm)
                    if typ == "BakedGroomManagerFXModule":
                        break
                else:
                    invalid.append(description)

        return invalid

    def process(self, instance):

        if instance.data["step"] == xgen.SHAPING:
            # (TODO) Should we ensure no descriptions baked in shaping step ?
            return

        invalid = self.get_invalid(instance)
        if invalid:
            for i in invalid:
                self.log.error(i)
            raise Exception("These descriptions should be baked.")
