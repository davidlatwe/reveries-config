
from collections import OrderedDict
from contextlib import contextmanager
import nuke


def exr_merge(beauty, layers):
    """Shuffle copy RGBA from multiple read nodes with layer named

    Referenced from `Exr Merge - Ztools v1.1`
    http://www.nukepedia.com/python/render/exr-merge-ztools

    All input Read nodes requires to have a knob called `avalon:aov`,
    which should holds the name of AOV.

    If there are duplicate named AOV, the layer name will be suffixed
    with ".duplicated%d".

    This function does not grouping anything like `Exr Merge` does.

    The last shuffle copy node will be selected for the convenience of
    connecting other node like Output node if this function is running
    inside a `Group.begin` <-> `Group.end` context.

    Args:
        beauty (nuke.Read): A Read node for being RGBA
        layers (list): List of Read node that loads AOV sequences

    Returns:
        (list): A list of newly created shuffle copy nodes

    """

    layers_by_name = OrderedDict()
    for node in layers:
        name = node["avalon:aov"].value()

        _, _n = 0, name
        while name in layers_by_name:
            _ += 1
            name = _n + ".duplicated%d" % _

        layers_by_name[name] = node

    shuffle_nodes = list()

    B = beauty
    for name, A in layers_by_name.items():
        B = shuffle_copy(A, B, name)
        shuffle_nodes.append(B)

    if shuffle_nodes:
        shuffle_nodes[-1]["selected"].setValue(True)

    return shuffle_nodes


def shuffle_copy(a, b, layer):
    """Shuffle copy `layer` from node `a` -> `b`

    Args:
        a (`nuke.Node`): ShuffleCopy input 1
        b (`nuke.Node`): ShuffleCopy input 2
        layer (str): Name of shuffle-copied (out) layer

    Returns:
        `ShuffleCopy` node

    """
    shuffle = nuke.nodes.ShuffleCopy()
    shuffle.setInput(0, b)
    shuffle.setInput(1, a)
    shuffle.autoplace()

    shuffle["red"].setValue("red")
    shuffle["green"].setValue("green")
    shuffle["blue"].setValue("blue")
    shuffle["alpha"].setValue("alpha")

    # Register layer to nuke
    channels = [".red", ".green", ".blue", ".alpha"]
    nuke.Layer(layer, [layer + ch for ch in channels])

    shuffle["out"].setValue(layer)

    return shuffle


@contextmanager
def group_scope(group):
    group.begin()
    try:
        yield
    finally:
        group.end()
