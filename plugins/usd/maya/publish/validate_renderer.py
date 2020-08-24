import avalon

import pyblish.api


class ValidateRenderer(pyblish.api.InstancePlugin):
    """Validate renderer setting exists in db."""

    order = pyblish.api.ValidatorOrder

    label = "Validate Renderer setting"
    hosts = ["maya"]
    families = [
        "reveries.look"
    ]

    def process(self, instance):
        project = avalon.io.find_one({
            "name": avalon.api.Session["AVALON_PROJECT"],
            "type": "project"
        })
        renderer = project.get('renderer', None)
        instance.data["renderer"] = renderer.lower() \
            if isinstance(renderer, (str, unicode)) else renderer

        assert renderer, \
            "There is no renderer setting in db. Please check with TD."
