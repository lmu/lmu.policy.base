from collective.solr.flare import PloneFlare
from lmu.policy.base.browser import cms_system
from OFS.Traversable import path2url
import logging

logger = logging.getLogger('Search Patch')


def getURL(self, relative=False):
    """ convert the physical path into a url, if it was stored """
    path = self.getPath()
    path = path.encode('utf-8')

    try:
        url = self.request.physicalPathToURL(path, relative)
        #import ipdb; ipdb.set_trace()
        if self.get('cms_system') != cms_system():
            url = self.get('domain')[0] + self.get('context_path_string')

        #if path.startswith(('/prototyp-1/sp', '/prototyp-1/in')):
        #    url = url.replace('/prototyp-1/sp', '')
        #    url = url.replace('/prototyp-1/in', '')
        #    url = url.replace('fucntions', '')
    except AttributeError:
        url = path2url(path.split('/'))
    except (TypeError, Exception):
        url = None  # "/missing/value"
    return url

PloneFlare.getURL = getURL
logger.info("Patching collective.solr.flare.PloneFlare.getURL")
