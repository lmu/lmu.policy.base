from Products.CMFCore import permissions
from Products.CMFPlone.browser.ploneview import Plone
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from collective.quickupload.portlet.quickuploadportlet import Assignment
from collective.quickupload.portlet.quickuploadportlet import Renderer
from datetime import datetime
from lmu.contenttypes.blog import MESSAGE_FACTORY as _  # XXX move translations
from lmu.policy.base.browser import str2bool
from lmu.policy.base.interfaces import ILMUCommentFormLayer
from plone import api
from plone.app.discussion.browser.comments import CommentsViewlet
from plone.app.textfield.interfaces import ITransformer
from plone.app.z3cform.templates import RenderWidget
from plone.dexterity.browser import add
from plone.dexterity.browser import edit
from z3c.form.interfaces import DISPLAY_MODE
from z3c.form.interfaces import HIDDEN_MODE
from z3c.form.interfaces import INPUT_MODE
from zope.component import getMultiAdapter
from zope.interface import alsoProvides
import json


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

    template = ViewPageTemplateFile('templates/entry_edit.pt')

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
