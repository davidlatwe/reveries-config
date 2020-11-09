from pxr import Usd

from reveries.common.path_resolver import PathResolver


class CheckPath(object):
    def __init__(self, file_path):
        self.file_path = file_path

        self.all_from_pub = True
        self.not_publish = []

        self._check(self.file_path)

    def _check(self, file_path):

        source_stage = Usd.Stage.Open(file_path)
        root_layer = source_stage.GetRootLayer()
        layers = [s.replace('\\', '/')
                  for s in root_layer.GetExternalReferences() if s]
        print('layers: {}\n'.format(layers))

        for _path in layers:
            if _path:
                _path_resolver = PathResolver(file_path=_path)
                if not _path_resolver.is_publish_file():
                    self.not_publish.append(_path)
                    self.all_from_pub = False

        return self.all_from_pub

    @classmethod
    def check(cls, file_path):
        return cls(file_path)
