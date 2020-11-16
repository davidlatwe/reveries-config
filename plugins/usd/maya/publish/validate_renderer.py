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
        from reveries.common import skip_instance

        context = instance.context
        if skip_instance(context, ['reveries.xgen']):
            return

        project = avalon.io.find_one({
            "name": avalon.api.Session["AVALON_PROJECT"],
            "type": "project"
        })
        renderer = project.get('renderer', None)
        instance.data["renderer"] = str(renderer.lower()) if renderer else None

        assert renderer, \
            "There is no renderer setting in db. Please check with TD."
