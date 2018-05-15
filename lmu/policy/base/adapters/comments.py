# coding=utf-8
from lmu.policy.base import MESSAGE_FACTORY as _
from lmu.policy.base.interfaces import ILMUCommentFormLayer
from plone.app.discussion.browser.comments import CommentForm
from plone.app.discussion.comment import Comment
from plone.namedfile.field import NamedBlobFile
from plone.namedfile.field import NamedBlobImage
from plone.z3cform.fieldsets.extensible import FormExtender
from plone.z3cform.fieldsets.interfaces import IFormExtender
from z3c.form.field import Fields
from zope.annotation import factory
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface


class ICommentFormExtender(Interface):
    ''' Extend the comments form providing additional fields
    for image and video upload
    '''
    image = NamedBlobImage(
        title=_(u"Upload an image"),
        required=False,
    )

    file = NamedBlobFile(
        title=_(u"Upload a file"),
        required=False,
    )


@adapter(Comment)
@implementer(ICommentFormExtender)
class CommentFormAdapter(object):
    """ CommentFormAdapter fields.
    """


CommentFormAdapter = factory(CommentFormAdapter)


@implementer(IFormExtender)
@adapter(Interface, ILMUCommentFormLayer, CommentForm)
class CommentFormExtender(FormExtender):
    ''' Extend the comment form with additional extra fields
    '''
    fields = Fields(ICommentFormExtender)

    def update(self):
        self.add(self.fields)
