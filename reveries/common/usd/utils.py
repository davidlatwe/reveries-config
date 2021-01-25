def get_UpAxis(host=""):
    assert host, "Please provide host name."

    from pxr import UsdGeom

    if host.lower() in ["maya", "houdini"]:
        return UsdGeom.Tokens.y
