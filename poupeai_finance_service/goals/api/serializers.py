from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from poupeai_finance_service.goals.validators import validate_date_not_in_past
from poupeai_finance_service.goals.models import Goal, GoalDeposit
from poupeai_finance_service.profiles.models import Profile

class GoalValidationMixin:    
    def _validate_initial_balance(self, data):
        initial_balance = data.get('initial_balance')
        goal_amount = data.get('goal_amount')
        
        if initial_balance is not None and goal_amount is not None and initial_balance > goal_amount:
            raise DRFValidationError({'initial_balance': _("Initial balance must be less than goal amount.")})
        
    def _validate_target_at(self, data):
        target_at = data.get('target_at')

        if self.instance:
            if target_at is None:
                target_at = self.instance.target_at

        try:
            validate_date_not_in_past(target_at)
        except ValidationError as e:
            raise DRFValidationError(e.message)
    
    def _validate_profile_context(self, validated_data):
        profile = validated_data.get('profile')
        if not isinstance(profile, Profile):
             raise DRFValidationError({'profile': _("Profile context not provided correctly for creation.")})
    
    def _validate_name(self, validated_data):
        profile = validated_data.get('profile')
        name = validated_data.get('name')
        if Goal.objects.filter(profile=profile, name=name).exists():
            raise DRFValidationError(_("A goal with this name already exists for this profile."))
    
    def _validate_name_update(self, validated_data):
        profile = validated_data.get('profile')
        name = validated_data.get('name')
        qs = Goal.objects.filter(profile=profile, name=name)
        
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise DRFValidationError(_("A goal with this name already exists for this profile."))
        
class GoalListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = ['id', 'name', 'description', 'color_hex', 'initial_balance', 'goal_amount', 'current_balance', 'percentage_completed', 'target_at', 'is_completed', 'completed_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'current_balance', 'percentage_completed', 'completed_at', 'is_completed', 'initial_balance']

class GoalCreateSerializer(GoalValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = ['id', 'name', 'description', 'color_hex', 'initial_balance', 'goal_amount', 'target_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        profile = self.context.get('profile')
        if profile:
            data['profile'] = profile

        self._validate_target_at(data)
        self._validate_initial_balance(data)
        self._validate_name(data)
        return data
        
    def create(self, validated_data):
        self._validate_profile_context(validated_data)
        return super().create(validated_data)

class GoalUpdateSerializer(GoalValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = ['id', 'name', 'description', 'color_hex', 'goal_amount', 'target_at', 'is_completed', 'completed_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_completed', 'completed_at']

    def validate(self, data):
        self._validate_target_at(data)
        self._validate_initial_balance(data)
        self._validate_name_update(data)
        return data

class GoalDetailSerializer(serializers.ModelSerializer):
    deposits = serializers.SerializerMethodField()
    
    class Meta:
        model = Goal
        fields = ['id', 'name', 'description', 'color_hex', 'initial_balance', 'goal_amount', 'current_balance', 'percentage_completed', 'target_at', 'is_completed', 'completed_at', 'deposits']
        read_only_fields = ['id', 'created_at', 'updated_at', 'current_balance', 'percentage_completed', 'completed_at', 'deposits', 'is_completed', 'initial_balance']
    
    def get_deposits(self, obj):
        return GoalDepositSerializer(
            obj.deposits.all().order_by('-deposit_at'), 
            many=True
        ).data

class GoalDepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalDeposit
        fields = ['id', 'deposit_amount', 'deposit_at', 'note', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        profile = self.context.get('profile')
        goal_id = self.context.get('goal_id')
        
        if not profile:
            raise DRFValidationError({'profile': _("Profile context not provided correctly.")})
        
        if not goal_id:
            raise DRFValidationError({'goal': _("Goal ID not provided in context.")})
        
        goal = self._validate_goal(goal_id, profile)
        self._validate_deposit_amount(data, goal)
        self._validate_is_completed(goal)
        self._validate_deposit_at(data, goal)
        data['goal'] = goal
        
        return data
    
    def _validate_goal(self, goal_id, profile):
        try:
            goal = Goal.objects.get(pk=goal_id, profile=profile)
            return goal
        except Goal.DoesNotExist:
            raise DRFValidationError({'goal': _("Goal not found or does not belong to your profile.")})
        
    def _validate_deposit_amount(self, data, goal):
        deposit_amount = data.get('deposit_amount')
        if deposit_amount is not None and deposit_amount + goal.current_balance > goal.goal_amount:
            raise DRFValidationError({'deposit_amount': _("Deposit amount cannot exceed the goal amount.")})
        
    def _validate_is_completed(self, goal):
        if goal.is_completed:
            raise DRFValidationError({'goal': _("Goal is already completed.")})
        
    def _validate_deposit_at(self, data, goal):
        deposit_at = data.get('deposit_at')
        if deposit_at is not None and deposit_at > goal.target_at:
            raise DRFValidationError({'deposit_at': _("Deposit date cannot be after the target date.")})

    def create(self, validated_data):
        goal = validated_data.get('goal')
        if not isinstance(goal, Goal):
            raise DRFValidationError({'goal': _("Goal context not provided correctly for creation.")})

        return super().create(validated_data)