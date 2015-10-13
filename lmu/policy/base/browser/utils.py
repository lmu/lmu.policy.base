
from plone.app.textfield.interfaces import ITransformer

from Products.CMFPlone.browser.ploneview import Plone


def strip_text(item, length=500):
    transformer = ITransformer(item)
    transformedValue = transformer(item.text, 'text/plain')
    striped_length = len(transformedValue)
    if striped_length > length:
        striped_length = transformedValue.rfind(' ', 0, length)
        transformedValue = transformedValue[:striped_length] + '...'
    return transformedValue


def _strip_text(item, length=500, ellipsis='...'):
    transformer = ITransformer(item)
    transformedValue = transformer(item.text, 'text/plain')
    return Plone.cropText(transformedValue, length=length, ellipsis=ellipsis)


def str2bool(v):
    return v is not None and v.lower() in ['true', '1']
