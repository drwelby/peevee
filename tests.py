from django.contrib.gis.geos import Point
from peevee.models import Parcels
from peevee.views import getparcelgeo
from django.test import TestCase

class InternalTest(TestCase):

    fixtures = ['Parcels',]

    def test_parcelgeo(self):
        p = Parcels.objects.all()[1]
        pt = p.geom.centroid
        assert getparcelgeo(pt)[0] == p
