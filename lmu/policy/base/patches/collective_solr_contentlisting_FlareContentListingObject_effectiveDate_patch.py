import logging

from collective.solr.contentlisting import FlareContentListingObject

logger = logging.getLogger('Search Patch')


def EffectiveDate(self):
    return self.flare.EffectiveDate


FlareContentListingObject.EffectiveDate = EffectiveDate
logger.info("Patching collective.solr.contentlisting.FlareContentListingObject.EffectiveDate")
