from rest_framework import serializers
from django.db.models import Avg, Sum, Count # Ensure Count is imported
from django.contrib.auth import get_user_model # Import get_user_model
from .models import (
    Project, ProjectPicture, Donation, Rating, Comment, Category, Tag,
    ProjectReport, CommentReport # Import new report models
)

User = get_user_model()

# Basic User serializer for nested representation
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name'] # Removed profile_picture as it's not default


class ProjectPictureSerializer(serializers.ModelSerializer):
    """Serializer for project pictures with full URLs"""
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProjectPicture
        # Corrected fields: 'image' and 'uploaded_at'. Removed non-existent 'is_main', 'order'
        fields = ['id', 'image', 'image_url', 'uploaded_at']
        read_only_fields = ['uploaded_at']

    def get_image_url(self, obj):
        """Get full image URL for React frontend"""
        if obj.image:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url # Fallback if request context is not available
        return None


class DonationSerializer(serializers.ModelSerializer):
    """Serializer for donations with user name display"""
    user_name = serializers.SerializerMethodField() # Get username from the related User object

    class Meta:
        model = Donation
        # Use 'user' (the FK field) and 'donated_at' (the DateTimeField)
        fields = ['id', 'user', 'user_name', 'amount', 'donated_at']
        read_only_fields = ['user', 'donated_at']

    def get_user_name(self, obj):
        """Get user's username for display"""
        if obj.user:
            return obj.user.username
        return "Anonymous User" # Handle cases where user might be null


class RatingSerializer(serializers.ModelSerializer):
    """Serializer for project ratings"""
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Rating
        # Use 'value' as per the Rating model field
        fields = ['id', 'user', 'user_name', 'value', 'created_at']
        read_only_fields = ['user', 'created_at']


class ProjectReportSerializer(serializers.ModelSerializer):
    """Serializer for reporting projects"""
    reporter_username = serializers.CharField(source='reporter.username', read_only=True)

    class Meta:
        model = ProjectReport
        fields = ['id', 'project', 'reporter', 'reporter_username', 'report_type', 'reason', 'created_at', 'status']
        read_only_fields = ['reporter', 'created_at', 'status'] # Reporter will be set by the view

    def create(self, validated_data):
        # Set reporter from request context
        validated_data['reporter'] = self.context['request'].user
        # Project should be passed from the view, not necessarily in validated_data
        if 'project' not in validated_data:
            raise serializers.ValidationError("Project is required for a project report.")
        return super().create(validated_data)


class CommentReportSerializer(serializers.ModelSerializer):
    """Serializer for reporting comments"""
    reporter_username = serializers.CharField(source='reporter.username', read_only=True)

    class Meta:
        model = CommentReport
        fields = ['id', 'comment', 'reporter', 'reporter_username', 'report_type', 'reason', 'created_at', 'status']
        read_only_fields = ['reporter', 'created_at', 'status']

    def create(self, validated_data):
        validated_data['reporter'] = self.context['request'].user
        if 'comment' not in validated_data:
            raise serializers.ValidationError("Comment is required for a comment report.")
        return super().create(validated_data)


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for Comments, with recursive replies"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    replies = serializers.SerializerMethodField() # To include nested replies

    class Meta:
        model = Comment
        fields = ['id', 'user', 'user_name', 'project', 'content', 'created_at', 'is_active', 'parent', 'replies']
        read_only_fields = ['user', 'project', 'created_at', 'is_active']

    def get_replies(self, obj):
        # Recursively serialize replies for this comment, only active ones
        active_replies = obj.replies.filter(is_active=True).order_by('created_at')
        # Avoid circular import by getting the serializer on demand (self.__class__)
        return self.__class__(active_replies, many=True, read_only=True, context=self.context).data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        # Project should be passed from the view when creating a comment (e.g., from URL pk)
        if 'project' not in validated_data:
            raise serializers.ValidationError("Project is required for a comment.")
        return super().create(validated_data)


class ProjectListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for project lists (homepage, search, etc.)"""
    owner = UserSerializer(read_only=True) # Nested UserSerializer for owner
    category = serializers.SerializerMethodField()
    pictures = ProjectPictureSerializer(many=True, read_only=True) # Use ProjectPictureSerializer
    
    # Directly use model fields or properties that reflect current/average values
    total_donations = serializers.SerializerMethodField() # From @property
    percent_funded = serializers.SerializerMethodField()   # From @property
    average_rating = serializers.FloatField(read_only=True) # Direct field on Project model
    donations_count = serializers.IntegerField(read_only=True) # From annotation or Count('donations')
    
    class Meta:
        model = Project
        fields = [
            'id', 'title', 'details', 'category', 'pictures',
            'total_target', 'total_donations', 'percent_funded', 'average_rating',
            'donations_count', 'owner', 'status', 'is_featured',
            'start_time', 'end_time', 'created_at', 'updated_at'
        ]

    def get_category(self, obj):
        """Get category details (removed slug)"""
        if obj.category:
            return {'id': obj.category.id, 'name': obj.category.name}
        return None

    def get_total_donations(self, obj):
        """Get total donations amount from model property or annotation"""
        # Prioritize annotated value if available (from get_queryset in views)
        return getattr(obj, 'total_donations_annotated', obj.total_donations_collected)

    def get_percent_funded(self, obj):
        """Get percentage funded from model property"""
        return obj.percent_funded

    def get_donations_count(self, obj):
        """Get donations count from annotation or direct count"""
        return getattr(obj, 'donations_count_annotated', obj.donations.count())


class ProjectDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single project view"""
    pictures = ProjectPictureSerializer(many=True, read_only=True)
    owner = UserSerializer(read_only=True)
    category = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    donations = DonationSerializer(many=True, read_only=True)
    ratings = RatingSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True) 

    # Direct fields from model (cached values)
    average_rating = serializers.FloatField(read_only=True)
    rating_count = serializers.IntegerField(read_only=True)

    # Calculated properties from the model
    total_donations = serializers.SerializerMethodField()
    percent_funded = serializers.SerializerMethodField()
    donations_count = serializers.SerializerMethodField() # Redundant with direct field if annotated, but for consistency

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'details', 'total_target', 'owner', 'category', 'tags',
            'start_time', 'end_time', 'created_at', 'updated_at', 'status', 'is_featured',
            'average_rating', 'rating_count', # Direct model fields
            'pictures', 'donations', 'ratings', 'comments', # Nested serializers
            'total_donations', 'percent_funded', 'donations_count', # Calculated properties/methods
        ]

    def get_category(self, obj):
        if obj.category:
            return {'id': obj.category.id, 'name': obj.category.name}
        return None

    def get_tags(self, obj):
        return [{'id': tag.id, 'name': tag.name} for tag in obj.tags.all()]

    def get_total_donations(self, obj):
        return getattr(obj, 'total_donations_annotated', obj.total_donations_collected)

    def get_percent_funded(self, obj):
        return obj.percent_funded

    def get_donations_count(self, obj):
        return getattr(obj, 'donations_count_annotated', obj.donations.count())


class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating projects"""
    # Use PrimaryKeyRelatedField for category and tags for input
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True, required=False, allow_null=True
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, source='tags', write_only=True, required=False
    )

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'details', 'total_target',
            'start_time', 'end_time', 'status', 'is_featured',
            'category_id', 'tag_ids',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'owner'] # Owner set by view

    def validate_title(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Title must be at least 5 characters long.")
        return value.strip()

    def validate_details(self, value):
        if len(value.strip()) < 100:
            raise serializers.ValidationError("Description must be at least 100 characters long.")
        return value.strip()

    def validate_total_target(self, value):
        if value < 100:
            raise serializers.ValidationError("Minimum funding goal is 100 EGP.")
        return value

    def validate(self, attrs):
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')

        if start_time and end_time:
            if end_time <= start_time:
                raise serializers.ValidationError({
                    'end_time': 'End date must be after start date.'
                })

            duration = end_time - start_time
            if duration.days < 7:
                raise serializers.ValidationError({
                    'end_time': 'Campaign must run for at least 7 days.'
                })
        return attrs

    def create(self, validated_data):
        # Pop category and tags, they will be set after project creation
        category = validated_data.pop('category', None)
        tags = validated_data.pop('tags', [])

        validated_data['owner'] = self.context['request'].user
        project = Project.objects.create(**validated_data)

        if category:
            project.category = category
            project.save() # Save project again if category was updated

        project.tags.set(tags) # Set many-to-many relationship
        return project

    def update(self, instance, validated_data):
        # Pop category and tags for separate handling
        category = validated_data.pop('category', None)
        tags = validated_data.pop('tags', [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if category: # Update category if provided
            instance.category = category
        
        instance.tags.set(tags) # Update many-to-many relationship

        instance.save()
        return instance

