# -*- coding: utf-8 -*-

#import StringIO
import logging

from datetime import timedelta
from collective.solr.browser.facets import SearchFacetsView
from collective.solr.browser.facets import convertFacets
from collective.solr.interfaces import ISolrConnectionConfig
from collective.solr.parser import SolrResponse
from Missing import Value as MissingValue
#from OFS import Image as OFSImage
#from PIL import Image as PILImage
#from Products.PlonePAS.utils import scale_image
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.browser.navtree import getNavigationRoot
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


def cms_system():
    registry = getUtility(IRegistry)
    lmu_settings = registry.forInterface(ILMUSettings)
    return lmu_settings.cms_system


def search_paths():
    registry = getUtility(IRegistry)
    lmu_settings = registry.forInterface(ILMUSettings)
    return lmu_settings.search_paths


def portal_domains():
    registry = getUtility(IRegistry)
    lmu_settings = registry.forInterface(ILMUSettings)
    return lmu_settings.domain


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

        log.debug("Raw Results: %s", getattr(results, '__dict__', {}))
        results = IContentListing(results)
        if batch:
            results = Batch(results, b_size, b_start)
        results.qtime = qtime

        log.debug("Processed Results: %s", getattr(results, '__dict__', {}))
        return results

    def extra_types(self):
        ptool = getToolByName(self, 'portal_properties')
        siteProperties = getattr(ptool, 'site_properties')
        extraTypes = siteProperties.getProperty('extra_types_searched', [])
        return list(extraTypes)

    def filter_query(self, query):
        query = super(Search, self).filter_query(query)
        if query:
            #import ipdb; ipdb.set_trace()
            if query['path'] == getNavigationRoot(self.context) or query['path'] is None:
                query['path'] = search_paths()
                log.debug('Make general path search, request was for "%s".', getNavigationRoot(self.context))
            else:
                log.debug('Make specific path ("%s") search.', query['path'])

            query['portal_type'] += self.extra_types()
        log.debug("Search Query: %s", query)
        return query

    def types_list(self):
        types = super(Search, self).types_list()
        return types + self.extra_types()

    def breadcrumbs(self, item):
        breadcrumbs = []
        schema = 'https://'
        #import ipdb; ipdb.set_trace()
        try:
            flare = getattr(item, 'flare', {})
            # Lookup primary Domain Name:
            domain = flare.get('domain', [])
            if domain and not isinstance(domain, type(MissingValue)):
                domain = domain[0]
                domain = domain.replace('https://', '')
                domain = domain.replace('http://', '')

            if flare and flare.get('cms_system') != cms_system():
                urls = flare.get('path_parents')
                titles = flare.get('breadcrumb_parent_titles')
                root_url = urls[1]
                while titles and len(titles) >= len(urls):
                    title = titles.pop()
                    url = urls.pop()
                    if title:
                        url = url.replace(root_url, '')
                        breadcrumbs.insert(0, {'absolute_url': schema + domain + url + '/index.html', 'Title': unicode(title, 'utf-8')})

            else:
                obj = item.getObject()
                view = getMultiAdapter((obj, self.request), name='breadcrumbs_view')
                # cut off the item itself
                breadcrumbs = list(view.breadcrumbs())[:-1]

                if domain != portal_domains[0]:
                    log.info('Wrong url in breadcrumb: %s', breadcrumbs)

            if domain and not isinstance(domain, type(MissingValue)):
                log.debug('Insert Breadcrumb for Portal-Root: "%s"', domain)
                if domain == 'www.intranet.verwaltung.uni-muenchen.de':
                    portal_root_breadcrumb = {'absolute_url': 'https://www.intranet.verwaltung.uni-muenchen.de/index.html', 'Title': unicode('ZUV-Intranet', 'utf-8')}
                elif domain == 'www.serviceportal.verwaltung.uni-muenchen.de':
                    portal_root_breadcrumb = {'absolute_url': 'https://www.serviceportal.verwaltung.uni-muenchen.de/index.html', 'Title': unicode('Serviceportal', 'utf-8')}
                else:
                    portal_root_breadcrumb = {'absolute_url': schema + domain + '/', 'Title': unicode('Portal', 'utf-8')}
                breadcrumbs.insert(0, portal_root_breadcrumb)

            if len(breadcrumbs) == 0:
                # don't show breadcrumbs if we only have a single element
                return None
            if len(breadcrumbs) > 4:
                # if we have too long breadcrumbs, emit the middle elements
                empty = {'absolute_url': '', 'Title': unicode('…', 'utf-8')}
                breadcrumbs = [breadcrumbs[0], breadcrumbs[1], empty] + breadcrumbs[-2:]
        except AttributeError as e:
            log.warn('During Breadcrumb generation has happend an Attribute error, "%s" is not found', e)
        except Exception as e:
            #import ipdb; ipdb.set_trace()
            log.warn('%s during Breadcrumb generation, %s', type(e), e)
            return None
        return breadcrumbs

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

        params = {'SearchableText': self.request.get('q', ''),  # self.searchterms(quote=False),
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


class Repair(BrowserView):

    def __call__(self):
        registry = getUtility(IRegistry)
        registry.registerInterface(ILMUSettings)
        return "Update erfolgreich"
