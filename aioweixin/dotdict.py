# -*- coding: utf-8 -*-


__all__ = ('dotdict', )


class dotdict(dict):
    """
    可以使dict通过点来访问其中的元素

    ::

        d = dotdict(a=1, b=2, c=3)
        asset d.a == 1
        d.a = 2
        asset d.a = d.b
        del d.b
        asset d.b is None
        delattr(d.c)
        asset d.c is None
    """
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
