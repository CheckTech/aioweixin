# -*- coding: utf-8 -*-


__all__ = ('WeixinError', )


class WeixinError(Exception):
    """
    微信错误信息

    ::
        raise WeixinError("fail", "invalid args")
    """

    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code
        self.message = msg

    def __str__(self):
        return self.message
