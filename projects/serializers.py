from rest_framework import serializers
from django.db.models import Avg, Sum, Count
from .models import Project, ProjectPicture, Donation, Rating, Comment, Category, Tag # Import all models

# Assuming a simple User serializer if needed, or just return username/id
# class UserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = get_user_model()
#         fields = ['id', 'username', 'first_name', 'last_name']


class ProjectPictureSerializer(serializers.ModelSerializer):
    """Serializer for project pictures with full URLs"""
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProjectPicture
        # Corrected fields: 'image' (not image_file), and removed non-existent 'is_main', 'order'
        fields = ['id', 'image', 'image_url', 'uploaded_at']
        read_only_fields = ['uploaded_at'] # Assuming uploaded_at is auto_now_add

    def get_image_url(self, obj):
        """Get full image URL for React frontend"""
        if obj.image:
            # Ensure obj.image exists before accessing .url
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url # Fallback if request context is not available
        return None


class DonationSerializer(serializers.ModelSerializer):
    """Serializer for donations with user name display"""
    # Corrected: Model has 'user', not 'donor'
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Donation
        # Corrected: 'user' (not donor), 'donated_at' (not donation_date)
        fields = ['id', 'user', 'user_name', 'amount', 'donated_at']
        read_only_fields = ['user', 'donated_at']

    def get_user_name(self, obj):
        """Get donor name (user's username)"""
        # Corrected: Access obj.user.username directly if user is always set
        if obj.user:
            return obj.user.username
        return "Anonymous" # If user is nullable


class RatingSerializer(serializers.ModelSerializer):
    """Serializer for project ratings"""
    # Corrected: Model has 'user', not 'user_name' in fields, source is correct
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Rating
        # Corrected: 'value' (not rating)
        fields = ['id', 'user', 'user_name', 'value', 'created_at']
        read_only_fields = ['user', 'created_at']


# Removed ProjectReportSerializer as Report is an abstract model and ProjectReport is not defined as concrete.
# If concrete report models are created, then a serializer for them would be appropriate.


class ProjectListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for project lists (homepage, search, etc.)"""
    # Corrected: 'owner' (not user)
    # owner = UserSerializer(read_only=True) # Use a UserSerializer for owner details
    category = serializers.SerializerMethodField()
    pictures = serializers.SerializerMethodField()
    total_donations = serializers.SerializerMethodField() # Uses model @property
    percent_funded = serializers.SerializerMethodField() # Uses model @property
    average_rating = serializers.SerializerMethodField() # Uses model field
    donations_count = serializers.SerializerMethodField()
    # Removed 'is_featured' as it's not in the Project model

    class Meta:
        model = Project
        # Corrected fields based on actual Project model and properties
        fields = [
            'id', 'title', 'details', 'category', 'pictures',
            'total_target', 'total_donations', 'percent_funded', 'average_rating',
            'donations_count', 'owner', 'status',
            'start_time', 'end_time', 'created_at', 'updated_at'
        ]

    def get_category(self, obj):
        """Get category details - Removed slug as Category model does not have it"""
        if obj.category:
            return {'id': obj.category.id, 'name': obj.category.name}
        return None

    def get_pictures(self, obj):
        """Get project pictures - Corrected image URL access, removed non-existent fields"""
        pictures = obj.pictures.all().order_by('uploaded_at') # Order by uploaded_at, or add 'order' field
        request = self.context.get('request')
        return [
            {
                'id': pic.id,
                'image_url': request.build_absolute_uri(pic.image.url) if pic.image and request else None,
                # Removed 'is_main', 'order' as they are not on ProjectPicture model
            }
            for pic in pictures
        ]

    def get_total_donations(self, obj):
        """Get total donations amount from model property"""
        return obj.total_donations # Directly use the @property from Project model

    def get_average_rating(self, obj):
        """Get average rating from model field or calculate fallback"""
        # If 'average_rating' field is being updated in the model, use that.
        # Otherwise, if it's a calculated property, use obj.average_rating_calculated
        rating = obj.average_rating # Assuming average_rating field is updated
        if rating is not None:
            return round(rating, 1)
        # Fallback calculation if field is not updated or is None
        avg = obj.ratings.aggregate(avg_value=Avg('value'))['avg_value'] # Corrected Avg('value')
        return round(avg, 1) if avg else 0.0

    def get_percent_funded(self, obj):
        """Get percentage funded from model property"""
        return obj.percent_funded # Directly use the @property from Project model

    def get_donations_count(self, obj):
        """Get donations count"""
        return obj.donations.count() # Direct count on related manager

    def get_owner(self, obj): # Corrected name to 'get_owner'
        """Get project owner info - Removed profile_picture as it's not in default User model"""
        if obj.owner:
            return {
                'id': obj.owner.id,
                'username': obj.owner.username,
                'first_name': obj.owner.first_name,
                'last_name': obj.owner.last_name,
                # Removed 'profile_picture' as it's not in the default User model
            }
        return None


class ProjectDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single project view"""
    pictures = ProjectPictureSerializer(many=True, read_only=True)
    # owner = UserSerializer(read_only=True) # Corrected: 'owner' (not user)
    category = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    donations = DonationSerializer(many=True, read_only=True)
    ratings = RatingSerializer(many=True, read_only=True)

    # Calculated fields (using SerializerMethodField is fine for properties)
    total_donations = serializers.SerializerMethodField()
    percent_funded = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    donations_count = serializers.SerializerMethodField()
    ratings_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        # Use '__all__' and then remove unwanted fields, or specify fields explicitly
        # fields = '__all__' # Removed 'is_featured' and 'currency' as they are not in the model
        fields = [
            'id', 'title', 'details', 'total_target', 'owner', 'category', 'tags',
            'start_time', 'end_time', 'created_at', 'updated_at', 'status',
            'average_rating', 'rating_count', # These are direct model fields
            'pictures', # Nested serializer
            'donations', # Nested serializer
            'ratings', # Nested serializer
            # Calculated properties from the model
            'total_donations', 'percent_funded',
            'donations_count', 'ratings_count', # These are SerializerMethodFields
        ]


    def get_category(self, obj):
        """Get category details - Removed slug"""
        if obj.category:
            return {'id': obj.category.id, 'name': obj.category.name}
        return None

    def get_tags(self, obj):
        """Get tag details"""
        return [{'id': tag.id, 'name': tag.name} for tag in obj.tags.all()]

    def get_owner(self, obj): # Corrected name to 'get_owner'
        """Get project owner info - Removed profile_picture"""
        if obj.owner:
            return {
                'id': obj.owner.id,
                'username': obj.owner.username,
                'first_name': obj.owner.first_name,
                'last_name': obj.owner.last_name,
            }
        return None

    def get_total_donations(self, obj):
        """Get total donations amount from model property"""
        return obj.total_donations

    def get_percent_funded(self, obj):
        """Get percentage funded from model property"""
        return obj.percent_funded

    def get_average_rating(self, obj):
        """Get average rating from model field or property"""
        # Use the 'average_rating' field which is a float, or 'average_rating_calculated' property
        rating = obj.average_rating # Assuming this field is updated or directly contains the average
        if rating is not None:
            return round(rating, 1)
        # Fallback calculation if field is not set/updated
        avg = obj.ratings.aggregate(avg_value=Avg('value'))['avg_value']
        return round(avg, 1) if avg else 0.0

    def get_donations_count(self, obj):
        """Get donations count"""
        return obj.donations.count()

    def get_ratings_count(self, obj):
        """Get ratings count"""
        return obj.ratings.count()


class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating projects"""
    # owner is set automatically in create method, so not directly in fields for input
    # category and tags can be handled by their IDs
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, source='tags', write_only=True
    )

    class Meta:
        model = Project
        # Corrected fields based on actual Project model, removed non-existent 'is_featured', 'currency'
        fields = [
            'id', 'title', 'details', 'total_target',
            'start_time', 'end_time', 'status',
            'category_id', 'tag_ids', # For input
            # 'average_rating', 'rating_count' are managed by the system, not directly creatable/updatable via this form
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at', 'owner'] # Owner is set by view

    def validate_title(self, value):
        """Validate project title"""
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Title must be at least 5 characters long.")
        return value.strip()

    def validate_details(self, value):
        """Validate project description"""
        if len(value.strip()) < 100:
            raise serializers.ValidationError("Description must be at least 100 characters long.")
        return value.strip()

    def validate_total_target(self, value):
        """Validate funding goal"""
        if value < 100:
            raise serializers.ValidationError("Minimum funding goal is 100 EGP.")
        return value

    def validate(self, attrs):
        """Validate start and end times"""
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')

        if start_time and end_time:
            if end_time <= start_time:
                raise serializers.ValidationError({
                    'end_time': 'End date must be after start date.'
                })

            # Check minimum 7 days duration
            duration = end_time - start_time
            if duration.days < 7:
                raise serializers.ValidationError({
                    'end_time': 'Campaign must run for at least 7 days.'
                })

        return attrs

    def create(self, validated_data):
        """Auto-set owner and handle category/tags from IDs"""
        category = validated_data.pop('category', None)
        tags = validated_data.pop('tags', [])

        validated_data['owner'] = self.context['request'].user
        project = Project.objects.create(**validated_data)
        if category:
            project.category = category
        project.tags.set(tags) # Set many-to-many relationship
        project.save()
        return project

    def update(self, instance, validated_data):
        """Update project and handle category/tags from IDs"""
        category = validated_data.pop('category', None)
        tags = validated_data.pop('tags', [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if category:
            instance.category = category
        instance.tags.set(tags) # Set many-to-many relationship

        instance.save()
        return instance


# Serializer for Comments
class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    replies = serializers.SerializerMethodField() # To include nested replies

    class Meta:
        model = Comment
        fields = ['id', 'user', 'user_name', 'project', 'content', 'created_at', 'is_active', 'parent', 'replies']
        read_only_fields = ['user', 'project', 'created_at', 'is_active']

    def get_replies(self, obj):
        # Recursively serialize replies for this comment, only active ones
        active_replies = obj.replies.filter(is_active=True).order_by('created_at')
        # Avoid circular import by getting the serializer on demand
        return CommentSerializer(active_replies, many=True, read_only=True, context=self.context).data

    def create(self, validated_data):
        # Set user and project from context/view if not provided directly
        validated_data['user'] = self.context['request'].user
        # Project should be passed from the view when creating a comment (e.g., from URL pk)
        if 'project' not in validated_data:
            raise serializers.ValidationError("Project is required for a comment.")
        return super().create(validated_data)

