import pyblish.api


class ValidateModelMaxPolyCount(pyblish.api.InstancePlugin):
    """Ensure total poly count does not exceed the limitation
    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.2
    hosts = ['maya']
    label = "Model Max Poly Count"

    def process(self, instance):
        assert instance.data.get("meshes", None), (
            "Instance has no meshes!")

        max_poly_count = instance.data["max_poly_count"]
        poly_count = instance.data["poly_count"]

        if max_poly_count and poly_count > max_poly_count:
            self.log.error("Model poly count exceeded, Limitation was {0}, "
                           "Poly count: {1}".format(max_poly_count,
                                                    poly_count))
            raise Exception("%s <Model Max Poly Count> Failed." % instance)

        self.log.info("%s <Model Max Poly Count> Passed." % instance)
