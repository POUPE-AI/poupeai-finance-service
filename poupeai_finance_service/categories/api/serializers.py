from rest_framework import serializers
from poupeai_finance_service.categories.models import Category

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'color_hex', 'type', 'profile_id', 'created_at', 'updated_at']