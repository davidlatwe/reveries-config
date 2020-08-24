from pxr import Usd, Sdf
from reveries.common.path_resolver import PathResolver


def update(usd_file=None, output_path=None):
    source_stage = Usd.Stage.Open(usd_file)
    root_layer = source_stage.GetRootLayer()
    layers = [s.replace('\\', '/') for s in root_layer.GetExternalReferences() if s]

    for prim in source_stage.Traverse():

        prim_stacks = prim.GetPrimStack()

        for _prim in prim_stacks:
            _prim_path = str(prim.GetPrimPath())
            if root_layer.GetPrimAtPath(_prim_path):
                try:
                    _layer = _prim.layer
                except Exception as e:
                    continue

                current_path = _layer.realPath.replace('\\', '/')

                if current_path in layers:
                    _path_resolver = PathResolver(file_path=current_path)
                    latest_file_path = _path_resolver.get_latest_file()
                    if latest_file_path != current_path:
                        if isinstance(latest_file_path, list):
                            latest_file_path = [s for s in latest_file_path if s.endswith(".usda")][0]

                        update_prim = source_stage.GetPrimAtPath(_prim_path)
                        update_prim.GetReferences().SetReferences(
                            [Sdf.Reference(latest_file_path)])

    # print(source_stage.GetRootLayer().ExportToString())
    source_stage.GetRootLayer().Export(output_path)


def test():
    tmp_usd = r'\...\houdini\scenes\test\lay_prim_v03.usda'
    output_path = r'\...\test\lay_prim_v03_tmp.usda'

    update(usd_file=tmp_usd, output_path=output_path)
