from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.utils.translation import gettext_lazy as _
from poupeai_finance_service.categories.models import Category

class CreateCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'color_hex', 'type', 'profile', 'created_at', 'updated_at']
        read_only_fields = ['profile']

    def validate_name(self, name):
        profile = self.context['profile']
        if Category.objects.filter(profile=profile, name=name).exists():
            raise DRFValidationError(_("A category with this name already exists for this profile."))
        return name
            
    def create(self, validated_data):
        profile = self.context['profile']
        validated_data['profile'] = profile
        return super().create(validated_data)

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'color_hex', 'type', 'profile', 'created_at', 'updated_at']
        read_only_fields = ['id', 'profile', 'type', 'created_at', 'updated_at']
    
    def validate_name(self, name):
        profile = self.context['profile']
        qs = Category.objects.filter(profile=profile, name=name)
        
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise DRFValidationError(_("A category with this name already exists for this profile."))
        return name
