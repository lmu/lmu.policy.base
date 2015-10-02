# -*- coding: utf-8 -*-

#import StringIO

from datetime import timedelta
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
from lmu.policy.base.controlpanel import ILMUSettings
from plone import api
from plone.app.contentlisting.interfaces import IContentListing
from plone.app.layout.viewlets import common
from plone.app.search.browser import Search as BaseSearch
from plone.app.search.browser import quote_chars
from plone.app.textfield.interfaces import ITransformer
from plone.registry.interfaces import IRegistry
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryUtility
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
        #import ipdb; ipdb.set_trace()
        images = [item for item in self.context.values() if item.portal_type == 'Image']
        if None in images:
            images.remove(None)
        return images

    def files(self):
        files = [item for item in self.context.values() if item.portal_type == 'File']
        if None in files:
            files.remove(None)
        #import ipdb; ipdb.set_trace()
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
        # import ipdb; ipdb.set_trace()
        return self.template()


class _EntryViewMixin(object):

    def can_see_history(self):
        return True

    def can_edit(self):
        return api.user.has_permission(permissions.ModifyPortalContent, obj=self.context)

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
        return api.user.has_permission(permissions.ReviewPortalContent, obj=self.context)

    def can_set_private(self):
        return api.user.has_permission(permissions.ReviewPortalContent, obj=self.context)

    def can_lock(self):
        return api.user.has_permission(permissions.ReviewPortalContent, obj=self.context)

    def isOwner(self):
        user = api.user.get_current()
        return 'Owner' in user.getRolesInContext(self.context)

    def isReviewer(self):
        user = api.user.get_current()
        return 'Reviewer' in user.getRolesInContext(self.context)

    def isManager(self):
        user = api.user.get_current()
        return any(role in user.getRolesInContext(self.context) for role in ['Manager', 'SiteAdmin'])
