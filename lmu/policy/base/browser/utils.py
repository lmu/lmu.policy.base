import Globals

from lmu.policy.base.controlpanel import ILMUSettings
from logging import getLogger
from plone.app.textfield.interfaces import ITransformer
from plone.protect.interfaces import IDisableCSRFProtection
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.browser.ploneview import Plone
from Products.Five.browser import BrowserView
from zope.component import getUtility
from zope.interface import alsoProvides

log = getLogger(__name__)


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
    log.debug("DB is readOnly: %s", isReadOnly)
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
            # RESPONSE.setHeader('Content-Type', 'application/xml;charset=utf-8')
            RESPONSE.setHeader('X-Theme-Disabled', 'True')
            RESPONSE.setHeader('X-Theme-Enabled', 'False')

            REQUEST.environ['HTTP_X_THEME_ENABLED'] = False
            REQUEST.environ['HTTP_X_THEME_DISABLED'] = True

            alsoProvides(REQUEST, IDisableCSRFProtection)
            # import ipdb; ipdb.set_trace()

        return self.template()


class Repair(BrowserView):

    def __call__(self):
        registry = getUtility(IRegistry)
        registry.registerInterface(ILMUSettings)
        #lmu_settings = registry.forInterface(ILMUSettings)
        alsoProvides(self.request, IDisableCSRFProtection)
        return "Update erfolgreich"
