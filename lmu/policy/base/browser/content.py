# -*- coding: utf-8 -*-
import time

from cStringIO import StringIO
from email import utils
from datetime import datetime

from Products.CMFCore import permissions
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from collective.quickupload.portlet.quickuploadportlet import Assignment
from collective.quickupload.portlet.quickuploadportlet import Renderer
from plone import api
from plone.app.discussion.browser.comments import CommentsViewlet
from plone.app.imagecropping.browser.editor import CroppingEditor
from plone.app.textfield.interfaces import ITransformer
from plone.app.z3cform.templates import RenderWidget
from plone.dexterity.browser import add
from plone.dexterity.browser import edit
from z3c.caching.purge import Purge
from z3c.form.interfaces import DISPLAY_MODE
from z3c.form.interfaces import HIDDEN_MODE
from z3c.form.interfaces import INPUT_MODE
from zope.annotation.interfaces import IAnnotations
from zope.component import getMultiAdapter
from zope.event import notify
from zope.interface import alsoProvides

from lmu.policy.base import MESSAGE_FACTORY as _  # XXX move translations
from lmu.policy.base.browser.utils import str2bool
from lmu.policy.base.browser.utils import isDBReadOnly as uIsDBReadOnly
from lmu.policy.base.browser.utils import _IncludeMixin
#from lmu.policy.base.browser.utils import strip_text as ustrip_text
from lmu.policy.base.interfaces import ILMUCommentFormLayer

import json
import PIL.Image

from logging import getLogger

logging = getLogger(__name__)


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

    def isDBReadOnly(self):
        return uIsDBReadOnly()


class _EntryViewMixin(object):

    def can_see_history(self):
        return True

    def can_edit(self):
        return api.user.has_permission(permissions.ModifyPortalContent, obj=self.context) and \
            any(role in ['Owner', 'Site Administrator', 'Manager'] for role in api.user.get_roles(obj=self.context))

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
            any(role in ['Owner', 'Site Administrator', 'Manager'] for role in api.user.get_roles(obj=self.context)) and \
            api.content.get_state(obj=self.context) in ['private', 'closed', 'banned']

    def can_hide(self):
        return False and api.user.has_permission(permissions.RequestReview, obj=self.context) and \
            any(role in ['Owner', 'Site Administrator', 'Manager'] for role in api.user.get_roles(obj=self.context)) and \
            api.content.get_state(obj=self.context) in ['internally_published', 'open']

    def can_reject(self):
        return api.user.has_permission(permissions.ReviewPortalContent, obj=self.context) and \
            any(role in ['Site Administrator', 'Manager'] for role in api.user.get_roles(obj=self.context)) and \
            api.content.get_state(obj=self.context) in ['internally_published', 'open']

    def can_lock(self):
        return api.user.has_permission(permissions.ReviewPortalContent, obj=self.context) and \
            any(role in ['Site Administrator', 'Manager'] for role in api.user.get_roles(obj=self.context)) and \
            api.content.get_state(obj=self.context) in ['internally_published', 'open']

    def isOwner(self):
        user = api.user.get_current()
        return 'Owner' in user.getRolesInContext(self.context)

    def isReviewer(self):
        user = api.user.get_current()
        return 'Reviewer' in user.getRolesInContext(self.context)

    def isManager(self):
        return any(role in ['Manager', 'Site Administrator'] for role in api.user.get_roles(obj=self.context))

    def isPrivate(self):
        return api.content.get_state(obj=self.context) in ['private']

    def isInternallyPublished(self):
        return api.content.get_state(obj=self.context) in ['internally_published', 'open']


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
    parastyles = (_(u'Überschrift 1') + u'|h2|',
                  _(u'Überschrift 2') + u'|h3|',
                  )


#class _AbstractLMUBaseContentEditForm(edit.DefaultEditForm):
#
#    def __call__(self):
#        self.updateWidgets()
#
#        text = self.schema.get('text')
#        text.widget = RichTextWidgetConfig()
#
#        formHelper(self,
#                   fields_to_show=[],
#                   fields_to_input=['title', 'description'],
#                   fields_to_hide=['IPublication.effective', 'IPublication.expires', ],
#                   fields_to_omit=['IPublication.effective', 'IPublication.expires', 'IVersionable.changeNote'])
#
#        buttons = self.buttons
#
#        for button in buttons.values():
#            if button.__name__ == 'save':
#                button.title = _(u'Preview')
#
#        return super(_AbstractLMUBaseContentEditForm, self).__call__()

class _NoCacheEntryMixin(BrowserView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        nowdt = datetime.now()
        nowtuple = nowdt.timetuple()
        nowtimestamp = time.mktime(nowtuple)
        RESPONSE = request.RESPONSE
        RESPONSE.setHeader('Cache-Control', 'private, max-age=0, no-cache')
        RESPONSE.setHeader('Pragma', 'no-cache')
        RESPONSE.setHeader('Expires', utils.formatdate(nowtimestamp))
        super(_NoCacheEntryMixin, self).__init__(context, request)


class EntryContentView(_AbstractLMUBaseContentView, _NoCacheEntryMixin):

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
        return self.context.objectIds()

    def mode_label(self):
        return self.mode[0].upper() + self.mode[1:]

    def content_sortinfo(self):
        return self.content(mode=self.mode)


class EntrySortFilesView(EntryContentView):

    template = ViewPageTemplateFile('templates/entry_sort_items_view.pt')
    mode = 'files'

    def __call__(self):
        return self.template()


class EntrySortImagesView(EntryContentView):

    template = ViewPageTemplateFile('templates/entry_sort_items_view.pt')
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

    index = ViewPageTemplateFile('templates/comments.pt')

    def isDBReadOnly(self):
        return utils.isReadOnly

    def update(self):
        alsoProvides(self.request, ILMUCommentFormLayer)
        super(LMUCommentsViewlet, self).update()

    def can_reply(self):
        is_blog_entry = (self.context.portal_type == 'Blog Entry')
        is_pinnwand_entry = (self.context.portal_type == 'Pinnwand Entry')
        is_private = (api.content.get_state(self.context) == 'private')
        if not uIsDBReadOnly() and (is_blog_entry or is_pinnwand_entry) and is_private:
            return False
        return super(LMUCommentsViewlet, self).can_reply()


class TeaserCroppingEditor(CroppingEditor):

    template = ViewPageTemplateFile('templates/cropping-editor.pt')

    title = _(u"Choose image detail")
    description = _(
        u"Here you can choose a section of the image that will be shown as "
        u"teaser image on listings and overviews. The aspect ratio is forced "
        u"to 16×9. You can later on pick a different section, or remove your "
        u"selection completely to revert to the default."
    )

    def _filter_scales(self, scales):
        return [x for x in scales if x['id'].find('_teaser') > 0]

    def _crop(self):
        """ Filter for all 'teaser' scales and apply the chosen cropping """
        def coordinate(x):
            return int(round(float(self.request.form.get(x))))
        x1 = coordinate('x1')
        y1 = coordinate('y1')
        x2 = coordinate('x2')
        y2 = coordinate('y2')
        scales = self.scales(fieldname=self.fieldname)
        scale_names = [scale['id'] for scale in self._filter_scales(scales)]
        for scale_name in scale_names:
            cropping_util = self.context.restrictedTraverse('@@crop-image')
            cropping_util._crop(fieldname=self.fieldname,
                                scale=scale_name,
                                box=(x1, y1, x2, y2))

    def get_lmu_scale(self):
        """ Find all 'teaser' scales and return the largest one"""
        scales = self.scales(fieldname=self.fieldname)
        if not len(scales):
            return None
        return sorted(
            self._filter_scales(scales),
            key=lambda x: x['thumb_width'], reverse=True
        )[0]


class HardCroppingEditor(CroppingEditor):

    template = ViewPageTemplateFile('templates/cropping-editor.pt')

    title = _(u"Crop Image")
    description = _(
        u"Here you can optionally crop the image, that means choose a section"
        u" of the image that you consider relevant. The parts of the image "
        u"that are not part of your selection will be removed permanently. "
        u"This cannot be undone!"
    )

    def get_lmu_scale(self):
        """ Manually construct a pseudo-scale with free aspect ratio """
        field = getattr(self.context, self.fieldname)
        image_size = field.getImageSize()
        scale = dict()
        select_box = (0, 0, image_size[0], image_size[1])
        large_image_url = self.image_url(self.fieldname)
        config = dict([
            ('allowResize', True),
            ('allowMove', True),
            ('trueSize', [image_size[0], image_size[1]]),
            ('boxWidth', self.default_editor_size[0]),
            ('boxHeight', self.default_editor_size[1]),
            ('setSelect', select_box),
            # No fixed aspect ratio
            ('aspectRatio', None),
            # provide a sensible minimal size without being too restrictive
            ('minSize', [50, 50]),
            ('maxSize', [image_size[0], image_size[1]]),
            ('imageURL', large_image_url),
        ])
        scale['config'] = json.dumps(config)
        # which scale to use for showing the crop area? - we pick 'large'
        scale['id'] = 'large'
        scale['title'] = u'Hard crop'
        scale['selected'] = 'selected'
        scale['is_cropped'] = False
        scale['thumb_width'] = image_size[0]
        scale['thumb_height'] = image_size[1]
        scale['image_url'] = large_image_url
        return scale

    def _crop(self):
        def coordinate(x):
            return int(round(float(self.request.form.get(x))))
        x1 = coordinate('x1')
        y1 = coordinate('y1')
        x2 = coordinate('x2')
        y2 = coordinate('y2')
        box = (x1, y1, x2, y2)
        field = getattr(self.context, self.fieldname, None)
        image_size = field.getImageSize()

        # short-cut: if the "crop" contains the whole image, do nothing
        if (0, 0, image_size[0], image_size[1]) == box:
            return

        data = field.data
        original_file = StringIO(data)
        image = PIL.Image.open(original_file)
        image_format = image.format or self.DEFAULT_FORMAT
        cropped_image = image.crop(box)
        cropped_image_file = StringIO()
        cropped_image.save(cropped_image_file, image_format, quality=100)
        cropped_image_file.seek(0)
        # Overwrite the image field data
        field.data = cropped_image_file.read()

        # Throw away saved scales and cropping info
        annotations = IAnnotations(self.context)
        if 'plone.scale' in annotations:
            del annotations['plone.scale']
        if 'plone.app.imagecropping' in annotations:
            del annotations['plone.app.imagecropping']

        # Purge caches if needed
        notify(Purge(self.context))


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
