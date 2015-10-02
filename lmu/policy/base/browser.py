# -*- coding: utf-8 -*-

#import StringIO

from datetime import datetime
from datetime import timedelta
from collective.quickupload.portlet.quickuploadportlet import Assignment
from collective.quickupload.portlet.quickuploadportlet import Renderer
from collective.solr.interfaces import ISolrConnectionConfig
from collective.solr.parser import SolrResponse
#from OFS import Image as OFSImage
#from PIL import Image as PILImage
#from Products.PlonePAS.utils import scale_image
from Products.CMFCore import permissions
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.browser.navtree import getNavigationRoot
from Products.CMFPlone.browser.ploneview import Plone
from Products.CMFPlone.PloneBatch import Batch
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PythonScripts.standard import url_quote_plus
from Products.ZCTextIndex.ParseTree import ParseError
from lmu.contenttypes.blog import MESSAGE_FACTORY as _  # XXX move translations
from lmu.policy.base.controlpanel import ILMUSettings
from lmu.policy.base.interfaces import ILMUCommentFormLayer
from plone import api
from plone.app.discussion.browser.comments import CommentsViewlet
from plone.app.contentlisting.interfaces import IContentListing
from plone.app.layout.viewlets import common
from plone.app.search.browser import Search as BaseSearch
from plone.app.search.browser import quote_chars
from plone.app.textfield.interfaces import ITransformer
from plone.app.z3cform.templates import RenderWidget
from plone.dexterity.browser import add
from plone.dexterity.browser import edit
from plone.registry.interfaces import IRegistry
from z3c.form.interfaces import HIDDEN_MODE
from z3c.form.interfaces import DISPLAY_MODE
from z3c.form.interfaces import INPUT_MODE
from zope.interface import alsoProvides
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryUtility
import json
import logging


def str2bool(v):
    return v is not None and v.lower() in ['true', '1']

log = logging.getLogger(__name__)


class Search(BaseSearch):

    def results(self, query=None, batch=True, b_size=10, b_start=0):
        """ Get properly wrapped search results from the catalog.
        Everything in Plone that performs searches should go through this view.
        'query' should be a dictionary of catalog parameters.
        """
        if query is None:
            query = {}
        if batch:
            query['b_start'] = b_start = int(b_start)
            query['b_size'] = b_size
        config = queryUtility(ISolrConnectionConfig)
        if config:
            query['facet'] = 'true'
            query['facet.field'] = config.facets

        query = self.filter_query(query)

        if query is None:
            results = []
        else:
            catalog = getToolByName(self.context, 'portal_catalog')
            try:
                results = catalog(**query)
            except ParseError:
                return []
        qtime = timedelta(0)
        if isinstance(results, SolrResponse) and results.responseHeader and 'QTime' in results.responseHeader:
            qtime = timedelta(milliseconds=results.responseHeader.get('QTime'))
        results = IContentListing(results)
        if batch:
            results = Batch(results, b_size, b_start)
        results.qtime = qtime
        return results

    def extra_types(self):
        ptool = getToolByName(self, 'portal_properties')
        siteProperties = getattr(ptool, 'site_properties')
        extraTypes = siteProperties.getProperty('extra_types_searched', [])
        return list(extraTypes)

    def filter_query(self, query):
        query = super(Search, self).filter_query(query)
        if query:
            # Only show Fiona Content in results that are from 'sp'
            if getNavigationRoot(self.context) == '/intranet':
                query['path'] = [getNavigationRoot(self.context), '/prototyp-1/in']
            elif getNavigationRoot(self.context) == '/serviceportal':
                query['path'] = [getNavigationRoot(self.context), '/prototyp-1/sp']
            else:
                query['path'] = [getNavigationRoot(self.context)]
            query['portal_type'] += self.extra_types()
        return query

    def types_list(self):
        types = super(Search, self).types_list()
        return types + self.extra_types()

    def breadcrumbs(self, item):
        try:
            obj = item.getObject()
            view = getMultiAdapter((obj, self.request), name='breadcrumbs_view')
            # cut off the item itself
            breadcrumbs = list(view.breadcrumbs())[:-1]
            if len(breadcrumbs) == 0:
                # don't show breadcrumbs if we only have a single element
                return None
            if len(breadcrumbs) > 3:
                # if we have too long breadcrumbs, emit the middle elements
                empty = {'absolute_url': '', 'Title': unicode('…', 'utf-8')}
                breadcrumbs = [breadcrumbs[0], empty] + breadcrumbs[-2:]
            return breadcrumbs
        except Exception:
            return None


class LivesearchReply(Search):

    template = ViewPageTemplateFile('templates/livesearch_reply2.pt')

    MAX_TITLE = 50
    MAX_DESCRIPTION = 150

    def searchterm_query(self):
        q = self.request.get('q', '')
        for char in ('?', '-', '+', '*'):
            q = q.replace(char, ' ')
        q = quote_chars(q)
        searchterm_query = '?searchterm=%s' % url_quote_plus(q)
        return searchterm_query

    def searchterms(self, quote=True):
        q = self.request.get('q', '')

        # XXX really if it contains + * ? or -
        # it will not be right since the catalog ignores all non-word
        # characters equally like
        # so we don't even attept to make that right.
        # But we strip these and these so that the catalog does
        # not interpret them as metachars
        for char in ('?', '-', '+', '*'):
            q = q.replace(char, ' ')
        r = q.split()
        r = " AND ".join(r)
        r = quote_chars(r) + '*'
        if quote:
            return url_quote_plus(r)
        else:
            return r

    def display_title(self, full_title):
        return self.ellipse(full_title, self.MAX_TITLE)

    def display_description(self, full_description):
        return self.ellipse(full_description, self.MAX_DESCRIPTION)

    def ellipse(self, full_string, max_len):
        if (full_string and
                len(full_string) > max_len):
            display_string = ''.join(
                (full_string[:max_len], '...'))
        else:
            display_string = full_string
        return display_string

    def __call__(self):
        limit = self.request.get('limit', 10)
        path = self.request.get('path', None)

        params = {'SearchableText': self.searchterms(quote=False),
                  'sort_limit': limit + 1}

        if path is not None:
            params['path'] = path

        self.live_results = self.results(query=params, b_size=limit)

        REQUEST = self.context.REQUEST
        RESPONSE = REQUEST.RESPONSE
        RESPONSE.setHeader('Content-Type', 'text/xml;charset=utf-8')

        return self.template()


class UserInfo(BrowserView):

    template = ViewPageTemplateFile('templates/user_info.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        user = api.user.get_current()
        pm = api.portal.get_tool('portal_membership')
        REQUEST = self.context.REQUEST
        RESPONSE = REQUEST.RESPONSE
        RESPONSE.setHeader('Content-Type', 'text/xml;charset=utf-8')

        self.username = user.getProperty('fullname')
        portrait = pm.getPersonalPortrait()
        #image = Image.open(StringIO.StringIO(portrait.data))
        #self.portrait = image.resize((30, 30))
        #import ipdb; ipdb.set_trace()
        #small_portrait, mimetype = scale_image(StringIO.StringIO(portrait.data), (30, 30))
        #self.portrait = OFSImage.Image(id=user.getUserName(), file=small_portrait, title='')
        self.portrait = portrait
        return self.template()


class PathBarViewlet(common.PathBarViewlet):
    """Replace the "Home" breadcrumb with the overrides from the control
       panel."""
    render = ViewPageTemplateFile('templates/path_bar.pt')

    def update(self):
        super(PathBarViewlet, self).update()

        registry = getUtility(IRegistry)
        try:
            self.lmu_settings = registry.forInterface(ILMUSettings)
        except Exception as e:
            log.exception(e)
            return

        portal_state = api.content.get_view(
            name='plone_portal_state',
            context=self.context,
            request=self.request)
        self.current_language = portal_state.locale().getLocaleID()

        self.is_any_override_active = (
            self.lmu_settings.show_breadcrumb_1 or
            self.lmu_settings.show_breadcrumb_2)


class _AbstractLMUBaseContentView(BrowserView):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def get_memberdata(self, item):
        pmt = api.portal.get_tool(name='portal_membership')
        member_id = item.Creator()
        member = pmt.getMemberById(member_id)
        return member

    def strip_text(self, item, length=500):
        transformer = ITransformer(item)
        transformedValue = transformer(item.text, 'text/plain')
        striped_length = len(transformedValue)
        if striped_length > length:
            striped_length = transformedValue.rfind(' ', 0, length)
            transformedValue = transformedValue[:striped_length] + '...'
        return transformedValue

    def _strip_text(self, item, length=500, ellipsis='...'):
        transformer = ITransformer(item)
        transformedValue = transformer(item.text, 'text/plain')
        return Plone.cropText(transformedValue, length=length, ellipsis=ellipsis)

    def images(self):
        #image_brains = api.content.find(context=self.context, depth=1, portal_type='Image')
        #images = [item.getObject() for item in image_brains]
        images = [item for item in self.context.values() if item.portal_type == 'Image']
        if None in images:
            images.remove(None)
        return images

    def files(self):
        files = [item for item in self.context.values() if item.portal_type == 'File']
        if None in files:
            files.remove(None)
        return files

    def getFileSize(self, fileobj):
        size = fileobj.file.getSize()
        if size < 1000:
            size = str(size) + ' Byte'
        elif size > 1024 and size/1024 < 1000:
            size = str(fileobj.file.getSize() / 1024) + ' KB'
        else:
            size = str(fileobj.file.getSize() / 1024 / 1024) + ' MB'
        return size

    def getFileType(self, fileobj):
        ctype = fileobj.file.contentType
        ctype = ctype.split('/')
        return str.upper(ctype[1])

    def _check_permission(self, permission, item):
        pmt = api.portal.get_tool(name='portal_membership')
        return pmt.checkPermission(permission, item)


class _FrontPageIncludeMixin(object):

    def update(self):
        """
        """
        # Hide the editable-object border
        request = self.request
        request.set('disable_border', True)

    def __call__(self):
        omit = self.request.get('full')
        self.omit = not str2bool(omit)
        author = self.request.get('author')
        self.author = bool(author)
        if self.omit:
            REQUEST = self.context.REQUEST
            RESPONSE = REQUEST.RESPONSE
            RESPONSE.setHeader('Content-Type', 'text/xml;charset=utf-8')
        return self.template()


class _EntryViewMixin(object):

    def can_see_history(self):
        return True

    def can_edit(self):
        return api.user.has_permission(permissions.ModifyPortalContent, obj=self.context) and \
            any(role in ['Owner', 'Site Manager', 'Manager'] for role in api.user.get_roles(obj=self.context))

    def can_remove(self):
        """Only show the delete-button if the user has the permission to delete
        items and the workflow_state fulfills a condition.
        """
        state = api.content.get_state(obj=self.context)
        can_delete = api.user.has_permission(
            permissions.DeleteObjects, obj=self.context)
        if can_delete and state not in ['banned']:
            return True

    def can_publish(self):
        return api.user.has_permission(permissions.ReviewPortalContent, obj=self.context) and \
            any(role in ['Owner', 'Site Manager', 'Manager'] for role in api.user.get_roles(obj=self.context)) and \
            api.content.get_state(obj=self.context) in ['private']

    def can_hide(self):
        return api.user.has_permission(permissions.ReviewPortalContent, obj=self.context) and \
            any(role in ['Owner', 'Site Manager', 'Manager'] for role in api.user.get_roles(obj=self.context)) and \
            api.content.get_state(obj=self.context) in ['internally_published']

    def can_reject(self):
        return api.user.has_permission(permissions.ReviewPortalContent, obj=self.context) and \
            any(role in ['Site Manager', 'Manager'] for role in api.user.get_roles(obj=self.context)) and \
            api.content.get_state(obj=self.context) in ['internally_published']

    def can_lock(self):
        return api.user.has_permission(permissions.ReviewPortalContent, obj=self.context) and \
            any(role in ['Site Manager', 'Manager'] for role in api.user.get_roles(obj=self.context)) and \
            api.content.get_state(obj=self.context) in ['internally_published']

    def isOwner(self):
        user = api.user.get_current()
        return 'Owner' in user.getRolesInContext(self.context)

    def isReviewer(self):
        user = api.user.get_current()
        return 'Reviewer' in user.getRolesInContext(self.context)

    def isManager(self):
        return any(role in ['Manager', 'SiteAdmin'] for role in api.user.get_roles(obj=self.context))

    def isPrivate(self):
        return api.content.get_state(obj=self.context) in ['private']

    def isInternallyPublished(self):
        return api.content.get_state(obj=self.context) in ['internally_published']


class RichTextWidgetConfig(object):
    allow_buttons = ('style',
                     'bold',
                     'italic',
                     'numlist',
                     'bullist',
                     'link',
                     'unlink',
                     )
    redefine_parastyles = True
    parastyles = (_('Heading') + '|h2|',
                  _('Subheading') + '|h3|',
                  )


class _AbstractLMUBaseContentEditForm(edit.DefaultEditForm):

    def __call__(self):
        self.updateWidgets()

        text = self.schema.get('text')
        text.widget = RichTextWidgetConfig()

        formHelper(self,
                   fields_to_show=[],
                   fields_to_input=['title', 'description'],
                   fields_to_hide=['IPublication.effective', 'IPublication.expires', ],
                   fields_to_omit=['IPublication.effective', 'IPublication.expires', 'IVersionable.changeNote'])

        buttons = self.buttons

        for button in buttons.values():
            if button.__name__ == 'save':
                button.title = _(u'Preview')

        return super(_AbstractLMUBaseContentEditForm, self).__call__()


class EntryContentView(_AbstractLMUBaseContentView):

    template = ViewPageTemplateFile('templates/entry_content_view.pt')

    def __call__(self):
        omit = self.request.get('full')
        self.omit = not str2bool(omit)
        return self.template()

    def content(self, mode='files'):
        if mode == 'images':
            type_test = lambda typ: typ == 'Image'
        else:
            plone_layout = getMultiAdapter((self.context, self.request),
                                           name='plone_layout')
            type_test = lambda typ: typ != 'Image'
        items = []
        previous = -1
        for current, obj in enumerate(self.context.objectValues()):
            if type_test(obj.portal_type):
                item = {'url': obj.absolute_url(),
                        'id': obj.getId(),
                        'title': obj.Title()}
                if mode == 'files':
                    item['tag'] = plone_layout.getIcon(obj).html_tag()
                    item['type'] = self.getFileType(obj)
                    item['size'] = self.getFileSize(obj)
                elif mode == 'images':
                    scales = api.content.get_view(
                        context=obj,
                        request=self.request,
                        name='images')
                    item['tag'] = scales.tag('image', width=80, height=80,
                                             direction='down')
                if previous > -1:
                    item['delta_up'] = previous - current
                items.append(item)
                previous = current
            else:
                items.append({})
        previous = -1
        for current, obj in enumerate(reversed(self.context.objectValues())):
            if type_test(obj.portal_type):
                if previous > -1:
                    items[-1 - current]['delta_down'] = current - previous
                previous = current
        return [i for i in items if i]

    def render_quickupload(self):
        ass = Assignment(header=_(''))
        renderer = CustomUploadRenderer(
            self.context, self.request, self, None, ass)
        renderer.update()
        return renderer.render()

    def timestamp(self):
        return datetime.now().isoformat()

    def subset_ids(self):
        return json.dumps(self.context.objectIds())

    def mode_label(self):
        return self.mode[0].upper() + self.mode[1:]

    def content_sortinfo(self):
        return self.content(mode=self.mode)


class EntrySortFilesView(EntryContentView):

    template = ViewPageTemplateFile('templates/entry_sort_images_view.pt')
    mode = 'files'

    def __call__(self):
        return self.template()


class EntrySortImagesView(EntryContentView):

    template = ViewPageTemplateFile('templates/entry_sort_images_view.pt')
    mode = 'images'

    def __call__(self):
        return self.template()


class CustomUploadRenderer(Renderer):
    def javascript(self):
        return ''


class ContainedObjectEditForm(edit.DefaultEditForm):

    description = None

    def __call__(self):
        formHelper(self,
                   fields_to_show=['image'],
                   fields_to_input=['title', 'description'],
                   fields_to_hide=['IPublication.effective',
                                   'IPublication.expires',
                                   'ICategorization.subjects',
                                   'ICategorization.language',
                                   'IRelatedItems.relatedItems',
                                   'IOwnership.creators',
                                   'IOwnership.contributors',
                                   'IOwnership.rights',
                                   'IAllowDiscussion.allow_discussion',
                                   'IExcludeFromNavigation.exclude_from_nav',
                                   ],
                   fields_to_omit=['IVersionable.changeNote'])

        buttons = self.buttons
        for button in buttons.values():
            #button.klass = u' button large round'
            if button.__name__ == 'save':
                button.title = _(u'Save')
        return super(ContainedObjectEditForm, self).__call__()

    def label(self):
        return None


class ContainedFileEditForm(ContainedObjectEditForm):

    portal_type = 'File'


class ContainedImageEditForm(ContainedObjectEditForm):

    portal_type = 'Image'


class LMUCommentAddForm(add.DefaultAddForm):

    template = ViewPageTemplateFile('templates/blog_entry_edit.pt')

    def __init__(self, context, request, ti=None):
        alsoProvides(self.request, ILMUCommentFormLayer)
        super(LMUCommentAddForm, self).__init__(context, request, ti=ti)

    def __call__(self):
        self.portal_type = self.context.portal_type
        text = self.schema.get('text')
        text.widget = RichTextWidgetConfig()
        self.updateWidgets()
        return super(LMUCommentAddForm, self).__call__()


class LMURenderWidget(RenderWidget):
    index = ViewPageTemplateFile('templates/widget.pt')


class LMUCommentsViewlet(CommentsViewlet):

    def update(self):
        alsoProvides(self.request, ILMUCommentFormLayer)
        super(LMUCommentsViewlet, self).update()

    def can_reply(self):
        is_blog_entry = (self.context.portal_type == 'Blog Entry')
        is_pinnwand_entry = (self.context.portal_type == 'Pinnwand Entry')
        is_private = (api.content.get_state(self.context) == 'private')
        if (is_blog_entry or is_pinnwand_entry) and is_private:
            return False
        return super(LMUCommentsViewlet, self).can_reply()


def formHelper(form, fields_to_show=[], fields_to_input=[], fields_to_hide=[], fields_to_omit=[]):

    form.updateWidgets()

    form.updateFields()
    fields = form.fields
    groups = form.groups

    for field in fields.values():
        if field.__name__ in fields_to_omit:
            field.omitted = True
        if field.__name__ in fields_to_hide:
            field.omitted = False
            field.mode = HIDDEN_MODE
        if field.__name__ in fields_to_show:
            field.omitted = False
            field.mode = DISPLAY_MODE
        if field.__name__ in fields_to_input:
            field.omitted = False
            field.mode = INPUT_MODE

    for group in groups:
        for field in group.fields.values():
            if field.__name__ in fields_to_omit:
                field.omitted = True
            if field.__name__ in fields_to_hide:
                field.omitted = False
                field.mode = HIDDEN_MODE
            if field.__name__ in fields_to_show:
                field.omitted = False
                field.mode = DISPLAY_MODE
            if field.__name__ in fields_to_input:
                field.omitted = False
                field.mode = INPUT_MODE
