"""
Tests for recipe API.
"""
from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingrediant

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """Return recipe detail URL."""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    """Return URL for recipe image upload."""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def create_recipe(user, **params):
    """Create and return a sample recipe."""
    defaults = {
        'title': 'Sample recipe',
        'description': 'Sample description',
        'time_minutes': 10,
        'price': Decimal('5.00'),
        'link': "https://sample.com"
    }
    defaults.update(params)

    return Recipe.objects.create(user=user, **defaults)


def create_user(**params):
    """Create and return a sample user."""
    return get_user_model().objects.create_user(**params)


class PublicRecipeApiTests(TestCase):
    """Test unauthenticated recipe API access."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required."""
        response = self.client.get(RECIPES_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test authenticated recipe API access."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='user@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes."""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_recipes_limited_to_user(self):
        """Test retrieving recipes for user."""
        user2 = create_user(
            email='new@example.com',
            password='testpass123'
        )
        create_recipe(user=user2)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)

    def test_view_recipe_detail(self):
        """Test viewing a recipe detail."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Test creating recipe."""
        payload = {
            'title': 'Chocolate cheesecake',
            'description': 'Delicious chocolate cheesecake',
            'time_minutes': 30,
            'price': Decimal('5.00')
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])

        for k, v in payload.items():
            self.assertEqual(v, getattr(recipe, k))

        self.assertEqual(recipe.user, self.user)

    def test_partial_update_recipe(self):
        """Test updating a recipe with patch."""
        recipe = create_recipe(user=self.user)
        payload = {
            'title': 'Chicken tikka'
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()

        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.user, self.user)

    def test_full_update_recipe(self):
        """Test updating a recipe with put."""
        recipe = create_recipe(user=self.user)
        payload = {
            'title': 'Spaghetti carbonara',
            'description': 'Spaghetti with bacon',
            'link': 'https://example.com/spaghetti-carbonara',
            'time_minutes': 25,
            'price': Decimal('7.00')
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()

        for k, v in payload.items():
            self.assertEqual(v, getattr(recipe, k))
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """Test that updating user returns error."""
        user2 = create_user(email='user2@example.com', password='testpass123')
        recipe = create_recipe(user=self.user)

        payload = {
            'user': user2.id
        }
        url = detail_url(recipe.id)
        self.client.patch(url, payload)
        recipe.refresh_from_db()

        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe successfully."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_recipe_other_users_recipe_error(self):
        """Test trying to delete another users recipe gives error."""
        new_user = create_user(email='user2@example.com', password='test123')
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        """Test creating a recipe with new tags."""
        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 30,
            'price': Decimal('10.00'),
            'tags': [{'name': 'Thai'}, {'name': 'Dinner'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes.first()
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        """Test creating a recipe with existing tags."""
        tag_indian = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 30,
            'price': Decimal('10.00'),
            'tags': [{'name': 'Indian'}, {'name': "Breakfast"}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes.first()
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test creating a tag on recipe update."""
        recipe = create_recipe(user=self.user)
        payload = {
            'tags': [{'name': 'Lunch'}]
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """Test asigning as existing tag when updating a recipe."""
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {
            'tags': [{'name': 'Lunch'}]
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """Test clearing all tags from a recipe."""
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        payload = {
            'tags': []
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingrediants(self):
        """Test creating a recipe with new ingrediants."""
        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 30,
            'price': Decimal('10.00'),
            'ingrediants': [{'name': 'Prawns'}, {'name': 'Curry'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes.first()
        self.assertEqual(recipe.ingrediants.count(), 2)
        for ingredient in payload['ingrediants']:
            exists = recipe.ingrediants.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredient(self):
        """Test creating a recipe with existing ingrediants."""
        ingredient_salt = Ingrediant.objects.create(user=self.user,
                                                    name='Salt')
        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 30,
            'price': Decimal('10.00'),
            'ingrediants': [{'name': 'Salt'}, {'name': "Curry"}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes.first()
        self.assertEqual(recipe.ingrediants.count(), 2)
        self.assertIn(ingredient_salt, recipe.ingrediants.all())
        for ingredient in payload['ingrediants']:
            exists = recipe.ingrediants.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """Test creating an ingredient on recipe update."""
        recipe = create_recipe(user=self.user)
        payload = {
            'ingrediants': [{'name': 'Salt'}]
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingrediant.objects.get(user=self.user, name='Salt')
        self.assertIn(new_ingredient, recipe.ingrediants.all())

    def test_update_recipe_assign_ingrediant(self):
        """Test assigning an existing ingredient when updating a recipe."""
        ingredient_salt = Ingrediant.objects.create(user=self.user,
                                                    name='Salt')
        recipe = create_recipe(user=self.user)
        recipe.ingrediants.add(ingredient_salt)

        ingredient_pepper = Ingrediant.objects.create(user=self.user,
                                                      name='Pepper')
        payload = {
            'ingrediants': [{'name': 'Pepper'}]
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient_pepper, recipe.ingrediants.all())
        self.assertNotIn(ingredient_salt, recipe.ingrediants.all())

    def test_clear_recipe_ingrediants(self):
        """Test clearing all ingrediants from a recipe."""
        ingredient_salt = Ingrediant.objects.create(user=self.user,
                                                    name='Salt')
        recipe = create_recipe(user=self.user)
        recipe.ingrediants.add(ingredient_salt)

        payload = {
            'ingrediants': []
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingrediants.count(), 0)

    def test_filter_by_tags(self):
        """Test returning recipes with specific tags."""
        recipe1 = create_recipe(user=self.user, title='Thai curry')
        recipe2 = create_recipe(user=self.user, title='Aloo Gobi')
        tag1 = Tag.objects.create(user=self.user, name='Vegan')
        tag2 = Tag.objects.create(user=self.user, name='Vegetarian')
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)

        recipe3 = create_recipe(user=self.user, title='Fish and Chips')

        res = self.client.get(
            RECIPES_URL,
            {'tags': f'{tag1.id},{tag2.id}'}
        )

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_by_ingredients(self):
        """Test returning recipes with specific ingredients."""
        recipe1 = create_recipe(user=self.user, title='Thai curry')
        recipe2 = create_recipe(user=self.user, title='Aloo Gobi')
        ingredient1 = Ingrediant.objects.create(user=self.user, name='Ginger')
        ingredient2 = Ingrediant.objects.create(user=self.user, name='Potato')
        recipe1.ingrediants.add(ingredient1)
        recipe2.ingrediants.add(ingredient2)

        recipe3 = create_recipe(user=self.user, title='Fish and Chips')

        res = self.client.get(
            RECIPES_URL,
            {'ingrediants': f'{ingredient1.id},{ingredient2.id}'}
        )

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)


class ImageUploadTests(TestCase):
    """Test image upload for recipes."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@example.com",
            "password123"
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image_to_recipe(self):
        """Test uploading an image to a recipe."""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            res = self.client.post(url,
                                   {'image': image_file},
                                   format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image."""
        url = image_upload_url(self.recipe.id)
        res = self.client.post(url,
                               {'image': 'notanimage'},
                               format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
