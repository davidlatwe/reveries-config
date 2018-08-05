
import reveries.base as base


class AnimationLoader(base.maya.ReferenceLoader):
    """Specific loader of Alembic for the reveries.animation family"""

    label = "Reference Animation Edit"
    order = -10
    icon = "code-fork"
    color = "orange"

    families = ["reveries.animation"]

    representations = base.pendable_reprs([
        ("mayaAscii", "ma"),
    ])

    def process_reference(self, context, name, namespace, data):
        # (TODO) load curves and other.
        pass

    def switch(self, container, representation):
        self.update(container, representation)
