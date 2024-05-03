"""
Serializers for recipe APIs
"""
from rest_framework import serializers

from core.models import Recipe, Tag, Ingrediant


class IngrediantSerializer(serializers.ModelSerializer):
    """Serializer for ingrediant objects."""

    class Meta:
        model = Ingrediant
        fields = ('id', 'name')
        read_only_fields = ('id',)


class TagSerializer(serializers.ModelSerializer):
    """Serializer for tag objects."""

    class Meta:
        model = Tag
        fields = ('id', 'name')
        read_only_fields = ('id',)


class RecipeSerializer(serializers.ModelSerializer):
    """Serializer for recipe objects."""
    tags = TagSerializer(many=True, required=False)
    ingrediants = IngrediantSerializer(many=True, required=False)

    class Meta:
        model = Recipe
        fields = (
            'id', 'title', 'time_minutes', 'price', 'link',
            'tags', "ingrediants"
        )
        read_only_fields = ('id',)

    def _get_or_create_tags(self, tags, recipe):
        """Get or create tags."""
        auth_user = self.context['request'].user
        for tag in tags:
            tag_obj, _ = Tag.objects.get_or_create(user=auth_user, **tag)
            recipe.tags.add(tag_obj)

    def _get_or_create_ingrediants(self, ingrediants, recipe):
        """Get or create ingrediants."""
        auth_user = self.context['request'].user
        for ingrediant in ingrediants:
            ingrediant_obj, _ = Ingrediant.objects.get_or_create(
                user=auth_user, **ingrediant)
            recipe.ingrediants.add(ingrediant_obj)

    def create(self, validated_data):
        """Create a recipe."""
        tags = validated_data.pop('tags', [])
        ingrediants = validated_data.pop('ingrediants', [])
        recipe = Recipe.objects.create(**validated_data)
        self._get_or_create_tags(tags, recipe)
        self._get_or_create_ingrediants(ingrediants, recipe)
        return recipe

    def update(self, instance, validated_data):
        """Update recipe."""
        tags = validated_data.pop('tags', None)
        ingrediants = validated_data.pop('ingrediants', None)

        if tags is not None:
            instance.tags.clear()
            self._get_or_create_tags(tags, instance)
        if ingrediants is not None:
            instance.ingrediants.clear()
            self._get_or_create_ingrediants(ingrediants, instance)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class RecipeDetailSerializer(RecipeSerializer):
    """Serializer for recipe detail objects."""

    class Meta(RecipeSerializer.Meta):
        model = Recipe
        fields = RecipeSerializer.Meta.fields + ('description',)
