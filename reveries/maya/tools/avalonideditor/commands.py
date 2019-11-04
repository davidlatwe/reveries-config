
from maya import cmds


def remove_id_edit(node):
    # (NOTE) No need to unload reference in prior
    def remove_edit(attr):
        cmds.referenceEdit(attr,
                           failedEdits=True,
                           successfulEdits=True,
                           editCommand="setAttr",
                           removeEdits=True)
    remove_edit(node + ".AvalonID")
    remove_edit(node + ".verifier")


def list_id_edit(reference_node):
    edits = cmds.referenceQuery(reference_node,
                                editNodes=True,
                                editAttrs=True,
                                editCommand="setAttr")
    id_edits = set()
    for edit in edits:
        if edit.endswith(".AvalonID") or edit.endswith(".verifier"):
            id_edits.add(edit)

    return id_edits
