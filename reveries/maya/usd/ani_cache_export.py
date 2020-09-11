# -*- coding: utf-8 -*-
import os

from pxr import Usd, Sdf, UsdGeom


class AnimationExtractor(object):
    """
    Export point cache only.
    """
    def __init__(self, source_path=None, shot_time=None):
        self.source_path = source_path
        self.shot_time = shot_time

        self.source_stage = None
        self.override_stage = None

        self.process()

    def _open_stage(self):
        assert os.path.exists(self.source_path), \
            'file not exist: {}'.format(self.source_path)
        self.source_stage = Usd.Stage.Open(self.source_path)

    def _create_stage(self):
        self.override_stage = Usd.Stage.CreateInMemory()
        if self.shot_time:
            self.override_stage.SetStartTimeCode(self.shot_time[0])
            self.override_stage.SetEndTimeCode(self.shot_time[1])

    def process(self):
        self._open_stage()
        self._create_stage()
        for prim in self.source_stage.Traverse():
            # print prim, prim.GetTypeName(), prim.IsActive()

            if prim.GetTypeName() == 'Mesh' and prim.IsActive():
                # print prim
                mesh = UsdGeom.Mesh(prim)
                points = mesh.GetPointsAttr()

                over_mesh_prim = self.override_stage.OverridePrim(prim.GetPath())
                over_mesh = UsdGeom.Mesh(over_mesh_prim)
                over_points = over_mesh.CreatePointsAttr()

                for time_sample in points.GetTimeSamples():
                    over_points.Set(points.Get(time_sample), time=Usd.TimeCode(time_sample))

            if prim.GetTypeName() == 'Xform' and prim.IsActive():
                xform = UsdGeom.Xform(prim)
                if xform.GetTimeSamples():
                    xform_order = xform.GetXformOpOrderAttr()
                    over_xform_prim = self.override_stage.OverridePrim(prim.GetPath())
                    over_xform = UsdGeom.Xform(over_xform_prim)

                    xform_op_names = []
                    for op in xform.GetOrderedXformOps():
                        if op.GetTimeSamples():
                            op_type = op.GetOpType()
                            op_name = op.GetName()

                            if op_type not in xform_op_names:
                                over_op = over_xform.AddXformOp(op_type)
                                for time_sample in op.GetTimeSamples():
                                    over_op.Set(op.Get(time_sample), time=Usd.TimeCode(time_sample))
                                xform_op_names.append(op_type)
                            else:
                                print 'Note: skip {}, type is {}, in {}.'.format(
                                    op_name,
                                    op_type,
                                    over_xform_prim.GetPath()
                                )

                    over_xform_order = over_xform.GetXformOpOrderAttr()
                    over_xform_order.Clear()
                    over_xform_order.Set(xform_order.Get())

    def get_stage(self):
        return self.override_stage

    def export(self, save_path):
        self.override_stage.Export(save_path)
        # self.override_stage.GetRootLayer().Export(save_path)

    def clean(self):
        os.remove(self.source_path)


# def update_prim_path(stage, layer, source_path, destination_path):
#     temp_layer = Sdf.Layer.CreateAnonymous()
#     Sdf.CopySpec(layer, source_path, temp_layer, '/temp')
#     stage.RemovePrim(source_path)
#     Sdf.CopySpec(temp_layer, '/temp', layer, destination_path)
#     temp_layer.Clear()
#     try:
#         stage.RemovePrim('/rigDefault')
#     except Exception as e:
#         print(e)


def _update_prim_path(stage, layer, mod_root_path, destination_path, asset_name=None, has_proxy=False):
    from pxr import Sdf, UsdGeom

    temp_layer = Sdf.Layer.CreateAnonymous()
    Sdf.CopySpec(layer, mod_root_path, temp_layer, '/temp')
    stage.RemovePrim(mod_root_path)
    UsdGeom.Xform.Define(stage, destination_path)
    Sdf.CopySpec(temp_layer, '/temp', layer, destination_path)
    temp_layer.Clear()

    # For proxy
    if has_proxy:
        source_path = '/ROOT/modelDefault/MOD/{}_proxy_geo_grp'.format(asset_name)
        tag_path = '/ROOT/modelDefaultProxy/MOD/{}_proxy_geo_grp'.format(asset_name)

        temp_layer = Sdf.Layer.CreateAnonymous()
        Sdf.CopySpec(layer, source_path, temp_layer, '/temp')
        stage.RemovePrim(source_path)
        UsdGeom.Xform.Define(stage, tag_path)
        Sdf.CopySpec(temp_layer, '/temp', layer, tag_path)
        temp_layer.Clear()

    try:
        stage.RemovePrim('/rigDefault')
    except Exception as e:
        print(e)


def export(source_file_path, output_path, mod_root_path='', asset_name='', has_proxy=False):
    """
    Export animation point cache usd file.

    :param source_file_path: (str) Source animation usd file path.
    :param output_path     : (str) Output path.
    :param mod_root_path   : (str) The hierarchy of 'MOD' group in usd source file.
        Most time is "/rigDefault/ROOT/Group/Geometry/modelDefault/ROOT"
    :param asset_name      : (str) Asset name
    :param has_proxy       : (bool) Has proxyPrim or not.
    :return:
    """

    authored_tmp_path = os.path.join(os.path.dirname(output_path), 'authored_data_tmp.usda')
    pe = AnimationExtractor(source_file_path)
    pe.export(authored_tmp_path)

    # Fix hierarchy
    stage = Usd.Stage.Open(authored_tmp_path)
    root_layer = stage.GetRootLayer()

    # Check 'MOD' exists
    destination_path = '/ROOT/modelDefault/MOD'
    for prim in stage.TraverseAll():
        if '/ROOT/MOD/' in str(prim.GetPath()):
            destination_path = '/ROOT/modelDefault'
            break

    # Export usd
    _update_prim_path(stage, root_layer, mod_root_path, destination_path,
                      asset_name=asset_name,
                      has_proxy=has_proxy)
    root_layer.Export(output_path)

    print('Done.')
