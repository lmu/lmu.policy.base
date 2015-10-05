import logging
import transaction

from plone import api
from StringIO import StringIO
#from Products.PlonePAS.Extensions.Install import activatePluginInterface
from Products.AutoRoleFromHostHeader.plugins.AutoRole import AutoRole

log = logging.getLogger(__name__)

PRODUCT_DEPENDENCIES = (
    'Products.AutoUserMakerPASPlugin',
)


def setupVarious(context):
    """Install all additional Things that can't be done via Generic Setup
    """

    if context.readDataFile('lmu.policy.base_default.txt') is None:
        return

    _setupAutoUserMaker(context)
    _setupAutoRoleHeader(context)


def _setupAutoRoleHeader(context):
    acl_users = api.portal.get_tool('acl_users')
    portal = api.portal.get()

    #import ipdb; ipdb.set_trace()
    out = StringIO()

    arh_cmsadmins = AutoRole('auto_role_header_cms-admins',
                             title='AutoRole for CMS-Admins',
                             match_roles=('Groupmembership; cms-admins-insp; Site Administrator'))

#    activatePluginInterface(portal, arh_cmsadmins, out)

    auto_role = acl_users['auto_role_header']
    auto_role.manage_changeProperties(
        match_roles=('Groupmembership; cms-admins-insp; Site Administrator',)
    )


def _setupAutoUserMaker(context):
    portal_quickinstaller = api.portal.get_tool('portal_quickinstaller')
    for product in PRODUCT_DEPENDENCIES:
        if not portal_quickinstaller.isProductInstalled(product):
            portal_quickinstaller.installProduct(product)
            #transaction.savepoint(True)
    acl_users = api.portal.get_tool('acl_users')
    if 'AutoUserMakerPASPlugin' not in acl_users.objectIds():
        log.warn('AutoUserMakerPASPlugin not found, please install'
                 ' AutoUserMakerPASPlugin!')
    else:
        auto_user = acl_users['AutoUserMakerPASPlugin']
        auto_user.manage_changeProperties(
            http_remote_user='HTTP_EDUPERSONPRINCIPALNAME',
            http_commonname='HTTP_DISPLAYNAME',
            http_email='HTTP_MAIL',
            auto_update_user_properties=1,
        )
