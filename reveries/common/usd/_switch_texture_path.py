import os
from pxr import Usd, Sdf


class SwitchPath(object):
    def __init__(self, file_path=None, pub_dir=None, output_path=None):
        self.file_path = file_path
        self.pub_dir = pub_dir

        if not output_path:
            self.output_path = os.path.join(
                os.path.dirname(file_path),
                "output.usda"
            )

        self._switch()

    def _switch(self):
        source_stage = Usd.Stage.Open(self.file_path)
        root_layer = source_stage.GetRootLayer()
        layers = [s.replace('\\', '/')
                  for s in root_layer.GetExternalReferences() if s]
        print("layers: ", layers)

    @classmethod
    def switch(cls, file_path=None, pub_dir=None, output_path=None):
        return cls(
            file_path=file_path,
            pub_dir=pub_dir,
            output_path=output_path
        )


def test():
    source_file_path = r'Q:\199909_AvalonPlay\Avalon\PropBox\BoxB\work\lookdev\maya\scenes\usd\look.usda'
    pub_dir = r'Q:/199909_AvalonPlay/Avalon/PropBox/BoxB/publish/lookTexB/v016/USD'

    SwitchPath(file_path=source_file_path, pub_dir=pub_dir)
