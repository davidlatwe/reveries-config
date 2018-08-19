
from reveries.plugins import repr_obj
from reveries.maya.plugins import ReferenceLoader


class AnimationLoader(ReferenceLoader):
    """Specific loader of Alembic for the reveries.animation family"""

    label = "Reference Animation Edit"
    order = -10
    icon = "code-fork"
    color = "orange"

    families = ["reveries.animation"]

    representations = [
        repr_obj("mayaAscii", "ma"),
    ]

    def process_reference(self, context, name, namespace, data):
        # (TODO) load curves and other.
        pass

    def switch(self, container, representation):
        self.update(container, representation)
