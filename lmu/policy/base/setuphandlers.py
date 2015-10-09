import logging
import transaction

from plone import api
#from Products.PlonePAS.Extensions.Install import activatePluginInterface
from Products.AutoRoleFromHostHeader.plugins.AutoRole import AutoRole

log = logging.getLogger(__name__)

PRODUCT_DEPENDENCIES = (
    'Products.AutoUserMakerPASPlugin',
)


required_groups = {
    'cms-admins-insp': {
        'roles': ['Manager', 'Site Manager', 'Site Administrator'],
        'title': 'CMS Admins (Virtual Group)',
        'description': 'Virtual Group for Administrators coming from Shibboleth via "cn=cms-admin-insp,ou=..."'
    },
    'in_sp_supportteam': {
        'roles': ['Contributor', 'Editor', 'Reader', 'Reviewer'],
        'title': 'Intranet Supportteam (Virtual Group)',
        'description': 'Virtual Group for the Intranet-Supportteam coming from Shibboleth via "cn=in_sp_supportteam,ou=..."'
    },
}


def setupVarious(context):
    """Install all additional Things that can't be done via Generic Setup
    """

    if context.readDataFile('lmu.policy.base_default.txt') is None:
        return

    _setupAutoUserMaker(context)
#    _setupAutoRoleHeader(context)


def _setupGroups(context):
    #portal = apit.portal.get()
    gtool = api.portal.get_tool(name='portal_groups')
    groups = api.group.get_groups()
    for gid, gdata in required_groups.iteritems():
        if not gid in groups:
            api.group.create(
                groupname=gid,
                title=gdata['title'],
                roles=gdata['roles'],
                description=gdata['description']
            )
        else:
            gtool.editGroup(
                gid,
                title=gdata['title'],
                roles=gdata['roles'],
                description=gdata['description']
            )


#def _setupAutoRoleHeader(context):
#    acl_users = api.portal.get_tool('acl_users')
#
#    #import ipdb; ipdb.set_trace()
#
#    arh_cmsadmins = AutoRole('auto_role_header_cms-admins-insp',
#                             title='AutoRole for CMS-Admins INSP',
#                             match_roles=('Groupmembership; ^(.*?(\b{group_name}\b)[^$]*)$; Site Administrator; python:True'))
#    acl_users['auto_role_header_cms-admins-insp'] = arh_cmsadmins
#
#    arh_supportteam = AutoRole('auto_role_header_supportteam',
#                               title='AutoRole for CMS-Admins INSP',
#                               match_roles=('Groupmembership; ^(.*?(\b{group_name}\b)[^$]*)$; Site Administrator; python:True'))
#
#    acl_users['auto_role_header_supportteam'] = arh_supportteam
#    activatePluginInterface(portal, arh_cmsadmins, out)


def _setupAutoUserMaker(context):
    portal_quickinstaller = api.portal.get_tool('portal_quickinstaller')
    for product in PRODUCT_DEPENDENCIES:
        if not portal_quickinstaller.isProductInstalled(product):
            portal_quickinstaller.installProduct(product)
            transaction.savepoint(True)
    acl_users = api.portal.get_tool('acl_users')
    if 'AutoUserMakerPASPlugin' not in acl_users.objectIds():
        log.warn('AutoUserMakerPASPlugin not found, please install'
                 ' AutoUserMakerPASPlugin!')
    else:
        auto_user = acl_users['AutoUserMakerPASPlugin']
        auto_user.manage_changeProperties(
            strip_domain_names=1,
            strip_domain_name_list="""lmu.de\n""",
            http_remote_user='HTTP_EDUPERSONPRINCIPALNAME',
            http_commonname='HTTP_CN',
            http_email='HTTP_MAIL',
            auto_update_user_properties=1,
        )
