from plone import api
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.registry.field import PersistentField
from plone.z3cform import layout
from z3c.form import form
from z3c.form.object import registerFactoryAdapter
from zope import schema
from zope.interface import Interface
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary
from zope.i18nmessageid import MessageFactory

#from lmu.policy.base import MESSAGE_FACTORY as _
_ = MessageFactory('lmu.poliy.base')


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


timedeltas_vocabulary = SimpleVocabulary([
    SimpleTerm(token='0', value=u'0', title=_(u'immediat')),
    SimpleTerm(token='1', value=u'1', title=_(u'1 day')),
    SimpleTerm(token='7', value=u'7', title=_(u'1 week')),
    SimpleTerm(token='14', value=u'14', title=_(u'2 weeks')),
    SimpleTerm(token='30', value=u'30', title=_(u'1 month')),
    SimpleTerm(token='90', value=u'90', title=_(u'3 month')),
    SimpleTerm(token='180', value=u'180', title=_(u'6 month')),
])


class ITitleLanguagePair(Interface):
    language = schema.Choice(
        title=_(u"Language"),
        vocabulary="lmu.policy.base.AvailableLanguages",
    )
    text = schema.TextLine(title=_(u"Title"))


class TitleLanguagePair(object):
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
        value_type=PersistentObject(
            ITitleLanguagePair,
            title=u"Title by Language"),
        required=False
    )
    breadcrumb_1_url = schema.TextLine(
        title=_(u"Breadcrumb override level 1 - Link"),
        description=_(u""),
        required=False
    )
    show_breadcrumb_1 = schema.Bool(
        title=_(u"Show Breadcrumb override level 1"),
        default=False,
        description=_(u""),
        required=False
    )

    breadcrumb_2_title = schema.List(
        title=_(u"Breadcrumb override level 2 - Title"),
        description=_(u""),
        value_type=PersistentObject(
            ITitleLanguagePair,
            title=u"Title by Language"),
        required=False
    )
    breadcrumb_2_url = schema.TextLine(
        title=_(u"Breadcrumb override level 2 - Link"),
        description=_(u""),
        required=False
    )
    show_breadcrumb_2 = schema.Bool(
        title=_(u"Show Breadcrumb override level 2"),
        default=False,
        description=_(u""),
        required=False
    )
    domain = schema.List(
        title=_(u"Domain(s)"),
        description=_(u"Domain(s) that the content of this site is valid for"),
        value_type=schema.TextLine(),
        required=False,
    )
    search_paths = schema.List(
        title=_(u"Search Path(s)"),
        description=_(u"Solr Path_parrents that should be searched"),
        value_type=schema.TextLine(),
        required=False,
    )
    cms_system = schema.TextLine(
        title=_(u"CMS System"),
        description=_(u"Name that this CMS system uses to be identified among"
                      " others that may be used in parallel"),
        required=False,
        default=u"Plone",
    )
    del_timedelta = schema.Choice(
        title=_(u"Delete Timedelta"),
        description=_(u"When sould expired Entries be deleted automaticaly"),
        required=False,
        default='90',
        vocabulary=timedeltas_vocabulary,
    )


class LMUControlPanelForm(RegistryEditForm):
    form.extends(RegistryEditForm)
    schema = ILMUSettings

LMUControlPanelView = layout.wrap_form(
    LMUControlPanelForm, ControlPanelFormWrapper)
LMUControlPanelView.label = u"LMU settings"
