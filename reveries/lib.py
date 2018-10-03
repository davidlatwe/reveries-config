
def iter_uri(path, sep):
    """Iter parents of node from its long name.

    Args:
        path (str): URI string
        sep (str): URI path sep

    Yields:
        str: All parent path

    Example:
        >>> path = "foo/bar/dir/file"
        >>> for p in iter_uri(path, "/"):
        ...     print(p)
        ...
        foo/bar/dir
        foo/bar
        foo

    """
    while True:
        split = path.rsplit(sep, 1)
        if len(split) == 1:
            return

        path = split[0]
        yield path
