# -*- coding: utf-8 -*-


import enum
import asyncio

from typing import Optional

from weixin.client import Client, runner
from weixin.errors import WeixinError
from weixin.dotdict import dotdict


__all__ = ('WeixinPay')


class WeixinPayStatus(enum.Enum):
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"


class WeixinPay(Client):
    """
    微信支付


    :param app_id: 应用id
    :param mch_id: 商户id
    :param mch_key: 商户key, 主动设置的
    :param notify_url: 回调地址
    :param refund_notify_url: 退款回调地址, 可选
    :param key: 证书key, 可选
    :param cert: 证书cert, 可选
    """

    PAY_HOST = "https://api.mch.weixin.qq.com"

    def __init__(
        self,
        app_id: str,
        mch_id: str,
        mch_key: str,
        notify_url: str,
        *
        mode: str = 'async',
        loop: Optional[asyncio.AbstractEventLoop] = None,
        refund_notify_url: Optional[str] = None,
        key: Optional[str] = None
        cert: Optional[str] = None
        **kwargs,
    ):
        self._app_id = app_id
        self._mch_id = mch_id
        self._mch_key = mch_key
        self._notify_url = notify_url
        self._refund_notify_url = refund_notify_url or notify_url
        self._key = key
        self._cert = cert
        super().__init__(mode=mode, loop=loop, **kwargs)
