
def matrix_equals(a, b, tolerance=1e-10):
    """
    Compares two matrices with an imperfection tolerance

    Args:
        a (list, tuple): the matrix to check
        b (list, tuple): the matrix to check against
        tolerance (float): the precision of the differences

    Returns:
        bool : True or False

    """
    if not all(abs(x - y) < tolerance for x, y in zip(a, b)):
        return False
    return True


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
