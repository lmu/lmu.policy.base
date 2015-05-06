from collective.solr.flare import PloneFlare
from OFS.Traversable import path2url
import logging

logger = logging.getLogger('Search Patch')


def getURL(self, relative=False):
    """ convert the physical path into a url, if it was stored """
    path = self.getPath()
    path = path.encode('utf-8')

    try:
        url = self.request.physicalPathToURL(path, relative)
        if path.startswith(('/prototyp-1/sp', '/prototyp-1/in')):
            url = url.replace('/functions/prototyp-1/sp', '')
            url = url.replace('/functions/prototyp-1/in', '')
    except AttributeError:
        url = path2url(path.split('/'))
    except TypeError:
        url = "/missing/value"
    return url

PloneFlare.getURL = getURL
logger.info("Patching collective.solr.flare.PloneFlare.getURL")
