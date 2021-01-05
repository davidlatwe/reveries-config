from pxr import UsdShade


class TextureSamplerBuilder(object):
    def __init__(self, stage, translator, procNamespace):
        self.stage = stage
        self.translator = translator
        self.procNamespace = procNamespace

    def get_usdShader(
            self, source_shader, usdShadingGroup, node_type, attr_list=[]):
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

    def post_file(
            self, maya_shader, usd_file_shader, usdShadingGroup,
            last_usd_target, last_target_attr, source_attr):

        # Get RSVectorToScalars USD Shader
        node_type = "RSColorSplitter"
        prim_name = "{}_{}".format(node_type, self.procNamespace(maya_shader))
        attr_list = [("input", (0, 0, 0, 1))]
        usd_color_splitter_shader = \
            self.get_usdShader(
                prim_name, usdShadingGroup, node_type,
                attr_list=attr_list
            )

        usd_file_output = self.get_usdShader_output(
            usd_file_shader, "file", "outColor")

        usd_color_splitter_shader.GetInput("input").ConnectToSource(
            usd_file_output)

        # Connect
        _source_attr, _target_attr = self._attr_mapping(source_attr, last_target_attr)

        if _source_attr and _target_attr:
            usd_color_splitter_outputR = self.get_usdShader_output(
                usd_color_splitter_shader, node_type, _source_attr)

            last_usd_target.GetInput(_target_attr).ConnectToSource(
                usd_color_splitter_outputR)

    def _attr_mapping(self, attr_name, target_attr_name):
        _mapping = {
            "outAlpha": {
                "attr_name": "outA",
                "is_setRange": "x"
            },
            "outColorR": {
                "attr_name": "outR",
                "is_setRange": "x"
            },
            "outColorG": {
                "attr_name": "outG",
                "is_setRange": "y"
            },
            "outColorB": {
                "attr_name": "outB",
                "is_setRange": "z"
            }
        }

        if attr_name in _mapping.keys():
            _data = _mapping[attr_name]
            if target_attr_name in _data.keys():
                return _data["attr_name"], _data[target_attr_name]

            return _data["attr_name"], target_attr_name
        return "", ""
