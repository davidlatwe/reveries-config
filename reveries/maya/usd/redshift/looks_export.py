import re

from pxr import Sdf, Usd, UsdShade, UsdGeom

# Maya Attributes to USD post process


def Same(arg):
    return arg


def FloatToVector(arg):
    return (arg, arg, arg)


def MayaArrayToVector(arg):
    return arg[0]


def MayaArrayToFloat2(arg):
    return arg[0]


def IntToString(arg):
    return str(arg)


def VectorToVector4(arg):
    return (arg[0][0], arg[0][1], arg[0][2], 1)


def MayaArrayToFloat(arg):
    return arg[0][0]


def MayaArrayToInt(arg):
    return int(arg[0][0])


def stripNamespace(name):
    return name.split(':')[-1]


def keepNamespace(name):
    return name.replace(':', '_')


def getShadingGroups(root):
    import maya.api.OpenMaya as om
    import maya.cmds as cmds

    children_meshs = cmds.listRelatives(root,
                                        ad=True, typ='surfaceShape', f=True)
    mesh_list = om.MSelectionList()
    for mesh in children_meshs:
        mesh_list.add(mesh)
    shadingGroup_list = []
    for i in range(mesh_list.length()):
        mesh = om.MFnMesh(mesh_list.getDagPath(i))
        shadingGroups = [om.MFnDependencyNode(x).name()
                         for x in mesh.getConnectedShaders(0)[0]]
        shadingGroup_list += shadingGroups
    shadingGroup_list = list(set(shadingGroup_list))

    return shadingGroup_list


class RedshiftShadersToUSD:

    def __init__(self, shadingGroups=None, scopeName='Looks', filename=None,
                 assetVersion=None, assetName='None', stripNS=True):
        import maya.cmds as cmds

        if shadingGroups == None or type(shadingGroups) is not list:
            return

        if len(shadingGroups) == 0:
            return

        if False in [(cmds.nodeType(shadingGroup) == 'shadingEngine')
                     for shadingGroup in shadingGroups]:
            return

        if stripNS is True:
            self.procNamespace = stripNamespace
        else:
            self.procNamespace = keepNamespace

        self.vector_scalars_builder = {}
        self.translator = {
            'RedshiftMaterial': {
                'info:id': {'name': 'redshift::Material'},
                'diffuse_color': {'name': 'diffuse_color', 'type': Sdf.ValueTypeNames.Color3f,
                                  'convert': MayaArrayToVector},
                'diffuse_weight': {'name': 'diffuse_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'diffuse_roughness': {'name': 'diffuse_roughness', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'transl_color': {'name': 'transl_color', 'type': Sdf.ValueTypeNames.Color3f,
                                 'convert': MayaArrayToVector},
                'transl_weight': {'name': 'transl_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'opacity_color': {'name': 'opacity_color', 'type': Sdf.ValueTypeNames.Color3f,
                                  'convert': MayaArrayToVector},
                'refl_color': {'name': 'refl_color', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'refl_weight': {'name': 'refl_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_roughness': {'name': 'refl_roughness', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_samples': {'name': 'refl_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_brdf': {'name': 'refl_brdf', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'refl_aniso': {'name': 'refl_aniso', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_aniso_rotation': {'name': 'refl_aniso_rotation', 'type': Sdf.ValueTypeNames.Float,
                                        'convert': Same},
                'refl_fresnel_mode': {'name': 'refl_fresnel_mode', 'type': Sdf.ValueTypeNames.Token,
                                      'convert': IntToString},
                'refl_reflectivity': {'name': 'refl_reflectivity', 'type': Sdf.ValueTypeNames.Color3f,
                                      'convert': MayaArrayToVector},
                'refl_edge_tint': {'name': 'refl_edge_tint', 'type': Sdf.ValueTypeNames.Color3f,
                                   'convert': MayaArrayToVector},
                'refl_metalness': {'name': 'refl_metalness', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_ior': {'name': 'refl_ior', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'refr_color': {'name': 'refr_color', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'refr_weight': {'name': 'refr_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refr_roughness': {'name': 'refr_roughness', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refr_samples': {'name': 'refr_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refr_ior': {'name': 'refr_ior', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refr_use_base_IOR': {'name': 'refr_use_base_IOR', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'coat_color': {'name': 'coat_color', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'coat_weight': {'name': 'coat_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'coat_roughness': {'name': 'coat_roughness', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'coat_samples': {'name': 'coat_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'coat_brdf': {'name': 'coat_brdf', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'coat_reflectivity': {'name': 'coat_reflectivity', 'type': Sdf.ValueTypeNames.Color3f,
                                      'convert': MayaArrayToVector},
                'coat_transmittance': {'name': 'coat_transmittance', 'type': Sdf.ValueTypeNames.Color3f,
                                       'convert': MayaArrayToVector},
                'coat_thickness': {'name': 'coat_thickness', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'bump_input': {'name': 'bump_input', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'emission_color': {'name': 'emission_color', 'type': Sdf.ValueTypeNames.Color3f,
                                   'convert': MayaArrayToVector},
                'emission_weight': {'name': 'emission_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'ss_unitsMode': {'name': 'ss_unitsMode', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'ss_extinction_coeff': {'name': 'ss_extinction_coeff', 'type': Sdf.ValueTypeNames.Color3f,
                                        'convert': MayaArrayToVector},
                'ss_extinction_scale': {'name': 'ss_extinction_scale', 'type': Sdf.ValueTypeNames.Float,
                                        'convert': Same},
                'ss_scatter_coeff': {'name': 'ss_scatter_coeff', 'type': Sdf.ValueTypeNames.Color3f,
                                     'convert': MayaArrayToVector},
                'ss_amount': {'name': 'ss_amount', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ss_phase': {'name': 'ss_phase', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ss_samples': {'name': 'ss_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'ms_amount': {'name': 'ms_amount', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ms_radius_scale': {'name': 'ms_radius_scale', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ms_mode': {'name': 'ms_mode', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'ms_samples': {'name': 'ms_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'ms_include_mode': {'name': 'ms_include_mode', 'type': Sdf.ValueTypeNames.Token,
                                    'convert': IntToString},

                'ms_color0': {'name': 'ms_color0', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'ms_weight0': {'name': 'ms_weight0', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ms_radius0': {'name': 'ms_radius0', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'ms_color1': {'name': 'ms_color1', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'ms_weight1': {'name': 'ms_weight1', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ms_radius1': {'name': 'ms_radius1', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'ms_color2': {'name': 'ms_color2', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'ms_weight2': {'name': 'ms_weight2', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ms_radius2': {'name': 'ms_radius2', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'diffuse_direct': {'name': 'diffuse_direct', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'diffuse_indirect': {'name': 'diffuse_indirect', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'refl_direct': {'name': 'refl_direct', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_indirect': {'name': 'refl_indirect', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_isGlossiness': {'name': 'refl_isGlossiness', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'coat_direct': {'name': 'coat_direct', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'coat_indirect': {'name': 'coat_indirect', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'coat_isGlossiness': {'name': 'coat_isGlossiness', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},

                'post_proc': self.post_Nothing
            },
            'RedshiftSubSurfaceScatter': {
                'info:id': {'name': 'redshift::SubSurfaceScatter'},
                'preset': {'name': 'preset', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'sub_surface_color': {'name': 'sub_surface_color', 'type': Sdf.ValueTypeNames.Color3f,
                                      'convert': MayaArrayToVector},
                'diffuse_amount': {'name': 'diffuse_amount', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'no_diffuse_bump': {'name': 'no_diffuse_bump', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'mode': {'name': 'mode', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'samples': {'name': 'samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'singleScatter_on': {'name': 'singleScatter_on', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'phase': {'name': 'phase', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'include_mode': {'name': 'include_mode', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'scatter_color': {'name': 'scatter_color', 'type': Sdf.ValueTypeNames.Color3f,
                                  'convert': MayaArrayToVector},
                'scatter_radius': {'name': 'scatter_radius', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_color': {'name': 'refl_color', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'reflectivity': {'name': 'reflectivity', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_gloss': {'name': 'refl_gloss', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_gloss_samples': {'name': 'refl_gloss_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_brdf': {'name': 'refl_brdf', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'no_refl_bump': {'name': 'no_refl_bump', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'enableFresnel': {'name': 'enableFresnel', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_fresnel_useior': {'name': 'refl_fresnel_useior', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_fresnel_0_degree_refl': {'name': 'refl_fresnel_0_degree_refl', 'type': Sdf.ValueTypeNames.Float,
                                               'convert': Same},
                'refl_fresnel_90_degree_refl': {'name': 'refl_fresnel_90_degree_refl', 'type': Sdf.ValueTypeNames.Float,
                                                'convert': Same},
                'refl_fresnel_curve': {'name': 'refl_fresnel_curve', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_enablecutoff': {'name': 'refl_enablecutoff', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_cutoff': {'name': 'refl_cutoff', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'skip_inside_refl': {'name': 'skip_inside_refl', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'depth_override': {'name': 'depth_override', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_depth': {'name': 'refl_depth', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_hl_only': {'name': 'refl_hl_only', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'refr_depth': {'name': 'refr_depth', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refr_cutoff': {'name': 'refr_cutoff', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refr_enablecutoff': {'name': 'refr_enablecutoff', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'additional_bump_mode': {'name': 'additional_bump_mode', 'type': Sdf.ValueTypeNames.Int,
                                         'convert': Same},

                'bump_input': {'name': 'bump_input', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},

                'ss_nostransparency': {'name': 'ss_nostransparency', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'ss_transmittance': {'name': 'ss_transmittance', 'type': Sdf.ValueTypeNames.Color3f,
                                     'convert': MayaArrayToVector},
                'ss_overrideCoeffs': {'name': 'ss_overrideCoeffs', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'ss_amount': {'name': 'ss_amount', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ss_thickness': {'name': 'ss_thickness', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ss_samples': {'name': 'ss_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},

                'post_proc': self.post_Nothing
            },
            'RedshiftSkin': {
                'info:id': {'name': 'redshift::Skin'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'radius_scale': {'name': 'radius_scale', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'overall_scale': {'name': 'overall_scale', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'diffuse_amount': {'name': 'diffuse_amount', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'no_diffuse_bump': {'name': 'no_diffuse_bump', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'normalize_weights': {'name': 'normalize_weights', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'mode': {'name': 'mode', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'samples': {'name': 'samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'include_mode': {'name': 'include_mode', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'shallow_color': {'name': 'shallow_color', 'type': Sdf.ValueTypeNames.Color3f,
                                  'convert': MayaArrayToVector},
                'shallow_weight': {'name': 'shallow_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'shallow_radius': {'name': 'shallow_radius', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'mid_color': {'name': 'mid_color', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'mid_weight': {'name': 'mid_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'mid_radius': {'name': 'mid_radius', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'deep_color': {'name': 'deep_color', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'deep_weight': {'name': 'deep_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'deep_radius': {'name': 'deep_radius', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ss_transmittance': {'name': 'ss_transmittance', 'type': Sdf.ValueTypeNames.Color3f,
                                     'convert': MayaArrayToVector},
                'ss_phase': {'name': 'ss_phase', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ss_amount': {'name': 'ss_amount', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ss_thickness': {'name': 'ss_thickness', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ss_samples': {'name': 'ss_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'refl_color0': {'name': 'refl_color0', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'refl_weight0': {'name': 'refl_weight0', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_brdf0': {'name': 'refl_brdf0', 'type': Sdf.ValueTypeNames.Int, 'convert': IntToString},
                'refl_gloss0': {'name': 'refl_gloss0', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_gloss_samples0': {'name': 'refl_gloss_samples0', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_ior0': {'name': 'refl_ior0', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_color1': {'name': 'refl_color1', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'refl_weight1': {'name': 'refl_weight1', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_brdf1': {'name': 'refl_brdf1', 'type': Sdf.ValueTypeNames.Int, 'convert': IntToString},
                'refl_gloss1': {'name': 'refl_gloss1', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_gloss_samples1': {'name': 'refl_gloss_samples1', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_ior1': {'name': 'refl_ior1', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'no_refl_bump': {'name': 'no_refl_bump', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'depth_override': {'name': 'depth_override', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_depth': {'name': 'refl_depth', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_hl_only': {'name': 'refl_hl_only', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_cutoff': {'name': 'refl_cutoff', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_enablecutoff': {'name': 'refl_enablecutoff', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'additional_bump_mode': {'name': 'additional_bump_mode', 'type': Sdf.ValueTypeNames.Int,
                                         'convert': Same},

                'bump_input': {'name': 'bump_input', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},

                'post_proc': self.post_Nothing
            },
            'RedshiftCarPaint': {
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'base_color': {'name': 'base_color', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'diffuse_weight': {'name': 'diffuse_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'edge_color': {'name': 'edge_color', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'edge_color_bias': {'name': 'edge_color_bias', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'spec_color': {'name': 'spec_color', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'spec_weight': {'name': 'spec_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'spec_brdf': {'name': 'spec_brdf', 'type': Sdf.ValueTypeNames.Int, 'convert': IntToString},
                'spec_gloss': {'name': 'spec_gloss', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'spec_samples': {'name': 'spec_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'spec_norefl': {'name': 'spec_norefl', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'spec_facingweight': {'name': 'spec_facingweight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'spec_perpweight': {'name': 'spec_perpweight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'spec_curvefactor': {'name': 'spec_curvefactor', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'flake_color': {'name': 'flake_color', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'flake_weight': {'name': 'flake_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'flake_gloss': {'name': 'flake_gloss', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'flake_samples': {'name': 'flake_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'flake_norefl': {'name': 'flake_norefl', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'flake_facingweight': {'name': 'flake_facingweight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'flake_perpweight': {'name': 'flake_perpweight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'flake_curvefactor': {'name': 'flake_curvefactor', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'flake_density': {'name': 'flake_density', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'flake_decay': {'name': 'flake_decay', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'flake_strength': {'name': 'flake_strength', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'flake_scale': {'name': 'flake_scale', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'clearcoat_color': {'name': 'clearcoat_color', 'type': Sdf.ValueTypeNames.Color3f,
                                    'convert': MayaArrayToVector},
                'clearcoat_weight': {'name': 'clearcoat_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'clearcoat_brdf': {'name': 'clearcoat_brdf', 'type': Sdf.ValueTypeNames.Int, 'convert': IntToString},
                'clearcoat_gloss': {'name': 'clearcoat_gloss', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'clearcoat_samples': {'name': 'clearcoat_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'clearcoat_facingweight': {'name': 'clearcoat_facingweight', 'type': Sdf.ValueTypeNames.Float,
                                           'convert': Same},
                'clearcoat_perpweight': {'name': 'clearcoat_perpweight', 'type': Sdf.ValueTypeNames.Float,
                                         'convert': Same},
                'clearcoat_curvefactor': {'name': 'clearcoat_curvefactor', 'type': Sdf.ValueTypeNames.Float,
                                          'convert': Same},
                'depth_override': {'name': 'depth_override', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_depth': {'name': 'refl_depth', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_enablecutoff': {'name': 'refl_enablecutoff', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_cutoff': {'name': 'refl_cutoff', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'no_baselayer_bump': {'name': 'no_baselayer_bump', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'no_clearcoat_bump': {'name': 'no_clearcoat_bump', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'additional_bump_mode': {'name': 'additional_bump_mode', 'type': Sdf.ValueTypeNames.Int,
                                         'convert': Same},
                'bump_input': {'name': 'bump_input', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},

                'post_proc': self.post_Nothing
            },
            'RedshiftArchitectural': {
                'info:id': {'name': 'redshift::Architectural'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'diffuse': {'name': 'diffuse', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'diffuse_weight': {'name': 'diffuse_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'diffuse_roughness': {'name': 'diffuse_roughness', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'no_diffuse_bump': {'name': 'no_diffuse_bump', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refr_translucency': {'name': 'refr_translucency', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refr_trans_color': {'name': 'refr_trans_color', 'type': Sdf.ValueTypeNames.Color3f,
                                     'convert': MayaArrayToVector},
                'refr_trans_weight': {'name': 'refr_trans_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'reflectivity': {'name': 'reflectivity', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_color': {'name': 'refl_color', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'refl_brdf': {'name': 'refl_brdf', 'type': Sdf.ValueTypeNames.Int, 'convert': IntToString},
                'refl_gloss': {'name': 'refl_gloss', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_gloss_samples': {'name': 'refl_gloss_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'no_refl0_bump': {'name': 'no_refl0_bump', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'brdf_fresnel': {'name': 'brdf_fresnel', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'brdf_fresnel_lockIOR': {'name': 'brdf_fresnel_lockIOR', 'type': Sdf.ValueTypeNames.Int,
                                         'convert': Same},
                'brdf_fresnel_ior': {'name': 'brdf_fresnel_ior', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'brdf_fresnel_type': {'name': 'brdf_fresnel_type', 'type': Sdf.ValueTypeNames.Int,
                                      'convert': IntToString},
                'brdf_extinction_coeff': {'name': 'brdf_extinction_coeff', 'type': Sdf.ValueTypeNames.Float,
                                          'convert': Same},
                'brdf_0_degree_refl': {'name': 'brdf_0_degree_refl', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'brdf_90_degree_refl': {'name': 'brdf_90_degree_refl', 'type': Sdf.ValueTypeNames.Float,
                                        'convert': Same},
                'brdf_curve': {'name': 'brdf_curve', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_is_metal': {'name': 'refl_is_metal', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'hl_vs_refl_balance': {'name': 'hl_vs_refl_balance', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'anisotropy': {'name': 'anisotropy', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'anisotropy_rotation': {'name': 'anisotropy_rotation', 'type': Sdf.ValueTypeNames.Float,
                                        'convert': Same},
                'anisotropy_orientation': {'name': 'anisotropy_orientation', 'type': Sdf.ValueTypeNames.Int,
                                           'convert': IntToString},
                'refl_base': {'name': 'refl_base', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_base_color': {'name': 'refl_base_color', 'type': Sdf.ValueTypeNames.Color3f,
                                    'convert': MayaArrayToVector},
                'refl_base_brdf': {'name': 'refl_base_brdf', 'type': Sdf.ValueTypeNames.Int, 'convert': IntToString},
                'refl_base_gloss': {'name': 'refl_base_gloss', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_base_gloss_samples': {'name': 'refl_base_gloss_samples', 'type': Sdf.ValueTypeNames.Int,
                                            'convert': Same},
                'no_refl1_bump': {'name': 'no_refl1_bump', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'brdf_base_fresnel': {'name': 'brdf_base_fresnel', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'brdf_base_fresnel_lockIOR': {'name': 'brdf_base_fresnel_lockIOR', 'type': Sdf.ValueTypeNames.Int,
                                              'convert': Same},
                'brdf_base_fresnel_ior': {'name': 'brdf_base_fresnel_ior', 'type': Sdf.ValueTypeNames.Float,
                                          'convert': Same},
                'brdf_base_fresnel_type': {'name': 'brdf_base_fresnel_type', 'type': Sdf.ValueTypeNames.Int,
                                           'convert': IntToString},
                'brdf_base_extinction_coeff': {'name': 'brdf_base_extinction_coeff', 'type': Sdf.ValueTypeNames.Float,
                                               'convert': Same},
                'brdf_base_0_degree_refl': {'name': 'brdf_base_0_degree_refl', 'type': Sdf.ValueTypeNames.Float,
                                            'convert': Same},
                'brdf_base_90_degree_refl': {'name': 'brdf_base_90_degree_refl', 'type': Sdf.ValueTypeNames.Float,
                                             'convert': Same},
                'brdf_base_curve': {'name': 'brdf_base_curve', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'transparency': {'name': 'transparency', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refr_color': {'name': 'refr_color', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'refr_gloss': {'name': 'refr_gloss', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refr_gloss_samples': {'name': 'refr_gloss_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refr_ior': {'name': 'refr_ior', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'no_refr_bump': {'name': 'no_refr_bump', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'thin_walled': {'name': 'thin_walled', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'do_refractive_caustics': {'name': 'do_refractive_caustics', 'type': Sdf.ValueTypeNames.Int,
                                           'convert': Same},
                'global_vol_scatter': {'name': 'global_vol_scatter', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refr_falloff_on': {'name': 'refr_falloff_on', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refr_falloff_dist': {'name': 'refr_falloff_dist', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refr_falloff_color_on': {'name': 'refr_falloff_color_on', 'type': Sdf.ValueTypeNames.Int,
                                          'convert': Same},
                'refr_falloff_color': {'name': 'refr_falloff_color', 'type': Sdf.ValueTypeNames.Color3f,
                                       'convert': MayaArrayToVector},
                'ao_on': {'name': 'ao_on', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'ao_combineMode': {'name': 'ao_combineMode', 'type': Sdf.ValueTypeNames.Int, 'convert': IntToString},
                'ao_applyToIncandescence': {'name': 'ao_applyToIncandescence', 'type': Sdf.ValueTypeNames.Int,
                                            'convert': Same},
                'ao_compensateForExposure': {'name': 'ao_compensateForExposure', 'type': Sdf.ValueTypeNames.Int,
                                             'convert': Same},
                'ao_samples': {'name': 'ao_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'ao_distance': {'name': 'ao_distance', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ao_spread': {'name': 'ao_spread', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ao_falloff': {'name': 'ao_falloff', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ao_invert': {'name': 'ao_invert', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'ao_dark': {'name': 'ao_dark', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'ao_ambient': {'name': 'ao_ambient', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'depth_override': {'name': 'depth_override', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_depth': {'name': 'refl_depth', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_hl_only': {'name': 'refl_hl_only', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'skip_inside_refl': {'name': 'skip_inside_refl', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_enablecutoff': {'name': 'refl_enablecutoff', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_cutoff': {'name': 'refl_cutoff', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refr_depth': {'name': 'refr_depth', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refr_enablecutoff': {'name': 'refr_enablecutoff', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refr_cutoff': {'name': 'refr_cutoff', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'combined_depth': {'name': 'combined_depth', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'additional_color': {'name': 'additional_color', 'type': Sdf.ValueTypeNames.Color3f,
                                     'convert': MayaArrayToVector},
                'incandescent_scale': {'name': 'incandescent_scale', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'cutout_opacity': {'name': 'cutout_opacity', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'propagate_alpha': {'name': 'propagate_alpha', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'additional_bump_mode': {'name': 'additional_bump_mode', 'type': Sdf.ValueTypeNames.Int,
                                         'convert': Same},
                'bump_input': {'name': 'bump_input', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},

                'post_proc': self.post_Nothing
            },
            'RedshiftMaterialBlender': {
                'info:id': {'name': 'redshift::MaterialBlender'},
                'outColor': {'name': 'outDisplacementVector', 'type': Sdf.ValueTypeNames.Float3,
                             'convert': MayaArrayToVector},
                'baseColor': {'name': 'baseInput', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},

                'layerColor1': {'name': 'layerColor1', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'layerColor2': {'name': 'layerColor2', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'layerColor3': {'name': 'layerColor3', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'layerColor4': {'name': 'layerColor4', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'layerColor5': {'name': 'layerColor5', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'layerColor6': {'name': 'layerColor6', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},

                'blendColor1': {'name': 'blendColor1', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'blendColor2': {'name': 'blendColor2', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'blendColor3': {'name': 'blendColor3', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'blendColor4': {'name': 'blendColor4', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'blendColor5': {'name': 'blendColor5', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'blendColor6': {'name': 'blendColor6', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},

                'additiveMode1': {'name': 'additiveMode1', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'additiveMode2': {'name': 'additiveMode2', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'additiveMode3': {'name': 'additiveMode3', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'additiveMode4': {'name': 'additiveMode4', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'additiveMode5': {'name': 'additiveMode5', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'additiveMode6': {'name': 'additiveMode6', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftMatteShadowCatcher': {
                'info:id': {'name': 'redshift::MatteShadow'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'backgroundIsEnv': {'name': 'backgroundIsEnv', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'background': {'name': 'background', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'background_alpha': {'name': 'background_alpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'emissive_color': {'name': 'emissive_color', 'type': Sdf.ValueTypeNames.Color3f,
                                   'convert': MayaArrayToVector},
                'emissive_scale': {'name': 'emissive_scale', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'catch_diffuse': {'name': 'catch_diffuse', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'diffuse': {'name': 'diffuse', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'diffuse_weight': {'name': 'diffuse_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'catch_shadows': {'name': 'catch_shadows', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'shadows': {'name': 'shadows', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'shadows_alpha': {'name': 'shadows_alpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ambient': {'name': 'ambient', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'use_dot_nl': {'name': 'use_dot_nl', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'saturation': {'name': 'saturation', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'transparency': {'name': 'transparency', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_enabled': {'name': 'refl_enabled', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_color': {'name': 'refl_color', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'refl_alpha': {'name': 'refl_alpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'reflectivity': {'name': 'reflectivity', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_brdf': {'name': 'refl_brdf', 'type': Sdf.ValueTypeNames.Int, 'convert': IntToString},
                'refl_glossiness': {'name': 'refl_glossiness', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_samples': {'name': 'refl_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_fog_enable': {'name': 'refl_fog_enable', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_max_dist': {'name': 'refl_max_dist', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ao_on': {'name': 'ao_on', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'ao_samples': {'name': 'ao_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'ao_distance': {'name': 'ao_distance', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'ao_dark': {'name': 'ao_dark', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'bump_input': {'name': 'bump_input', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},

                'post_proc': self.post_Nothing
            },
            'RedshiftHair': {
                'info:id': {'name': 'redshift::Hair'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'irefl_color': {'name': 'irefl_color', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'irefl_weight': {'name': 'irefl_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'irefl_gloss': {'name': 'irefl_gloss', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'irefl_samples': {'name': 'irefl_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'irefl_norefl': {'name': 'irefl_norefl', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'diffuse_color': {'name': 'diffuse_color', 'type': Sdf.ValueTypeNames.Color3f,
                                  'convert': MayaArrayToVector},
                'diffuse_weight': {'name': 'diffuse_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'diffuseTrans_weight': {'name': 'diffuseTrans_weight', 'type': Sdf.ValueTypeNames.Float,
                                        'convert': Same},
                'trans_color': {'name': 'trans_color', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'trans_weight': {'name': 'trans_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'trans_lgloss': {'name': 'trans_lgloss', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'trans_wgloss': {'name': 'trans_wgloss', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_color': {'name': 'refl_color', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'refl_weight': {'name': 'refl_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_gloss': {'name': 'refl_gloss', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refl_samples': {'name': 'refl_samples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_norefl': {'name': 'refl_norefl', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'angularShift': {'name': 'angularShift', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'applyFresnel': {'name': 'applyFresnel', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'ior': {'name': 'ior', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'transp_color': {'name': 'transp_color', 'type': Sdf.ValueTypeNames.Color3f,
                                 'convert': MayaArrayToVector},
                'transp_weight': {'name': 'transp_weight', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'balanceEnergy': {'name': 'balanceEnergy', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'depth_override': {'name': 'depth_override', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_depth': {'name': 'refl_depth', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_enablecutoff': {'name': 'refl_enablecutoff', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refl_cutoff': {'name': 'refl_cutoff', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'trans_depth': {'name': 'trans_depth', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'trans_enablecutoff': {'name': 'trans_enablecutoff', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'trans_cutoff': {'name': 'trans_cutoff', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'combined_depth': {'name': 'combined_depth', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'shaveCompatibility': {'name': 'shaveCompatibility', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftIncandescent': {
                'info:id': {'name': 'redshift::Incandescent'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'color': {'name': 'color', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'temperature': {'name': 'temperature', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'colorMode': {'name': 'colorMode', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'intensity': {'name': 'intensity', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'doublesided': {'name': 'doublesided', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'applyExposureCompensation': {'name': 'applyExposureCompensation', 'type': Sdf.ValueTypeNames.Int,
                                              'convert': Same},
                'alphaMode': {'name': 'alphaMode', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'alpha': {'name': 'alpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'transparentShadows': {'name': 'transparentShadows', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'reflectScale': {'name': 'reflectScale', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'refractScale': {'name': 'refractScale', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'GIScale': {'name': 'GIScale', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'affectEmissionAOV': {'name': 'affectEmissionAOV', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftShaderSwitch': {
                'info:id': {'name': 'redshift::ShaderSwitch'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'selector': {'name': 'selector', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'selector_offset': {'name': 'selector_offset', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'shader0': {'name': 'shader0', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'shader1': {'name': 'shader1', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'shader2': {'name': 'shader2', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'shader3': {'name': 'shader3', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'shader4': {'name': 'shader4', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'shader5': {'name': 'shader5', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'shader6': {'name': 'shader6', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'shader7': {'name': 'shader7', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'shader8': {'name': 'shader8', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'shader9': {'name': 'shader9', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'default_shader': {'name': 'default_shader', 'type': Sdf.ValueTypeNames.Color3f,
                                   'convert': MayaArrayToVector},

                'post_proc': self.post_Nothing
            },
            'RedshiftSprite': {
                'info:id': {'name': 'redshift::Sprite'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'input': {'name': 'input', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'tex0': {'name': 'tex0', 'type': Sdf.ValueTypeNames.Asset, 'convert': Same},
                'mode': {'name': 'mode', 'type': Sdf.ValueTypeNames.Int, 'convert': IntToString},
                'repeats': {'name': 'repeats', 'type': Sdf.ValueTypeNames.Float2, 'convert': Same},
                'tex0_gammaoverride': {'name': 'tex0_gammaoverride', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'tex0_srgb': {'name': 'tex0_srgb', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'tex0_gamma': {'name': 'tex0_gamma', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftDisplacement': {
                'info:id': {'name': 'redshift::Displacement'},
                'out': {'name': 'out', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'scale': {'name': 'scale', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'texMap': {'name': 'texMap', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'map_encoding': {'name': 'map_encoding', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'space_type': {'name': 'space_type', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'newrange_max': {'name': 'newrange_max', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'newrange_min': {'name': 'newrange_min', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'oldrange_max': {'name': 'oldrange_max', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'oldrange_min': {'name': 'oldrange_min', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftDisplacementBlender': {
                'info:id': {'name': 'redshift::DisplacementBlender'},
                'out': {'name': 'out', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'baseInput': {'name': 'baseInput', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'displaceInput0': {'name': 'displaceInput0', 'type': Sdf.ValueTypeNames.Float,
                                   'convert': MayaArrayToFloat},
                'displaceInput1': {'name': 'displaceInput1', 'type': Sdf.ValueTypeNames.Float,
                                   'convert': MayaArrayToFloat},
                'displaceInput2': {'name': 'displaceInput2', 'type': Sdf.ValueTypeNames.Float,
                                   'convert': MayaArrayToFloat},

                'displaceWeight0': {'name': 'displaceWeight0', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'displaceWeight1': {'name': 'displaceWeight1', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'displaceWeight2': {'name': 'displaceWeight2', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'additive': {'name': 'additive', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'displacementShader': {
                'info:id': {'name': 'redshift::Displacement'},
                'displacement': {'name': 'out', 'type': Sdf.ValueTypeNames.Float3, 'convert': FloatToVector},
                'scale': {'name': 'scale', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'post_proc': self.post_displacemenShader
            },
            'file': {
                'info:id': {'name': "redshift::TextureSampler"},
                'output': {'name': 'out', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'outColorR': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': FloatToVector},
                'outColorG': {'name': 'outColor',
                              'type': Sdf.ValueTypeNames.Color3f,
                              'convert': FloatToVector},
                'outColorB': {'name': 'outColor',
                              'type': Sdf.ValueTypeNames.Color3f,
                              'convert': FloatToVector},
                'outAlpha': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': FloatToVector},
                'colorGain': {'name': 'color_multiplier', 'type': Sdf.ValueTypeNames.Color3f,
                              'convert': MayaArrayToVector},
                'colorOffset': {'name': 'color_offset', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'defaultColor': {'name': 'invalid_color', 'type': Sdf.ValueTypeNames.Color3f,
                                 'convert': MayaArrayToVector},
                'alphaOffset': {'name': 'alpha_offset', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'alphaGain': {'name': 'alpha_multiplier', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'fileTextureName': {'name': 'tex0', 'type': Sdf.ValueTypeNames.Asset, 'convert': Same},
                'alphaIsLumianace': {'name': 'alpha_is_luminance', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'rsFilterEnable': {'name': 'filter_enable_mode', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'rsMipBias': {'name': 'mip_bias', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'rsBicubicFiltering': {'name': 'filter_bicubic', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'post_proc': self.post_TextureSampler
            },
            'ramp': {
                'info:id': {'name': "redshift::RSRamp"},
                'outAlpha': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': FloatToVector},
                'post_proc': self.post_Ramp
            },
            'RedshiftWireFrame': {
                'info:id': {'name': 'redshift::WireFrame'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'polyColor': {'name': 'polyColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'wireColor': {'name': 'wireColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'thickness': {'name': 'thickness', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'showHiddenEdges': {'name': 'showHiddenEdges', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftStoreColorToAOV': {
                'info:id': {'name': 'redshift::StoreColorToAOV'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'beauty_input': {'name': 'beauty_input', 'type': Sdf.ValueTypeNames.Color3f,
                                 'convert': MayaArrayToVector},

                'post_proc': self.post_Nothing
            },
            'RedshiftStoreIntegerToAOV': {
                'info:id': {'name': 'redshift::StoreIntegerToAOV'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'beauty_input': {'name': 'beauty_input', 'type': Sdf.ValueTypeNames.Color3f,
                                 'convert': MayaArrayToVector},

                'post_proc': self.post_Nothing
            },
            'RedshiftStoreScalarToAOV': {
                'info:id': {'name': 'redshift::StoreScalarToAOV'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'beauty_input': {'name': 'beauty_input', 'type': Sdf.ValueTypeNames.Color3f,
                                 'convert': MayaArrayToVector},

                'post_proc': self.post_Nothing
            },
            'RedshiftUserDataColor': {
                'info:id': {'name': 'redshift::RSUserDataColor'},
                'out': {'name': 'out', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'attributeName': {'name': 'attributeName', 'type': Sdf.ValueTypeNames.String, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            # 'RedshiftUserDataScalar': {
            #     'info:id': {'name': 'redshift::RSUserDataScalar'},
            #     'out': {'name': 'out', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
            #     'attributeName': {'name': 'attributeName', 'type': Sdf.ValueTypeNames.String, 'convert': Same},
            #
            #     'post_proc': self.post_Nothing
            # },
            'RedshiftUserDataScalar': {
                'info:id': {'name': 'redshift::ParticleAttributeLookup'},
                'out': {
                    'name': 'outScalar',
                    'type': Sdf.ValueTypeNames.Float,
                    'convert': Same
                },
                'attributeName': {
                    'name': 'attribute',
                    'type': Sdf.ValueTypeNames.String,
                    'convert': Same
                },
                'post_proc': self.post_Nothing
            },
            'RSVectorMaker': {
                'info:id': {'name': 'redshift::RSVectorMaker'},
                'out': {
                    'name': 'out',
                    'type': Sdf.ValueTypeNames.Vector3f,
                    'convert': Same
                },
                'x': {
                    'name': 'x',
                    'type': Sdf.ValueTypeNames.Float,
                    'convert': Same
                },
                'y': {
                    'name': 'y',
                    'type': Sdf.ValueTypeNames.Float,
                    'convert': Same
                },
                'z': {
                    'name': 'z',
                    'type': Sdf.ValueTypeNames.Float,
                    'convert': Same
                },
                'post_proc': self.post_Nothing
            },
            'RSVectorToScalars': {
                'info:id': {'name': 'redshift::RSVectorToScalars'},
                'input': {
                    'name': 'input',
                    'type': Sdf.ValueTypeNames.Vector3f,
                    'convert': Same
                },
                'outValueX': {
                    'name': 'outX',
                    'type': Sdf.ValueTypeNames.Float,
                    'convert': Same
                },
                'outValueY': {
                    'name': 'outY',
                    'type': Sdf.ValueTypeNames.Float,
                    'convert': Same
                },
                'outValueZ': {
                    'name': 'outZ',
                    'type': Sdf.ValueTypeNames.Float,
                    'convert': Same
                },
                'post_proc': self.post_Nothing
            },
            'RedshiftUserDataVector': {
                'info:id': {'name': 'redshift::RSUserDataVector'},
                'out': {'name': 'out', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'attributeName': {'name': 'attributeName', 'type': Sdf.ValueTypeNames.String, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftUserDataInteger': {
                'info:id': {'name': 'redshift::RSUserDataInteger'},
                'out': {'name': 'out', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'attributeName': {'name': 'attributeName', 'type': Sdf.ValueTypeNames.String, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftTriPlanar': {
                'info:id': {'name': 'redshift::TriPlanar'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'outAlpha': {'name': 'outAlpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'sameImageOnEachAxis': {'name': 'sameImageOnEachAxis', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'imageX': {'name': 'imageX', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'imageXAlpha': {'name': 'imageXAlpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'imageY': {'name': 'imageY', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'imageYAlpha': {'name': 'imageYAlpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'imageZ': {'name': 'imageZ', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'imageZAlpha': {'name': 'imageZAlpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'blendAmount': {'name': 'blendAmount', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'blendCurve': {'name': 'blendCurve', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'scale': {'name': 'scale', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'offset': {'name': 'offset', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'rotation': {'name': 'rotation', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'projSpaceType': {'name': 'projSpaceType', 'type': Sdf.ValueTypeNames.Int, 'convert': IntToString},
                'isLeftHanded': {'name': 'isLeftHanded', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'yIsUp': {'name': 'yIsUp', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftAttributeLookup': {
                'info:id': {'name': 'redshift::VertexAttributeLookup'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'outScalar': {'name': 'outScalar', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'attributeName': {'name': 'attributeName', 'type': Sdf.ValueTypeNames.String, 'convert': Same},
                'defaultColor': {'name': 'defaultColor', 'type': Sdf.ValueTypeNames.Color3f,
                                 'convert': MayaArrayToVector},
                'defaultScalar': {'name': 'defaultScalar', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftRaySwitch': {
                'info:id': {'name': 'redshift::RaySwitch'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'cameraSwitchFrontBack': {'name': 'cameraSwitchFrontBack', 'type': Sdf.ValueTypeNames.Int,
                                          'convert': Same},
                'cameraColor': {'name': 'cameraColor', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},
                'cameraColorBack': {'name': 'cameraColorBack', 'type': Sdf.ValueTypeNames.Color3f,
                                    'convert': MayaArrayToVector},
                'reflectionSwitch': {'name': 'reflectionSwitch', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'reflectionSwitchFrontBack': {'name': 'reflectionSwitchFrontBack', 'type': Sdf.ValueTypeNames.Int,
                                              'convert': Same},
                'reflectionColor': {'name': 'reflectionColor', 'type': Sdf.ValueTypeNames.Color3f,
                                    'convert': MayaArrayToVector},
                'reflectionColorBack': {'name': 'reflectionColorBack', 'type': Sdf.ValueTypeNames.Color3f,
                                        'convert': MayaArrayToVector},
                'refractionSwitch': {'name': 'refractionSwitch', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'refractionSwitchFrontBack': {'name': 'refractionSwitchFrontBack', 'type': Sdf.ValueTypeNames.Int,
                                              'convert': Same},
                'refractionColor': {'name': 'refractionColor', 'type': Sdf.ValueTypeNames.Color3f,
                                    'convert': MayaArrayToVector},
                'refractionColorBack': {'name': 'refractionColorBack', 'type': Sdf.ValueTypeNames.Color3f,
                                        'convert': MayaArrayToVector},
                'giSwitch': {'name': 'giSwitch', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'giSwitchFrontBack': {'name': 'giSwitchFrontBack', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'giColor': {'name': 'giColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'giColorBack': {'name': 'giColorBack', 'type': Sdf.ValueTypeNames.Color3f,
                                'convert': MayaArrayToVector},

                'post_proc': self.post_Nothing
            },
            'RedshiftHairRandomColor': {
                'info:id': {'name': 'redshift::HairRandomColor'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'color': {'name': 'color', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'hueAmount': {'name': 'hueAmount', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'satAmount': {'name': 'satAmount', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'valAmount': {'name': 'valAmount', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftState': {
                'info:id': {'name': 'redshift::State'},
                'outNormal': {'name': 'outNormal', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'outBumpNormal': {'name': 'outBumpNormal', 'type': Sdf.ValueTypeNames.Float3,
                                  'convert': MayaArrayToVector},
                'outTriNormal': {'name': 'outTriNormal', 'type': Sdf.ValueTypeNames.Float3,
                                 'convert': MayaArrayToVector},
                'outTangent': {'name': 'outTangent', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'outBitangent': {'name': 'outBitangent', 'type': Sdf.ValueTypeNames.Float3,
                                 'convert': MayaArrayToVector},
                'outRayOrigin': {'name': 'outRayOrigin', 'type': Sdf.ValueTypeNames.Float3,
                                 'convert': MayaArrayToVector},
                'outRayDirection': {'name': 'outRayDirection', 'type': Sdf.ValueTypeNames.Float3,
                                    'convert': MayaArrayToVector},
                'outRayPosition': {'name': 'outRayPosition', 'type': Sdf.ValueTypeNames.Float3,
                                   'convert': MayaArrayToVector},
                'outRayLength': {'name': 'outRayLength', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'trans_space': {'name': 'trans_space', 'type': Sdf.ValueTypeNames.Int, 'convert': IntToString},
                'showRayFacingNormals': {'name': 'showRayFacingNormals', 'type': Sdf.ValueTypeNames.Int,
                                         'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftColorLayer': {
                'info:id': {'name': 'redshift::RSColorLayer'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                # 'outAlpha': {'name': 'outAlpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'advanced_mode': {'name': 'advanced_mode', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'base_color': {'name': 'base_color', 'type': Sdf.ValueTypeNames.Color4f, 'convert': VectorToVector4},
                # 'base_alpha': {'name': 'base_alpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'base_color_premult': {'name': 'base_color_premult', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'layer1_enable': {'name': 'layer1_enable', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'layer1_color': {'name': 'layer1_color', 'type': Sdf.ValueTypeNames.Color4f,
                                 'convert': VectorToVector4},
                # 'layer1_alpha': {'name': 'layer1_alpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'layer1_mask': {'name': 'layer1_mask', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'layer1_blend_mode': {'name': 'layer1_blend_mode', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'layer1_overlay_mode': {'name': 'layer1_overlay_mode', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'layer1_color_premult': {'name': 'layer1_color_premult', 'type': Sdf.ValueTypeNames.Bool, 'convert': Same},
                'layer2_enable': {'name': 'layer2_enable', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'layer2_color': {'name': 'layer2_color', 'type': Sdf.ValueTypeNames.Color4f,
                                 'convert': VectorToVector4},
                'layer2_alpha': {'name': 'layer2_alpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'layer2_mask': {'name': 'layer2_mask', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'layer2_blend_mode': {'name': 'layer2_blend_mode', 'type': Sdf.ValueTypeNames.Token,
                                      'convert': IntToString},
                'layer2_overlay_mode': {'name': 'layer2_overlay_mode', 'type': Sdf.ValueTypeNames.Token,
                                        'convert': IntToString},
                'layer2_color_premult': {'name': 'layer2_color_premult', 'type': Sdf.ValueTypeNames.Bool,
                                         'convert': Same},
                'layer3_enable': {'name': 'layer3_enable', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'layer3_color': {'name': 'layer3_color', 'type': Sdf.ValueTypeNames.Color4f,
                                 'convert': VectorToVector4},
                'layer3_alpha': {'name': 'layer3_alpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'layer3_mask': {'name': 'layer3_mask', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'layer3_blend_mode': {'name': 'layer3_blend_mode', 'type': Sdf.ValueTypeNames.Token,
                                      'convert': IntToString},
                'layer3_overlay_mode': {'name': 'layer3_overlay_mode', 'type': Sdf.ValueTypeNames.Token,
                                        'convert': IntToString},
                'layer3_color_premult': {'name': 'layer3_color_premult', 'type': Sdf.ValueTypeNames.Bool,
                                         'convert': Same},
                'layer4_enable': {'name': 'layer4_enable', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'layer4_color': {'name': 'layer4_color', 'type': Sdf.ValueTypeNames.Color4f,
                                 'convert': VectorToVector4},
                'layer4_alpha': {'name': 'layer4_alpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'layer4_mask': {'name': 'layer4_mask', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'layer4_blend_mode': {'name': 'layer4_blend_mode', 'type': Sdf.ValueTypeNames.Token,
                                      'convert': IntToString},
                'layer4_overlay_mode': {'name': 'layer4_overlay_mode', 'type': Sdf.ValueTypeNames.Token,
                                        'convert': IntToString},
                'layer4_color_premult': {'name': 'layer4_color_premult', 'type': Sdf.ValueTypeNames.Bool,
                                         'convert': Same},
                'layer5_enable': {'name': 'layer5_enable', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'layer5_color': {'name': 'layer5_color', 'type': Sdf.ValueTypeNames.Color4f,
                                 'convert': VectorToVector4},
                'layer5_alpha': {'name': 'layer5_alpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'layer5_mask': {'name': 'layer5_mask', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'layer5_blend_mode': {'name': 'layer5_blend_mode', 'type': Sdf.ValueTypeNames.Token,
                                      'convert': IntToString},
                'layer5_overlay_mode': {'name': 'layer5_overlay_mode', 'type': Sdf.ValueTypeNames.Token,
                                        'convert': IntToString},
                'layer5_color_premult': {'name': 'layer5_color_premult', 'type': Sdf.ValueTypeNames.Bool,
                                         'convert': Same},
                'layer6_enable': {'name': 'layer6_enable', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'layer6_color': {'name': 'layer6_color', 'type': Sdf.ValueTypeNames.Color4f,
                                 'convert': VectorToVector4},
                'layer6_alpha': {'name': 'layer6_alpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'layer6_mask': {'name': 'layer6_mask', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'layer6_blend_mode': {'name': 'layer6_blend_mode', 'type': Sdf.ValueTypeNames.Token,
                                      'convert': IntToString},
                'layer6_overlay_mode': {'name': 'layer6_overlay_mode', 'type': Sdf.ValueTypeNames.Token,
                                        'convert': IntToString},
                'layer6_color_premult': {'name': 'layer6_color_premult', 'type': Sdf.ValueTypeNames.Bool,
                                         'convert': Same},
                'layer7_enable': {'name': 'layer7_enable', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'layer7_color': {'name': 'layer7_color', 'type': Sdf.ValueTypeNames.Color4f,
                                 'convert': VectorToVector4},
                'layer7_alpha': {'name': 'layer7_alpha', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'layer7_mask': {'name': 'layer7_mask', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'layer7_blend_mode': {'name': 'layer7_blend_mode', 'type': Sdf.ValueTypeNames.Token,
                                      'convert': IntToString},
                'layer7_overlay_mode': {'name': 'layer7_overlay_mode', 'type': Sdf.ValueTypeNames.Token,
                                        'convert': IntToString},
                'layer7_color_premult': {'name': 'layer7_color_premult', 'type': Sdf.ValueTypeNames.Bool,
                                         'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftBumpMap': {
                'info:id': {'name': 'redshift::BumpMap'},
                'out': {'name': 'out', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'input': {'name': 'input', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'inputType': {'name': 'inputType', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'scale': {'name': 'scale', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'flipY': {'name': 'flipY', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'unbiasedNormalMap': {'name': 'unbiasedNormalMap', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftBumpBlender': {
                'info:id': {'name': 'redshift::BumpBlender'},
                'outColor': {'name': 'outDisplacementVector', 'type': Sdf.ValueTypeNames.Float3,
                             'convert': MayaArrayToVector},
                'baseInput': {'name': 'baseInput', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'bumpInput0': {'name': 'bumpInput0', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'bumpInput1': {'name': 'bumpInput1', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'bumpInput2': {'name': 'bumpInput2', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},

                'bumpWeight0': {'name': 'bumpWeight0', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'bumpWeight1': {'name': 'bumpWeight1', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'bumpWeight2': {'name': 'bumpWeight2', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'additive': {'name': 'additive', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftNormalMap': {
                'info:id': {'name': 'redshift::NormalMap'},
                'outDisplacementVector': {'name': 'outDisplacementVector', 'type': Sdf.ValueTypeNames.Float3,
                                          'convert': MayaArrayToVector},
                'scale': {'name': 'scale', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'eccmax': {'name': 'eccmax', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'flipY': {'name': 'flipY', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'alt_x': {'name': 'alt_x', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'alt_y': {'name': 'alt_y', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'tex0': {'name': 'tex0', 'type': Sdf.ValueTypeNames.Asset, 'convert': Same},
                'min_uv': {'name': 'min_uv', 'type': Sdf.ValueTypeNames.Float2, 'convert': MayaArrayToFloat2},
                'max_uv': {'name': 'max_uv', 'type': Sdf.ValueTypeNames.Float2, 'convert': MayaArrayToFloat2},
                'unbiasedNormalMap': {'name': 'unbiasedNormalMap', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftAmbientOcclusion': {
                'info:id': {'name': 'redshift::AmbientOcclusion'},
                'out': {'name': 'out', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'bright': {'name': 'bright', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'dark': {'name': 'dark', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},

                'spread': {'name': 'spread', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'fallOff': {'name': 'fallOff', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'maxDistance': {'name': 'maxDistance', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'numSamples': {'name': 'numSamples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'reflective': {'name': 'reflective', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'invert': {'name': 'invert', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'occlusionInAlpha': {'name': 'occlusionInAlpha', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'sameObjectOnly': {'name': 'sameObjectOnly', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'outputMode': {'name': 'outputMode', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},

                'post_proc': self.post_Nothing
            },
            'RedshiftCurvature': {
                'info:id': {'name': 'redshift::Curvature'},
                'out': {'name': 'out', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'radius': {'name': 'radius', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'inputMin': {'name': 'inputMin', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'inputMax': {'name': 'inputMax', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'contrastVal': {'name': 'contrastVal', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'contrastPivot': {'name': 'contrastPivot', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'bias': {'name': 'bias', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'gain': {'name': 'gain', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'outputMin': {'name': 'outputMin', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'outputMax': {'name': 'outputMax', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'clampMin': {'name': 'clampMin', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'clampMax': {'name': 'clampMax', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'mode': {'name': 'mode', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'numSamples': {'name': 'numSamples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'sameObjectOnly': {'name': 'sameObjectOnly', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'clampEnable': {'name': 'clampEnable', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'clampExpand': {'name': 'clampExpand', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftRoundCorners': {
                'info:id': {'name': 'redshift::RoundCorners'},
                'out': {'name': 'out', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'radius': {'name': 'radius', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'numSamples': {'name': 'numSamples', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'sameObjectOnly': {'name': 'sameObjectOnly', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftFresnel': {
                'info:id': {'name': 'redshift::Fresnel'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'facing_color': {'name': 'facing_color', 'type': Sdf.ValueTypeNames.Color3f,
                                 'convert': MayaArrayToVector},
                'perp_color': {'name': 'perp_color', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'ior': {'name': 'ior', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'user_curve': {'name': 'user_curve', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'extinction_coeff': {'name': 'extinction_coeff', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'correct_intensity': {'name': 'correct_intensity', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'fresnel_useior': {'name': 'fresnel_useior', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'bump_input': {'name': 'bump_input', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},

                'post_proc': self.post_Nothing
            },
            'RedshiftColorCorrection': {
                'info:id': {'name': 'redshift::RSColorCorrection'},
                'input': {'name': 'input', 'type': Sdf.ValueTypeNames.Color4f, 'convert': VectorToVector4},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'gamma': {'name': 'gamma', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'contrast': {'name': 'contrast', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'hue': {'name': 'hue', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'saturation': {'name': 'saturation', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'level': {'name': 'level', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftNoise': {
                'info:id': {'name': 'redshift::RSNoise'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'color1': {'name': 'color1', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'color2': {'name': 'color2', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'range_min': {'name': 'range_min', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'range_max': {'name': 'range_max', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'range_bias': {'name': 'range_bias', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'noise_gain': {'name': 'noise_gain', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'noise_scale': {'name': 'noise_scale', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'distort': {'name': 'distort', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'distort_scale': {'name': 'distort_scale', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'time': {'name': 'time', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'time_constant': {'name': 'time_constant', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'coord_scale_global': {'name': 'coord_scale_global', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'coord_scale': {'name': 'coord_scale', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'coord_offset': {'name': 'coord_offset', 'type': Sdf.ValueTypeNames.Float3,
                                 'convert': MayaArrayToVector},

                'noise_type': {'name': 'noise_type', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'time_source': {'name': 'time_source', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'coord_source': {'name': 'coord_source', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'color_invert': {'name': 'color_invert', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'noise_complexity': {'name': 'noise_complexity', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            'RedshiftMaxonNoise': {
                'info:id': {'name': 'redshift::MaxonNoise'},
                'outColor': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'color1': {'name': 'color1', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'color2': {'name': 'color2', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
                'octaves': {'name': 'octaves', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'lacunarity': {'name': 'lacunarity', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'gain': {'name': 'gain', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'exponent': {'name': 'exponent', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'animation_speed': {'name': 'animation_speed', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},

                'animation_time': {'name': 'animation_time', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'cycles': {'name': 'cycles', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'low_clip': {'name': 'low_clip', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'high_clip': {'name': 'high_clip', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'brightness': {'name': 'brightness', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'contrast': {'name': 'contrast', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'coord_scale_global': {'name': 'coord_scale_global', 'type': Sdf.ValueTypeNames.Float, 'convert': Same},
                'coord_scale': {'name': 'coord_scale', 'type': Sdf.ValueTypeNames.Float3, 'convert': MayaArrayToVector},
                'coord_offset': {'name': 'coord_offset', 'type': Sdf.ValueTypeNames.Float3,
                                 'convert': MayaArrayToVector},

                'noise_type': {'name': 'noise_type', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'animation_source': {'name': 'animation_source', 'type': Sdf.ValueTypeNames.Token,
                                     'convert': IntToString},
                'absolute': {'name': 'absolute', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},
                'coord_source': {'name': 'coord_source', 'type': Sdf.ValueTypeNames.Token, 'convert': IntToString},
                'seed': {'name': 'seed', 'type': Sdf.ValueTypeNames.Int, 'convert': Same},

                'post_proc': self.post_Nothing
            },
            # 'setRange': {
            #     'info:id': {'name': 'redshift::RSColorRange'},
            #     'value': {'name': 'input', 'type': Sdf.ValueTypeNames.Color4f, 'convert': VectorToVector4},
            #     'outValue': {'name': 'outColor', 'type': Sdf.ValueTypeNames.Color3f, 'convert': MayaArrayToVector},
            #     'min': {'name': 'new_min', 'type': Sdf.ValueTypeNames.Color4f, 'convert': VectorToVector4},
            #     'max': {'name': 'new_max', 'type': Sdf.ValueTypeNames.Color4f, 'convert': VectorToVector4},
            #     'oldMin': {'name': 'old_min', 'type': Sdf.ValueTypeNames.Color4f, 'convert': VectorToVector4},
            #     'oldMax': {'name': 'old_max', 'type': Sdf.ValueTypeNames.Color4f, 'convert': VectorToVector4},
            #
            #     'post_proc': self.post_Nothing
            # },
            'setRange': {
                'info:id': {'name': 'redshift::RSMathRangeVector'},
                'value': {'name': 'input', 'type': Sdf.ValueTypeNames.Vector3f,
                          'convert': MayaArrayToVector},
                'outValue': {'name': 'out',
                             'type': Sdf.ValueTypeNames.Vector3f,
                             'convert': MayaArrayToVector},
                'outValueX': {
                    'attr_proc': self.attr_proc_setRange_outValue,
                },
                'outValueY': {
                    'attr_proc': self.attr_proc_setRange_outValue,
                },
                'outValueZ': {
                    'attr_proc': self.attr_proc_setRange_outValue,
                },
                'min': {'name': 'new_min', 'type': Sdf.ValueTypeNames.Vector3f,
                        'convert': MayaArrayToVector},
                'max': {'name': 'new_max', 'type': Sdf.ValueTypeNames.Vector3f,
                        'convert': MayaArrayToVector},
                'oldMin': {'name': 'old_min',
                           'type': Sdf.ValueTypeNames.Vector3f,
                           'convert': MayaArrayToVector},
                'oldMax': {'name': 'old_max',
                           'type': Sdf.ValueTypeNames.Vector3f,
                           'convert': MayaArrayToVector},
                'post_proc': self.post_setRange
            }
        }
        self.shadingGroups = shadingGroups
        self.scopeName = scopeName
        self.filename = filename
        self.assetVersion = assetVersion
        self.assetName = assetName
        self.ExportMaterials()

    def ExportMaterials(self):
        import maya.cmds as cmds

        # Build Stage
        self.stage = Usd.Stage.CreateInMemory()
        # Build Root Scope
        self.scope = UsdGeom.Scope.Define(self.stage, '/ROOT/' + self.scopeName)
        scopeRoot = self.scope.GetPrim()

        if self.assetName:
            scopeRoot.SetAssetInfoByKey("version", self.assetVersion)
        if self.assetName:
            scopeRoot.SetAssetInfoByKey("name", self.assetName)

        root_prim = self.stage.GetPrimAtPath('/ROOT')
        self.stage.SetDefaultPrim(root_prim)
        # self.stage.SetDefaultPrim(scopeRoot)

        for shadingGroup in self.shadingGroups:
            surfaceShaders = cmds.listConnections(
                shadingGroup + '.surfaceShader')
            if surfaceShaders:
                surfaceShader = surfaceShaders[0]
                self._check_usd_preview(surfaceShader, shadingGroup)

            usdShadingGroup = UsdShade.Material.Define(
                self.stage,
                self.scope.GetPath().AppendChild(
                    self.procNamespace(shadingGroup)
                )
            )
            usdShaderCollector = UsdShade.Shader.Define(
                self.stage,
                usdShadingGroup.GetPath().AppendChild(
                    self.procNamespace(shadingGroup)
                )
            )
            usdShaderCollector.CreateIdAttr('redshift_usd_material')
            usdShaderCollector.CreateOutput('Shader', Sdf.ValueTypeNames.Token)
            usdShadingGroup.CreateOutput(
                'Redshift:surface',
                Sdf.ValueTypeNames.Token).\
                ConnectToSource(usdShaderCollector, 'Shader')

            if surfaceShaders:
                surfaceShader = surfaceShaders[0]
                usdShaderCollector.CreateInput(
                    'Surface',
                    Sdf.ValueTypeNames.Color3f
                )
                source_attr = cmds.listConnections(
                    shadingGroup + '.surfaceShader',
                    p=True)[0].split('.')[-1]
                self.rebuildShader(
                    source_shader=surfaceShader,
                    usd_target=usdShaderCollector,
                    source_attr=source_attr,
                    target_attr='Surface',
                    usdShadingGroup=usdShadingGroup
                )

            displacementShaders = cmds.listConnections(
                shadingGroup + '.displacementShader'
            )
            if displacementShaders:
                displacementShader = displacementShaders[0]
                usdShaderCollector.CreateInput(
                    'Displacement',
                    Sdf.ValueTypeNames.Float3
                )
                source_attr = cmds.listConnections(
                    shadingGroup + '.displacementShader',
                    p=True)[0].split('.')[-1]
                self.rebuildShader(
                    source_shader=displacementShader,
                    usd_target=usdShaderCollector,
                    source_attr=source_attr,
                    target_attr='Displacement',
                    usdShadingGroup=usdShadingGroup
                )

    def _Color(self, r, g, b):
        # for this tutorial, the colors i got are not in linear space.
        from pxr import Gf
        return Gf.ConvertDisplayToLinear(Gf.Vec3f(r, g, b))

    def _check_usd_preview(self, source_shader, shadingGroup):
        import maya.cmds as cmds

        if cmds.attributeQuery('usd_preview', node=source_shader, ex=True):
            if cmds.getAttr('{}.usd_preview'.format(source_shader)):
                material = UsdShade.Material.Define(
                    self.stage,
                    self.scope.GetPath().AppendChild(
                        self.procNamespace(shadingGroup)
                    )
                )
                pbrShader = UsdShade.Shader.Define(
                    self.stage,
                    material.GetPath().AppendChild(
                        self.procNamespace(source_shader)))
                pbrShader.CreateIdAttr("UsdPreviewSurface")

                # Get color
                color = cmds.getAttr("{}.color".format(source_shader))[0]

                r, g, b = self._Color(color[0], color[1], color[2])
                pbrShader.CreateInput(
                    'diffuseColor',
                    Sdf.ValueTypeNames.Color3f).Set((r, g, b))

                material.CreateSurfaceOutput().ConnectToSource(
                    pbrShader, "surface")

                return True
        return False

    def rebuildShader(self, source_shader, usd_target, source_attr,
                      target_attr, usdShadingGroup):
        import maya.cmds as cmds

        nodeType = cmds.nodeType(source_shader)

        # Creating the Shader. Check nodeType if in translator dictionary
        if nodeType in self.translator.keys():
            attr_table = self.translator[nodeType]
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
                    self.translator[nodeType]['info:id']['name']
                )
            else:
                usdShader = UsdShade.Shader.Get(
                    self.stage,
                    usdShadingGroup.GetPath().AppendChild(
                        self.procNamespace(source_shader)
                    )
                )

            # Check connection input if in translator dictionary
            if source_attr in attr_table.keys():
                if attr_table[source_attr].get('attr_proc', None):
                    attr_table[source_attr]['attr_proc'](
                        source_shader, usdShader, usdShadingGroup,
                        last_usd_target=usd_target,
                        last_target_attr=target_attr,
                        source_attr=source_attr
                    )
                else:
                    if attr_table[source_attr]['name'] not in \
                            [x.GetBaseName() for x in usdShader.GetOutputs()]:
                        usdShaderOutput = usdShader.CreateOutput(
                            attr_table[source_attr]['name'],
                            attr_table[source_attr]['type']
                        )
                    else:
                        usdShaderOutput = usdShader.GetOutput(
                            attr_table[source_attr]['name'])

                    # Connect
                    usd_target.GetInput(target_attr).\
                        ConnectToSource(usdShaderOutput)
            else:
                msg = "{}.{}".format(source_shader, source_attr)
                print("Source attribute not in dict: {}".format(msg))
                return

            # Creating the attributes and setting the value
            for attr in cmds.listAttr(source_shader, hd=True):
                if attr in attr_table.keys():
                    if "attr_proc" in attr_table[attr].keys():
                        continue

                    if nodeType == 'RedshiftColorLayer':
                        match = re.findall('(layer+\S)', attr)
                        if match:
                            if not cmds.getAttr("{}.{}_enable".format(source_shader, match[0])):
                                continue

                    if nodeType == 'file' and attr == 'fileTextureName':
                        _value = self._get_fileTextureName(source_shader)
                    else:
                        _value = cmds.getAttr(
                            '{}.{}'.format(source_shader, attr),
                            x=True
                        )

                    usdShader.CreateInput(
                        attr_table[attr]['name'],
                        attr_table[attr]['type']).\
                        Set(attr_table[attr]['convert'](_value))

            if attr_table['post_proc'](
                    source_shader, usdShader, usdShadingGroup):

                all_connections = cmds.listConnections(source_shader, d=False, c=True, p=True)
                if all_connections:
                    connections = iter(all_connections)

                    for connectDest, connectSource in zip(connections, connections):

                        connectSourceNode = connectSource.split('.')[0]
                        connectSourceAttr = connectSource.split('.')[-1]
                        # connectDestNode = connectDest.split('.')[0]
                        connectDestAttr = connectDest.split('.')[-1]

                        _target_attr = ""
                        if cmds.nodeType(connectSourceNode) == "setRange" and \
                                connectSourceAttr != "outValue":
                            connectDestAttr = self._attr_remove_rgb(connectDestAttr)
                            _target_attr = connectDestAttr

                        if connectDestAttr in attr_table.keys():
                            if not _target_attr:
                                _target_attr = attr_table[connectDestAttr]['name']
                            self.rebuildShader(
                                source_shader=connectSourceNode,
                                usd_target=usdShader,
                                source_attr=connectSourceAttr,
                                target_attr=_target_attr,
                                usdShadingGroup=usdShadingGroup
                            )
                        # else:
                        #     return
        else:
            return

    def _attr_remove_rgb(self, attr_name):
        for _k in ["colorR", "colorG", "colorB"]:
            attr_name = attr_name.replace(_k, "color")\
        # .replace("colorG", "color").replace("colorB", "color")

        return attr_name

    def _get_fileTextureName(self, node):
        import maya.cmds as cmds

        if cmds.attributeQuery(
                'computedFileTextureNamePattern',
                node=node,
                exists=True
        ):
            texture_pattern = cmds.getAttr(
                '{}.computedFileTextureNamePattern'.format(node))

            patterns = [
                "<udim>", "<tile>", "u<u>_v<v>", "<f>", "<frame0", "<uvtile>"]
            lower = texture_pattern.lower()
            if any(pattern in lower for pattern in patterns):
                return texture_pattern

        # Otherwise use fileTextureName
        return cmds.getAttr('{0}.fileTextureName'.format(node))

    # USD Shader post process
    def post_Nothing(self, mayaShader, usdShader, usdShadingGroup):
        return True

    def attr_proc_setRange_outValue(
            self, mayaShader, usdShader, usdShadingGroup,
            last_usd_target=None, last_target_attr=None, source_attr=None):
        """
        Create "RSVectorToScalars" node between setRange node and the source
        node of setRange node.
        :param mayaShader: setRange node maya shader
        :param usdShader: setRange node usd shader
        :param usdShadingGroup: usdShadingGroup
        :param last_usd_target: The source usd shader of setRange node.
            eg. The usd shader of RedshiftMaterial node
        :param last_target_attr: Attribute name of laset usd shader node.
            eg. The attribute name "refr_roughness" of RedshiftMaterial node
        :param source_attr: The output attribute name of setRange node.
            eg. outValueX/outValueY/outValueZ
        :return:
        """

        from set_range_builder import SetRangeBuilder
        # last_target_attr = last_target_attr.replace("colorR", "color").replace("colorG", "color").replace("colorB", "color")
        if mayaShader not in self.vector_scalars_builder.keys():
            _builder = SetRangeBuilder(
                    self.stage,
                    self.translator,
                    self.procNamespace)

            _builder.post_setRange(mayaShader, usdShader, usdShadingGroup,
                                   last_usd_target, last_target_attr, source_attr)

    # def add_vector_to_scalars_node(
    #         self, source_shader=None, source_attr=None,
    #         usd_target=None, target_attr=None, usdShadingGroup=None):
    #     """
    #     Create setRange node and the source node of setRange node.
    #     :param source_shader: The node name of setRange node
    #     :param source_attr: The output attribute name of setRange node
    #     :param usd_target: Target usd shader.
    #         eg. The RedshiftMaterial node's usd shader
    #     :param target_attr: Attribute name of target shader node.
    #         eg. The attribute name "refr_roughness" of RedshiftMaterial node
    #     :param usdShadingGroup:
    #     :return:
    #     """
    #
    #     self.rebuildShader(
    #         source_shader=source_shader,
    #         usd_target=usd_target,
    #         source_attr=source_attr,  # outValueX/outValueY/outValueZ
    #         target_attr=target_attr,
    #         usdShadingGroup=usdShadingGroup
    #     )

    def post_setRange(self, mayaShader, usdShader, usdShadingGroup):
        from set_range_builder import SetRangeBuilder

        set_range_builder = SetRangeBuilder(
            self.stage,
            self.translator,
            self.procNamespace)
        set_range_builder.pre_setRange(mayaShader, usdShader, usdShadingGroup)

        return False

    def post_displacemenShader(self, mayaShader, usdShader, usdShadingGroup):
        import maya.cmds as cmds

        if cmds.listConnections(mayaShader + '.displacement',
                                s=True, d=False, p=True):
            connectSourceNode, source_attr = \
            cmds.listConnections(mayaShader + '.displacement',
                                 s=True, d=False, p=True)[0].split('.')
            usdShader.CreateInput('scale', Sdf.ValueTypeNames.Float)
            self.rebuildShader(
                source_shader=connectSourceNode,
                usd_target=usdShader,
                source_attr=source_attr,
                target_attr='scale',
                usdShadingGroup=usdShadingGroup
            )
        elif cmds.listConnections(mayaShader + '.vectorDisplacement',
                                  s=True, d=False, p=True):
            connectSourceNode, source_attr = \
            cmds.listConnections(mayaShader + '.vectorDisplacement',
                                 s=True, d=False, p=True)[0].split('.')
            usdShader.CreateInput('texMap', Sdf.ValueTypeNames.Color3f)
            self.rebuildShader(
                source_shader=connectSourceNode,
                usd_target=usdShader,
                source_attr=source_attr,
                target_attr='texMap',
                usdShadingGroup=usdShadingGroup
            )
        return False

    def post_Ramp(self, mayaShader, usdShader, usdShadingGroup):
        import maya.cmds as cmds
        from reveries.common.maya_shader_export.ramp import RampSampler

        ramper = RampSampler(mayaShader)

        _node_type = str(cmds.getAttr('{}.type'.format(mayaShader)))
        usdShader.CreateInput('inputMapping', Sdf.ValueTypeNames.Token).Set(
            _node_type)

        usdShader.CreateInput('ramp_basis', Sdf.ValueTypeNames.String).Set(
            ramper.get_basis_name())
        usdShader.CreateInput('ramp', Sdf.ValueTypeNames.Int).Set(
            ramper.get_key_number())
        usdShader.CreateInput('ramp_keys', Sdf.ValueTypeNames.FloatArray).Set(
            ramper.get_keys_list())
        usdShader.CreateInput(
            'ramp_values', Sdf.ValueTypeNames.Float3Array).Set(
            ramper.get_color_list())

        self._uv_coord(mayaShader, usdShader)

    def _uv_coord(self, mayaShader, usdShader):
        import maya.cmds as cmds

        connections = cmds.listConnections(mayaShader + '.uvCoord')
        if connections and cmds.nodeType(connections[0]) == 'place2dTexture':
            uv_coord = connections[0]
            usdShader.CreateInput('mirrorU', Sdf.ValueTypeNames.Int).Set(
                cmds.getAttr(uv_coord + '.mirrorU'))
            usdShader.CreateInput('mirrorV', Sdf.ValueTypeNames.Int).Set(
                cmds.getAttr(uv_coord + '.mirrorV'))
            usdShader.CreateInput('wrapU', Sdf.ValueTypeNames.Int).Set(
                cmds.getAttr(uv_coord + '.wrapU'))
            usdShader.CreateInput('wrapV', Sdf.ValueTypeNames.Int).Set(
                cmds.getAttr(uv_coord + '.wrapV'))
            usdShader.CreateInput('rotate', Sdf.ValueTypeNames.Float).Set(
                cmds.getAttr(uv_coord + '.rotateUV'))
            usdShader.CreateInput('offset', Sdf.ValueTypeNames.Float2).Set(
                cmds.getAttr(uv_coord + '.offset')[0])

    def post_TextureSampler(self, mayaShader, usdShader, usdShadingGroup):
        import maya.cmds as cmds

        color_space = cmds.getAttr(mayaShader + '.colorSpace')
        if color_space == 'sRGB':
            usdShader.CreateInput('tex0_srgb', Sdf.ValueTypeNames.Int).Set(1)
        else:
            usdShader.CreateInput('tex0_srgb', Sdf.ValueTypeNames.Int).Set(0)

        usdShader.CreateInput('tspace_id', Sdf.ValueTypeNames.String).Set("uv")
        self._uv_coord(mayaShader, usdShader)

        return True

    # Get Temp Stage
    def GetStage(self):
        return self.stage

    # Get Root Scope
    def GetScope(self):
        if self.scope:
            return self.scope
        else:
            return False

    # Save Stage to File
    def Save(self):
        self.stage.Export(self.filename)


def export(file_path=None):
    import maya.cmds as cmds

    shadingGroups = getShadingGroups(cmds.ls(sl=True)[0])
    exporter = RedshiftShadersToUSD(
        shadingGroups=shadingGroups,
        filename=file_path
    )
    # print(tmp.stage.GetRootLayer().ExportToString())
    exporter.Save()
    del exporter
