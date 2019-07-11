
import os
import math


AVALON_ID = "AvalonID"

DEFAULT_MATRIX = [1.0, 0.0, 0.0, 0.0,
                  0.0, 1.0, 0.0, 0.0,
                  0.0, 0.0, 1.0, 0.0,
                  0.0, 0.0, 0.0, 1.0]


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


def floor_dec(x, places):
    """Return the floor at given decimal places of x

    Return the largest float that floor at given decimal places which
    less than or equal to x.

    Example:
        >>> floor_dec(0.11029, 4)
        0.1102

    """
    scale = 10**places
    return math.floor(x * scale) / float(scale)


def soft_mtime(path):
    """Return file modification time that floor at 4 decimal places

    File modification time thet retrieved by Python may loose some
    accuracy, so we chop it down to 4 decimal places and will suffice
    for our use case.

    """
    mtime = os.path.getmtime(path)
    return floor_dec(mtime, 4)


def file_cmp(A, B):
    """Comparing two file by size and modification time

    (NOTE) The file modification time (seconds) only take down to 4
           decimal places. See function `soft_mtime`.

    """

    def cmp_size(A, B):
        return os.path.getsize(A) == os.path.getsize(B)

    def cmp_mtime(A, B):
        return soft_mtime(A) == soft_mtime(B)

    same_size = cmp_size(A, B)
    same_time = cmp_mtime(A, B)

    return same_size and same_time


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
