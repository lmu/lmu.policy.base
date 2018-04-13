# -*- coding: utf-8 -*-
from plone.app.imagecropping.dx import _millis
from plone.app.imagecropping.dx import CroppingUtilsDexterity
from plone.app.imagecropping.interfaces import IImageCroppingUtils
from plone.app.imaging.utils import getAllowedSizes
from plone.namedfile.interfaces import IImageScaleTraversable
from plone.scale.scale import scaleImage
from plone.scale.storage import AnnotationStorage
from zope.component import adapter
from zope.interface import implementer


@implementer(IImageCroppingUtils)
@adapter(IImageScaleTraversable)
class LMUCroppingUtilsDexterity(CroppingUtilsDexterity):

    def save_cropped(self, fieldname, scale, image_file):
        """ see interface
        """
        sizes = getAllowedSizes()
        w, h = sizes[scale]

        def crop_factory(fieldname, **parameters):
            result = scaleImage(image_file.read(), **parameters)
            if result is not None:
                data, format, dimensions = result
                mimetype = 'image/{0:s}'.format(format.lower())
                field = self.get_image_field(fieldname)
                value = field.__class__(
                    data,
                    contentType=mimetype,
                    filename=field.filename
                )
                value.fieldname = fieldname
                return value, format, dimensions

        # call storage with actual time in milliseconds
        # this always invalidates old scales
        storage = AnnotationStorage(self.context, _millis)

        # We need to pass direction='thumbnail' since this is the default
        # used by plone.namedfile.scaling, also for retrieval of scales.
        # Otherwise the key under which the scaled and cropped image is
        # saved in plone.scale.storage.AnnotationStorage will not match the
        # key used for retrieval (= the cropped scaled image will not be
        # found)
        storage.scale(
            factory=crop_factory,
            direction='thumbnail',
            fieldname=fieldname,
            width=w,
            height=h,
        )
