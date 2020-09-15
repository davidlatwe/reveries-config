BASIS_MAPPING = {
    1: 'linear'
}


class RampSampler(object):
    def __init__(self, node_name):
        import maya.cmds as cmds
        import maya.api.OpenMaya as om

        self.key_number = None
        self.keys_list = []
        self.color_list = []
        self.basis_value = None
        self.basis_name = ''

        node = om.MGlobal.getSelectionListByName(node_name).getDependNode(0)
        depfn = om.MFnDependencyNode(node)
        compound_plug = depfn.findPlug("colorEntryList", False)
        for idx in range(compound_plug.numElements()):
            index_plug = compound_plug.elementByPhysicalIndex(idx)
            pos_handle = index_plug.child(0).asMDataHandle()
            color_handle = index_plug.child(1).asMDataHandle()

            # print idx, pos_handle.asFloat(), ":", color_handle.asFloat3()
            self.keys_list.append(pos_handle.asFloat())
            self.color_list.append(color_handle.asFloat3())

        self.key_number = compound_plug.numElements()
        self.basis_value = cmds.getAttr("{}.interpolation".format(node_name))

    def get_key_number(self):
        return self.key_number

    def get_keys_list(self):
        return self.keys_list

    def get_color_list(self):
        return self.color_list

    def get_basis_value(self):
        return self.basis_value

    def get_basis_name(self):
        return BASIS_MAPPING[self.basis_value]
