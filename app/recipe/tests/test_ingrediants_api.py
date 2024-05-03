"""
Tests for the ingrediants API.
"""
from django.urls import reverse
from django.test import TestCase
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingrediant

from recipe.serializers import IngrediantSerializer


INGREDIENTS_URL = reverse('recipe:ingrediant-list')


def detail_url(ingrediant_id):
    """Return ingrediant detail URL."""
    return reverse('recipe:ingrediant-detail', args=[ingrediant_id])


def create_user(email="user@example.com", password="testpass"):
    """Create and return user."""
    return get_user_model().objects.create_user(email, password)


class PublicIngrediantApiTests(TestCase):
    """Test the publically available ingrediants API. (Unauthorized)"""

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """Test that login is required to access the endpoint."""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngrediantApiTests(TestCase):
    """Test the private ingrediants API. (Authorized)"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients_list(self):
        """Test retrieving a list of ingredients."""
        Ingrediant.objects.create(user=self.user, name="Kale")
        Ingrediant.objects.create(user=self.user, name="Salt")

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingrediant.objects.all().order_by('-name')
        serializer = IngrediantSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """
        Test that only ingredients for the authenticated user are returned.
        """
        user2 = create_user(email="user2@example.com", password="testpass")
        Ingrediant.objects.create(user=user2, name="Vinegar")
        ingredient = Ingrediant.objects.create(user=self.user, name="Tumeric")

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["name"], ingredient.name)
        self.assertEqual(res.data[0]["id"], ingredient.id)

    def test_update_ingrediant(self):
        """Test updating an ingredient."""
        ingredient = Ingrediant.objects.create(user=self.user, name="Vinegar")
        payload = {"name": "Cabbage"}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload["name"])

    def test_delete_ingrediant(self):
        """Test deleting an ingredient."""
        ingredient = Ingrediant.objects.create(user=self.user, name="Vinegar")
        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Ingrediant.objects.count(), 0)
