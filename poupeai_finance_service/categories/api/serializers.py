from rest_framework import serializers
from poupeai_finance_service.categories.models import Category

class CreateCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'color_hex', 'type', 'profile', 'created_at', 'updated_at']
        read_only_fields = ['profile']
                  
    def create(self, validated_data):
        profile = self.context['profile']
        validated_data['profile'] = profile
        return super().create(validated_data)

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'color_hex', 'type', 'profile', 'created_at', 'updated_at']
        read_only_fields = ['id', 'profile', 'type', 'created_at', 'updated_at']
