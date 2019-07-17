# -*- coding: utf-8 -*-


import string
import random
import xmltodict


__all__ = ('rand_str', 'to_dict', 'to_xml')


def rand_str(length):
    char = string.ascii_letters + string.digits
    return "".join(random.choice(char) for _ in range(length))


def to_dict(content):
    data = xmltodict.parse(content)
    for k in data:
        return dict(data[k])
    return dict()


def to_xml(data):
    return xmltodict.unparse(dict(xml=data))
