from pxr import Sdf, Usd, UsdShade, UsdGeom


class SetRangeBuilder(object):
    def __init__(self, stage, translator, procNamespace):
        self.stage = stage
        self.translator = translator
        self.procNamespace = procNamespace

    # def _check_prim_exists(self, source_shader, usdShadingGroup, node_type):
    #     import maya.cmds as cmds
    #
    #     if self.procNamespace(source_shader) not in \
    #             [x.GetName() for x in
    #              usdShadingGroup.GetPrim().GetAllChildren()]:
    #         # Create ParticleAttributeLookup Node
    #         usdShader = UsdShade.Shader.Define(
    #             self.stage,
    #             usdShadingGroup.GetPath().AppendChild(
    #                 self.procNamespace(source_shader)
    #             )
    #         )
    #         usdShader.CreateIdAttr(
    #             self.translator[node_type]['info:id']['name']
    #         )
    #         # Attribute name
    #         atr_name_value = cmds.getAttr('{}.attributeName'.format(source_shader))
    #         if not atr_name_value:
    #             atr_name_value = ""
    #         usdShader.CreateInput(
    #             self.translator[node_type]["attributeName"]["name"],
    #             self.translator[node_type]["attributeName"]["type"]).Set(
    #             self.translator[node_type]["attributeName"]["convert"](
    #                 atr_name_value)
    #         )
    #         # Create RSVectorMaker Node
    #         usd_vector_shader = UsdShade.Shader.Define(
    #             self.stage,
    #             usdShadingGroup.GetPath().AppendChild(
    #                 self.procNamespace("RSVectorMaker_{}".format(source_shader))
    #             )
    #         )
    #         usd_vector_shader.CreateIdAttr(
    #             self.translator["RSVectorMaker"]['info:id']['name']
    #         )
    #         for _key in ["x", "y", "z"]:
    #             usd_vector_shader.CreateInput(
    #                 self.translator["RSVectorMaker"][_key]["name"],
    #                 self.translator["RSVectorMaker"][_key]["type"]).Set(
    #                 self.translator["RSVectorMaker"][_key]["convert"](
    #                     0.0)
    #             )
    #     else:
    #         usdShader = UsdShade.Shader.Get(
    #             self.stage,
    #             usdShadingGroup.GetPath().AppendChild(
    #                 self.procNamespace(source_shader)
    #             )
    #         )
    #         usd_vector_shader = UsdShade.Shader.Get(
    #             self.stage,
    #             usdShadingGroup.GetPath().AppendChild(
    #                 self.procNamespace("RSVectorMaker_{}".format(source_shader))
    #             )
    #         )
    #
    #     return usdShader, usd_vector_shader

    def get_usdShader(self, source_shader, usdShadingGroup, node_type, attr_list=[]):
        if self.procNamespace(source_shader) not in \
                [x.GetName() for x in
                 usdShadingGroup.GetPrim().GetAllChildren()]:

            usdShader = UsdShade.Shader.Define(
                self.stage,
                usdShadingGroup.GetPath().AppendChild(
                    self.procNamespace(source_shader)
                )
            )
            usdShader.CreateIdAttr(
                self.translator[node_type]['info:id']['name']
            )
            if attr_list:
                for _attr in attr_list:
                    if _attr[0] in self.translator[node_type].keys():
                        usdShader.CreateInput(
                            self.translator[node_type][_attr[0]]["name"],
                            self.translator[node_type][_attr[0]]["type"]).Set(
                            self.translator[node_type][_attr[0]]["convert"](
                                _attr[1])
                        )
        else:
            usdShader = UsdShade.Shader.Get(
                self.stage,
                usdShadingGroup.GetPath().AppendChild(
                    self.procNamespace(source_shader)
                )
            )

        return usdShader

    def get_usdShader_output(self, usdShader, node_type, attr_name):
        attr_table = self.translator[node_type]
        if attr_name in attr_table.keys():
            if attr_table[attr_name]['name'] not in \
                    [x.GetBaseName() for x in usdShader.GetOutputs()]:
                usdShaderOutput = usdShader.CreateOutput(
                    attr_table[attr_name]['name'],
                    attr_table[attr_name]['type']
                )
            else:
                usdShaderOutput = usdShader.GetOutput(
                    attr_table[attr_name]['name'])
            return usdShaderOutput
        else:
            return None

    def _attr_key_mapping(self, atr_name):
        if "max" in atr_name:
            return "new_max"
        if "min" in atr_name:
            return "new_min"
        if "value" in atr_name:
            return "input"
        if "oldMin" in atr_name:
            return "old_min"
        if "oldMax" in atr_name:
            return "old_max"

    def pre_setRange(self, mayaShader, usd_set_range_shader, usdShadingGroup):
        import maya.cmds as cmds

        if cmds.listConnections(mayaShader, d=False, c=True, p=True):

            connections = iter(cmds.listConnections(
                mayaShader, d=False, c=True, p=True))

            for connectDest, connectSource in \
                    zip(connections, connections):
                connectSourceNode = connectSource.split('.')[0]  # rsUserDataScalar_add
                connectSourceAttr = connectSource.split('.')[-1]  # out
                # connectDestNode = connectDest.split('.')[0]
                connectDestAttr = connectDest.split('.')[-1]

                node_type = cmds.nodeType(connectSourceNode)

                # Get ParticleAttributeLookup USD Shader
                atr_name_value = cmds.getAttr(
                    '{}.attributeName'.format(connectSourceNode))
                if not atr_name_value:
                    atr_name_value = ""
                attr_list = [("attributeName", atr_name_value)]

                usd_lookup_shader = \
                    self.get_usdShader(
                        connectSourceNode, usdShadingGroup, node_type,
                        attr_list=attr_list
                    )

                # Get RSVectorMaker USD Shader
                attr_list = [("x", 0.0), ("y", 0.0), ("z", 0.0)]
                usd_vector_shader = \
                    self.get_usdShader(
                        "RSVectorMaker_{}".format(connectSourceNode),
                        usdShadingGroup, "RSVectorMaker", attr_list=attr_list
                    )

                # Get ParticleAttributeLookup/RSVectorMaker usd output
                usd_lookup_node_output = self.get_usdShader_output(
                    usd_lookup_shader,
                    node_type,
                    connectSourceAttr
                )
                usd_vector_shader_output = self.get_usdShader_output(
                    usd_vector_shader,
                    "RSVectorMaker",
                    "out"
                )

                # Connect usd_lookup_node_output to usd_vector_shader
                usd_vector_shader.GetInput("x").ConnectToSource(
                    usd_lookup_node_output)
                usd_vector_shader.GetInput("y").ConnectToSource(
                    usd_lookup_node_output)
                usd_vector_shader.GetInput("z").ConnectToSource(
                    usd_lookup_node_output)

                # Connect usd_vector_shader_output to usd_set_range_shader
                redshift_atr_name = self._attr_key_mapping(connectDestAttr)
                usd_set_range_shader.GetInput(redshift_atr_name).\
                    ConnectToSource(usd_vector_shader_output)

                break

    def post_setRange(
            self,  maya_set_range_shader, usd_set_range_shader, usdShadingGroup,
            last_usd_target, last_target_attr, source_attr):

        # Get RSVectorToScalars USD Shader
        prim_name = "RSVectorToScalars_{}".format(maya_set_range_shader)
        attr_list = [("input", (0, 0, 0))]
        usd_vector_scalars_shader = \
            self.get_usdShader(
                prim_name, usdShadingGroup, "RSVectorToScalars",
                attr_list=attr_list
            )

        usd_set_range_output = self.get_usdShader_output(
            usd_set_range_shader, "setRange", "outValue")

        usd_vector_scalars_output = self.get_usdShader_output(
            usd_vector_scalars_shader, "RSVectorToScalars", source_attr)

        # Connect
        usd_vector_scalars_shader.GetInput("input").\
            ConnectToSource(usd_set_range_output)

        last_usd_target.GetInput(last_target_attr).\
            ConnectToSource(usd_vector_scalars_output)
