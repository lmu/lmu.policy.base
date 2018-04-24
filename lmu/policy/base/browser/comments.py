# coding=utf-8
from plone.namedfile.browser import Download
from plone.namedfile.scaling import ImageScale
from plone.namedfile.scaling import ImageScaling
from zope.publisher.interfaces import NotFound


class CommentDownload(Download):
    ''' Customization to overcome the traversing limitation of comment objects
    '''

    def _getFile(self):
        context = getattr(self.context, 'aq_explicit', self.context)
        file = getattr(context, self.fieldname, None)

        if file is None:
            raise NotFound(self, self.fieldname, self.request)

        return file


class CommentImageScale(ImageScale):
    ''' Customization to overcome the traversing limitation of comment objects
    '''

    def validate_access(self):
        return


class CommentImageScaling(ImageScaling):
    ''' Customize the @@images view for the comment content type
    '''
    _scale_view_class = CommentImageScale
