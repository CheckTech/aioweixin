# -*- coding: utf-8 -*-


import ssl
import enum
import asyncio

from typing import Optional, Union

from aioweixin.client import Client, runner
from aioweixin.errors import WeixinError
from aioweixin.util import to_xml, to_dict, rand_str


__all__ = ("WeixinPay", "Status", "TradeType")


class Status(enum.Enum):
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"


class TradeType(enum.Enum):
    APP = "APP"
    JSAPI = "JSAPI"
    NATIVE = "NATIVE"


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

    API_HOST = "https://api.mch.weixin.qq.com"

    def __init__(
        self,
        app_id: str,
        mch_id: str,
        mch_key: str,
        notify_url: str,
        *,
        mode: str = "async",
        loop: Optional[asyncio.AbstractEventLoop] = None,
        refund_notify_url: Optional[str] = None,
        key: Optional[str] = None,
        cert: Optional[str] = None,
        **kwargs,
    ):
        self._app_id = app_id
        self._mch_id = mch_id
        self._mch_key = mch_key
        self._notify_url = notify_url
        self._refund_notify_url = refund_notify_url or notify_url
        self._key = key
        self._cert = cert
        self._ssl = None
        super().__init__(mode=mode, loop=loop, **kwargs)

    @property
    def ssl(self):
        if self._ssl:
            return self._ssl
        if not self._cert or not self._key:
            return None
        self._ssl = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self._ssl.load_cert_chain(self._cert, self._key)
        return self._ssl

    @ssl.setter
    def ssl(self, key, cert):
        self._key = key
        self._cert = cert
        self._ssl = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self._ssl.load_cert_chain(self._cert, self._key)

    @property
    def nonce_str(self):
        return rand_str(32)

    async def do(
        self,
        url: str,
        data: dict,
    ) -> Union[str, dict]:
        """
        构建请求并且解析响应

        - 填充默认参数 `nonce_str`
        - 自动签名, 并且填充 `sign` 参数
        - 解析响应内容 `xml` 为 `dict`
        - 判断响应是否出错，出错抛出后异常 :class:`aioweixin.errors.WeixinError`

        :param url: 请求地址
        :param data: 请求数据
        """
        data.setdefault("nonce_str", self.nonce_str)
        data.setdefault("sign", self.sign(data))
        async with self.session.post(url, data=data, ssl=self.ssl) as resp:
            content = await resp.text()
            content_type = resp.headers.get("Content-Type", "")
            if xml not in content_type:
                return content
            data = to_dict(content)
            if data["return_code"] == Status.FAIL:
                raise WeixinError(data["return_code"], data["return_msg"])
            if data.get("result_code", "") == Status.FAIL:
                raise WeixinError(data["result_code"], data["err_code_des"])
            return data

    @classmethod
    def reply(cls, msg, ok=True):
        """
        回调函数回复微信支付的内容

        :param msg: 回复消息
        :param ok: 成功或者失败
        """
        code = Status.SUCCESS if ok else Status.FAIL
        return to_dict(dict(return_code=code, return_msg=msg))

    @runner
    async def sanbox(self):
        """
        开启沙箱模式
        """
        self.API_HOST += "/sandboxnew"
        url = self.API_HOST + "/pay/getsignkey"
        data = {"mch_id": self._mch_id}
        resp = await self.do(url, data)
        self._mch_key = resp["sandbox_signkey"]

    @runner
    async def unified_order(
        self,
        out_trade_no: str,
        trade_type: str,
        total_fee: int,
        body: str,
        spbill_create_ip: str,
        *,
        openid: Optional[str] = None,
        product_id: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """
        统一下单

        除被扫支付场景以外，商户系统先调用该接口在微信支付服务后台生成预支付交易单，
        返回正确的预支付交易会话标识后再按扫码、JSAPI、APP等不同场景生成交易串调起支付。

        https://pay.weixin.qq.com/wiki/doc/api/jsapi.php?chapter=9_1

        :param out_trade_no: 订单号
        :param trade_type: 订单类型
        :param total_fee: 订单费用，分
        :param body: 订单内容
        :param spbill_create_ip: 创建订单的ip
        :param openid: 用户唯一id,当 `trade_type` == `JSAPI` 时候必传
        :param product_id: 此参数为二维码中包含的商品ID,当 `trade_type` == `NATIVE` 时候必传
        """
        kwargs.setdefault("out_trade_no", out_trade_no)
        kwargs.setdefault("trade_type", trade_type)
        kwargs.setdefault("total_fee", total_fee)
        kwargs.setdefault("body", body)
        kwargs.setdefault("spbill_create_ip", spbill_create_ip)
        if trade_type == TradeType.JSAPI:
            if not openid:
                raise WeixinError(Status.FAIL, "openid required")
            kwargs.setdefault("openid", openid)
        elif trade_type == TradeType.NATIVE:
            if not product_id:
                raise WeixinError(Status.FAIL, "product_id required")
            kwargs.setdefault("product_id", product_id)

        # 填写默认参数
        url = self.API_HOST + "/pay/unifiedorder"
        kwargs.setdefault("appid", self._app_id)
        kwargs.setdefault("mch_id", self._mch_id)
        kwargs.setdefault("notify_url", self._notify_url)
        return await self.do(url, kwargs)

    @runner
    async def jsapi(
        self,
        out_trade_no: str,
        total_fee: int,
        body: str,
        spbill_create_ip: str,
        openid: str,
        **kwargs,
    ) -> dict:
        """
        微信公众号等统一下单

        :meth:`jsapi` 是对方法 :meth:`unified_order` 的包装

        https://pay.weixin.qq.com/wiki/doc/api/jsapi.php?chapter=7_7&index=6

        :param out_trade_no: 订单号
        :param trade_type: 订单类型
        :param total_fee: 订单费用，分
        :param body: 订单内容
        :param spbill_create_ip: 创建订单的ip
        :param openid: 用户唯一id
        """

        resp = await self.unified_order(
            out_trade_no,
            TradeType.JSAPI,
            total_fee,
            body,
            spbill_create_ip,
            openid=openid,
            **kwargs,
        )
        package = "prepay_id={0}".format(resp["prepay_id"])
        nonce_str = self.nonce_str
        timestamp = str(int(time.time()))
        raw = dict(appId=self.app_id, timeStamp=timestamp, nonceStr=nonce_str, package=package, signType="MD5")
        raw['sign'] = self.sign(raw)
        return raw

    @runner
    async def order_query(
        self,
        *,
        out_trade_no: Optional[str] = None,
        transaction_id: Optional[str] = None,
    ) -> dict:
        """
        查询订单

        该接口提供所有微信支付订单的查询，商户可以通过查询订单接口主动查询订单状态，完成下一步的业务逻辑。

        https://pay.weixin.qq.com/wiki/doc/api/jsapi.php?chapter=9_2

        需要调用查询接口的情况:

            - 当商户后台、网络、服务器等出现异常，商户系统最终未接收到支付通知；
            - 调用支付接口后，返回系统错误或未知交易状态情况；
            - 调用刷卡支付API，返回USERPAYING的状态；
            - 调用关单或撤销接口API之前，需确认支付状态；

        :param out_trade_no: 商户订单号
        :param transaction_id: 微信订单号,参数需要二选一
        """
        if not out_trade_no and not transaction_id:
            raise WeixinError(Status.FAIL, "out_trade_no or transaction_id required")

        out_trade_no and kwargs.setdefault("out_trade_no", out_trade_no)
        transaction_id and kwargs.setdefault("transaction_id", transaction_id)

        url = self.API_HOST + "/pay/orderquery"
        kwargs.setdefault("appid", self._app_id)
        kwargs.setdefault("mch_id", self._mch_id)
        return await self.do(url, kwargs)

    @runner
    async def close_order(
        self,
        out_trade_no: str,
        **kwargs,
    ) -> dict:
        """
        关闭订单

        :param out_trade_no: 商户订单号
        """
        kwargs.setdefault("out_trade_no", out_trade_no)

        url = self.API_HOST + "/pay/closeorder"
        kwargs.setdefault("appid", self._app_id)
        kwargs.setdefault("mch_id", self._mch_id)
        return await self.do(url, kwargs)


    @runner
    async def refund(
        self,
        out_refund_no: str,
        total_fee: int,
        refund_fee: int,
        *,
        out_trade_no: Optional[str] = None,
        transaction_id: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """
        申请退款

        当交易发生之后一段时间内，由于买家或者卖家的原因需要退款时，卖家可以通过退款接口将支付款退还给买家，
        微信支付将在收到退款请求并且验证成功之后，按照退款规则将支付款按原路退到买家帐号上。

        https://pay.weixin.qq.com/wiki/doc/api/micropay.php?chapter=9_4

        注意:

            - 交易时间超过一年的订单无法提交退款
            - 微信支付退款支持单笔交易分多次退款，多次退款需要提交原支付订单的商户订单号和设置不同的退款单号。申请退款总金额不能超过订单金额。 ``一笔退款失败后重新提交，请不要更换退款单号，请使用原商户退款单号``
            - 请求频率限制：150qps，即每秒钟正常的申请退款请求次数不超过150次, 错误或无效请求频率限制：6qps，即每秒钟异常或错误的退款申请请求不超过6次
            - 每个支付订单的部分退款次数不能超过50次

        :param out_refund_no: 商户系统内部的退款单号
        :param total_fee: 订单金额
        :param refund_fee: 退款金额
        :param out_trade_no: 商户订单号
        :param transaction_id: 微信订单号,参数需要二选一
        :param notify_url: 退款成功回调地址, 可选, 如果 :attr:`~WeixinPay.refund_notify_url` 存在，则为默认值
        """

        kwargs.setdefault("out_refund_no", out_refund_no)
        kwargs.setdefault("total_fee", total_fee)
        kwargs.setdefault("refund_fee", refund_fee)
        out_trade_no and kwargs.setdefault("out_trade_no", out_trade_no)
        transaction_id and kwargs.setdefault("transaction_id", transaction_id)

        url = self.API_HOST + "/pay/refund"
        kwargs.setdefault("notify_url", self._refund_notify_url)
        kwargs.setdefault("appid", self._app_id)
        kwargs.setdefault("mch_id", self._mch_id)
        return await self.do(url, kwargs)

    @runner
    async def refund_query(
        self,
        *,
        refund_id: Optional[str] = None,
        out_refund_no: Optional[str] = None,
        out_trade_no: Optional[str] = None,
        transaction_id: Optional[str] = None,
    ) -> dict:
        """
        退款查询

        提交退款申请后，通过调用该接口查询退款状态。退款有一定延时，
        用零钱支付的退款20分钟内到账，银行卡支付的退款3个工作日后重新查询退款状态。

        https://pay.weixin.qq.com/wiki/doc/api/micropay.php?chapter=9_5

        :param refund_id: 退款id
        :param out_refund_no: 商户退款号
        :param out_trade_no: 商户订单号
        :param transaction_id: 微信订单号,参数需要四选一
        """
        out_trade_no and kwargs.setdefault("out_trade_no", out_trade_no)
        transaction_id and kwargs.setdefault("transaction_id", transaction_id)
        refund_id and kwargs.setdefault("refund_id", refund_id)
        out_refund_no and kwargs.setdefault("out_refund_no", out_refund_no)

        url = self.API_HOST + "/pay/refundquery"
        kwargs.setdefault("appid", self._app_id)
        kwargs.setdefault("mch_id", self._mch_id)
        return await self.do(url, kwargs)
