from rest_framework import serializers
from poupeai_finance_service.profiles.models import Profile


class ProfileSerializer(serializers.ModelSerializer):    
    class Meta:
        model = Profile
        fields = ['user_id', 'email', 'first_name', 'last_name', 'is_deactivated', 'deactivation_scheduled_at', 'created_at', 'updated_at']
        read_only_fields = ['user_id', 'email', 'first_name', 'last_name', 'is_deactivated', 'deactivation_scheduled_at', 'created_at', 'updated_at']