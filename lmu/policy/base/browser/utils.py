import Globals

from lmu.policy.base.controlpanel import ILMUSettings
from plone.app.textfield.interfaces import ITransformer
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.browser.ploneview import Plone
from Products.Five.browser import BrowserView
from zope.component import getUtility

from logging import getLogger

logging = getLogger(__name__)


def strip_text(item, length=500, ellipsis='...', item_type='richtext'):
    if item_type == 'plain':
        striped_length = len(item)
        transformedValue = item

    else:  # item_type is 'richtext'
        transformer = ITransformer(item)
        transformedValue = transformer(item.text, 'text/plain')
        striped_length = len(transformedValue)

    if striped_length > length:
        striped_length = transformedValue.rfind(' ', 0, length)
        transformedValue = transformedValue[:striped_length] + ellipsis
    return transformedValue


def _strip_text(item, length=500, ellipsis='...'):
    transformer = ITransformer(item)
    transformedValue = transformer(item.text, 'text/plain')
    return Plone.cropText(transformedValue, length=length, ellipsis=ellipsis)


def str2bool(v):
    return v is not None and v.lower() in ['true', '1']


def isDBReadOnly():
    conn = Globals.DB.open()
    isReadOnly = conn.isReadOnly()
    conn.close()
    logging.debug("DB is readOnly: %s", isReadOnly)
    return isReadOnly


class _IncludeMixin(object):

    def update(self):
        """
        """
        # Hide the editable-object border
        request = self.request
        request.set('disable_border', True)

    def __call__(self):
        omit = self.request.get('full')
        self.omit = not str2bool(omit)
        if self.omit:
            REQUEST = self.context.REQUEST
            RESPONSE = REQUEST.RESPONSE
            RESPONSE.setHeader('Content-Type', 'application/xml;charset=utf-8')
        return self.template()


class Repair(BrowserView):

    def __call__(self):
        registry = getUtility(IRegistry)
        registry.registerInterface(ILMUSettings)
        return "Update erfolgreich"
