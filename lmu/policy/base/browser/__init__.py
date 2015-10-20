# -*- coding: utf-8 -*-

#import StringIO
import logging

from datetime import timedelta
from collective.solr.browser.facets import SearchFacetsView
from collective.solr.browser.facets import convertFacets
from collective.solr.interfaces import ISolrConnectionConfig
from collective.solr.parser import SolrResponse
#from OFS import Image as OFSImage
#from PIL import Image as PILImage
#from Products.PlonePAS.utils import scale_image
from Products.CMFCore.utils import getToolByName
#from Products.CMFPlone.browser.navtree import getNavigationRoot
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
from plone.registry.interfaces import IRegistry
from urllib import unquote
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryUtility

#from lmu.policy.base.browser.content_listing import _AbstractLMUBaseListingView
from lmu.policy.base.browser.utils import strip_text as ustrip_text
#from lmu.policy.base.browser.utils import str2bool
from lmu.policy.base.browser.utils import _IncludeMixin

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
        #import ipdb;ipdb.set_trace()

        log.info("Raw Results: %s", results.__dict__)
        results = IContentListing(results)
        if batch:
            results = Batch(results, b_size, b_start)
        results.qtime = qtime

        log.info("Processed Results: %s", results.__dict__)
        return results

    def extra_types(self):
        ptool = getToolByName(self, 'portal_properties')
        siteProperties = getattr(ptool, 'site_properties')
        extraTypes = siteProperties.getProperty('extra_types_searched', [])
        return list(extraTypes)

    def filter_query(self, query):
        query = super(Search, self).filter_query(query)
        #import ipdb; ipdb.set_trace()
        if query:
            # Only show Fiona Content in results that are from 'sp'
            #if getNavigationRoot(self.context) == '/intranet':
            #    query['path'] = [getNavigationRoot(self.context), '/prototyp-1/in']
            #elif getNavigationRoot(self.context) == '/serviceportal':
            #    query['path'] = [getNavigationRoot(self.context), '/prototyp-1/sp']
            #else:
            #    query['path'] = [getNavigationRoot(self.context)]

            query['portal_type'] += self.extra_types()
        log.info("Search Query: %s", query)
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

    def strip_text(item, length=500):
        return ustrip_text(item, length=length)

    def unquote(self, string):
        return unquote(string)


class LMUSearchFacetsView(SearchFacetsView):

    @property
    def shown_types(self):
        ptool = getToolByName(self, 'portal_properties')
        siteProperties = getattr(ptool, 'site_properties')
        shown_types = siteProperties.getProperty(
            'types_search_facets', [])
        return list(shown_types)

    def facets(self):
        """ prepare and return facetting info for the given SolrResponse """
        results = self.kw.get('results', None)
        fcs = getattr(results, 'facet_counts', None)
        shown_types = self.shown_types
        if results is not None and fcs is not None:
            def facet_filter(name, count):
                return name and name in shown_types and count > 0
            return convertFacets(
                fcs.get('facet_fields', {}), self, facet_filter)
        else:
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


class UserInfo(BrowserView, _IncludeMixin):

    template = ViewPageTemplateFile('templates/user_info.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        user = api.user.get_current()
        pm = api.portal.get_tool('portal_membership')
        #self.username = user.getProperty('fullname')
        self.username = user.getProperty('description')
        portrait = pm.getPersonalPortrait()
        #image = Image.open(StringIO.StringIO(portrait.data))
        #self.portrait = image.resize((30, 30))
        #import ipdb; ipdb.set_trace()
        #small_portrait, mimetype = scale_image(StringIO.StringIO(portrait.data), (30, 30))
        #self.portrait = OFSImage.Image(id=user.getUserName(), file=small_portrait, title='')
        self.portrait = portrait
        return super(UserInfo, self).__call__()


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
