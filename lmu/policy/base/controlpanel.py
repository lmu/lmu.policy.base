from lmu.policy.base import LMUMessageFactory as _
from lmu.policy.base.interfaces import ILMUSettings
from plone import api
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.registry.field import PersistentField
from plone.z3cform import layout
from z3c.form import form
from z3c.form.object import registerFactoryAdapter
from zope import schema
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


class AvailableLanguagesVocabulary(object):
    """Vocabulary factory returning available languages for the portal.
    """
    implements(IVocabularyFactory)

    def __call__(self, context):
        # need to get the context of the adapter
        ltool = api.portal.get_tool(name='portal_languages')
        available = ltool.getAvailableLanguages()
        supported = ltool.getSupportedLanguages()

        items = []
        for lang in supported:
            desc = u"%s (%s)" % (
                unicode(available[lang]['native'].encode('utf-8'), 'utf-8'),
                lang
            )
            items.append(SimpleTerm(lang, lang, desc))

        return SimpleVocabulary(items)

AvailableLanguagesVocabularyFactory = AvailableLanguagesVocabulary()


class ITitleLanguagePair(Interface):
    language = schema.Choice(
        title=_(u"Language"),
        vocabulary="lmu.policy.base.AvailableLanguages",
    )
    text = schema.TextLine(title=_(u"Title"))


class TitleLanguagePair:
    implements(ITitleLanguagePair)

    def __init__(self, language='', text=''):
        self.language = language
        self.text = text

registerFactoryAdapter(ITitleLanguagePair, TitleLanguagePair)


class PersistentObject(PersistentField, schema.Object):
    pass


class ILMUSettings(Interface):
    """Custom settings"""

    breadcrumb_1_title = schema.List(
        title=_(u"Breadcrumb override level 1 - Title"),
        description=_(u""),
        default=[
            TitleLanguagePair('de', u'LMU'),
            TitleLanguagePair('en', u'LMU'),
        ],
        value_type=PersistentObject(
            ITitleLanguagePair,
            title=u"Title by Language"),
        required=False
    )
    breadcrumb_1_url = schema.TextLine(
        title=_(u"Breadcrumb override level 1 - Link"),
        description=_(u""),
        default=u"http://www.lmu-muenchen.de",
        required=False
    )
    show_breadcrumb_1 = schema.Bool(
        title=_(u"Show Breadcrumb override level 1"),
        default=True,
        description=_(u""),
        required=False
    )

    breadcrumb_2_title = schema.List(
        title=_(u"Breadcrumb override level 2 - Title"),
        description=_(u""),
        default=[
            TitleLanguagePair('de', u'LMU'),
            TitleLanguagePair('en', u'LMU'),
        ],
        value_type=PersistentObject(
            ITitleLanguagePair,
            title=u"Title by Language"),
        required=False
    )
    breadcrumb_2_url = schema.TextLine(
        title=_(u"Breadcrumb override level 2 - Link"),
        description=_(u""),
        default=u"http://www.lmu-muenchen.de",
        required=False
    )
    show_breadcrumb_2 = schema.Bool(
        title=_(u"Show Breadcrumb override level 2"),
        default=True,
        description=_(u""),
        required=False
    )


class LMUControlPanelForm(RegistryEditForm):
    form.extends(RegistryEditForm)
    schema = ILMUSettings

LMUControlPanelView = layout.wrap_form(
    LMUControlPanelForm, ControlPanelFormWrapper)
LMUControlPanelView.label = u"LMU settings"
