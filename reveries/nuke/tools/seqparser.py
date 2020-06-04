
from avalon import api


SEQUENCE_KEYS = ["name"]


def build_layers(sequences):
    if not sequences:
        return

    first = next(iter(sequences.values()))
    root = first["root"]
    start = first["start"]
    end = first["end"]

    Loader = next(Plugin for Plugin in api.discover(api.Loader)
                  if Plugin.__name__ == "RenderLayerLoader")
    Loader.build_sequences(sequences,
                           root,
                           group_name="master",
                           stamp_name="renderLayers",
                           start=start,
                           end=end)
