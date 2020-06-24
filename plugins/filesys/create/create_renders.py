
import avalon.api


class RendersCreator(avalon.api.Creator):
    """Publish Render sequences"""

    label = "Renders"
    family = "reveries.renderlayer"
    icon = "film"

    def process(self):
        from avalon.tools.creator import app as creator

        # (NOTE) plugin data passing, this is a hack !
        data = creator.window.data
        if "_creatorData" not in data:
            raise Exception("No sequence data given.")

        sequences = data.pop("_creatorData")
        # (TODO) Dump instance
        print(sequences)

        return super(RendersCreator, self).process()
