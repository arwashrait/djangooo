from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
# Ensure MultiPartParser for file uploads, FormParser for form data, JSONParser for JSON bodies
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q, Avg, Sum, Count # Import Count for annotations
from django.utils import timezone
from datetime import timedelta # Although not directly used in the provided code, good to have if needed for calculations

# Import your models
from .models import Project, Donation, Rating, ProjectPicture, Category, Tag # Removed Report and ProjectReport if they are abstract/non-existent concrete models

# Import your serializers
from .serializers import (
    ProjectListSerializer, ProjectDetailSerializer,
    ProjectCreateUpdateSerializer, DonationSerializer,
    RatingSerializer # Removed ProjectReportSerializer as it's not applicable with current models
)


class ProjectViewSet(viewsets.ModelViewSet):
    """Complete project management viewset"""
    # Allow different parsers for different request types (e.g., file uploads, JSON data)
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_serializer_class(self):
        """Returns the appropriate serializer class based on the action."""
        if self.action == 'list' or self.action == 'similar' or self.action == 'homepage_data':
            return ProjectListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProjectCreateUpdateSerializer
        return ProjectDetailSerializer

    def get_permissions(self):
        """Returns the list of permissions that the current request requires."""
        # Authenticated users can create, update, delete projects.
        # Anyone can view (list, retrieve, similar, homepage_data).
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'donate', 'rate', 'cancel']:
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        """
        Custom queryset to include related data and annotations for list and detail views.
        Filters for active projects.
        """
        # Optimized queryset for fetching related objects and annotating sums/averages
        queryset = Project.objects.select_related('category', 'owner').prefetch_related(
            'pictures', 'tags', 'donations', 'ratings'
        ).annotate(
            # Corrected: Sum of 'amount' from Donation model
            total_donations_annotated=Sum('donations__amount'),
            # Corrected: Average of 'value' from Rating model
            average_rating_annotated=Avg('ratings__value'),
            donations_count_annotated=Count('donations')
        ).filter(status='active') # Corrected: Filter by 'status' field

        # Apply search filters based on query parameters
        search = self.request.query_params.get('search')
        category_name = self.request.query_params.get('category') # Changed from 'category' to 'category_name' for clarity
        title = self.request.query_params.get('title')
        tags_param = self.request.query_params.get('tags') # Changed from 'tags' to 'tags_param' for clarity
        min_target = self.request.query_params.get('min_target')
        max_target = self.request.query_params.get('max_target')

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(details__icontains=search) |
                Q(tags__name__icontains=search) # Ensure tag name search works
            ).distinct()

        if title:
            queryset = queryset.filter(title__icontains=title)

        if tags_param:
            tag_list = [tag.strip() for tag in tags_param.split(',') if tag.strip()]
            if tag_list:
                queryset = queryset.filter(tags__name__in=tag_list).distinct()

        if category_name:
            try:
                # Corrected: Filter by category name (as Category model has 'name', not 'slug')
                category_obj = Category.objects.get(name__iexact=category_name)
                queryset = queryset.filter(category=category_obj)
            except Category.DoesNotExist:
                # If category doesn't exist, return empty queryset or no filter
                queryset = queryset.none() # Or simply pass to not filter by category

        if min_target:
            try:
                min_target = float(min_target)
                queryset = queryset.filter(total_target__gte=min_target)
            except ValueError:
                pass # Handle invalid input gracefully

        if max_target:
            try:
                max_target = float(max_target)
                queryset = queryset.filter(total_target__lte=max_target)
            except ValueError:
                pass # Handle invalid input gracefully
        
        # Order by creation date to prevent UnorderedObjectListWarning if not explicitly ordered
        queryset = queryset.order_by('-created_at')

        return queryset

    def create(self, request, *args, **kwargs):
        """Enhanced project creation with images and tags handling"""
        # The serializer should now handle category_id and tag_ids directly
        # and set the owner from the context.
        serializer = ProjectCreateUpdateSerializer(data=request.data, context={'request': request})

        if serializer.is_valid(raise_exception=True): # raise_exception will return 400 automatically
            project = serializer.save() # This will call ProjectCreateUpdateSerializer.create()

            # Handle images (assuming 'image_0', 'image_1' etc. in request.FILES)
            # The ProjectPicture model now only has 'image' field
            images_to_process = []
            for key, file in request.FILES.items():
                if key.startswith('image_'): # Adjust prefix if needed
                    images_to_process.append(file)

            for image_file in images_to_process:
                ProjectPicture.objects.create(
                    project=project,
                    image=image_file,
                    # Removed 'is_main' and 'order' as they are not in your ProjectPicture model
                )

            # Return created project with full details using ProjectDetailSerializer
            response_serializer = ProjectDetailSerializer(project, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        # No need for explicit else branch here if raise_exception=True


    def update(self, request, *args, **kwargs):
        """Enhanced project update with tags handling"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = ProjectCreateUpdateSerializer(instance, data=request.data, partial=partial, context={'request': request})

        if serializer.is_valid(raise_exception=True):
            project = serializer.save() # This will call ProjectCreateUpdateSerializer.update()
            # Image updates would require more complex logic (e.g., deleting old, adding new)
            # which is outside the scope of simple serializer.save()

            response_serializer = ProjectDetailSerializer(project, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_200_OK)


    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def donate(self, request, pk=None):
        """Handle project donations"""
        project = self.get_object()
        amount = request.data.get('amount')

        if not amount:
            return Response(
                {'error': 'Donation amount is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amount = float(amount)
            if amount <= 0:
                return Response(
                    {'error': 'Donation amount must be greater than 0'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid donation amount'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if campaign is still active (using project status and end_time)
        if project.status != 'active' or project.end_time < timezone.now():
            return Response(
                {'error': 'Campaign is not active or has ended'},
                status=status.HTTP_400_BAD_REQUEST
            )

        donation = Donation.objects.create(
            project=project,
            user=request.user, # Corrected: 'user' field in Donation model
            amount=amount
        )
        
        # Optional: Update project's current_fund field if you're caching it
        # project.current_fund += amount # This would require Project model to have current_fund field updated by signals
        # project.save()

        serializer = DonationSerializer(donation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rate(self, request, pk=None):
        """Handle project ratings"""
        project = self.get_object()
        rating_value = request.data.get('value') # Corrected: Expect 'value' from serializer/frontend

        if not rating_value:
            return Response(
                {'error': 'Rating value is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            rating_value = int(rating_value)
            if not (1 <= rating_value <= 5):
                return Response(
                    {'error': 'Rating must be between 1 and 5'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid rating value'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rating, created = Rating.objects.update_or_create(
            project=project,
            user=request.user,
            defaults={'value': rating_value} # Corrected: 'value' field in Rating model
        )

        # Optional: Update project's average_rating and rating_count fields if you're caching them
        # project.update_average_rating() # You would need to implement this method in your Project model
        # project.save()

        serializer = RatingSerializer(rating)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """Cancel project if less than 25% funded (PDF requirement)"""
        project = self.get_object()

        if project.owner != request.user:
            return Response(
                {'error': 'Only project owner can cancel'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if project is already canceled or completed
        if project.status != 'active':
            return Response(
                {'error': f'Project is already {project.status}. Cannot cancel.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Use the @property for calculations
        if project.percent_funded >= 25: # Check against the property
            return Response(
                {'error': 'Cannot cancel project with 25% or more funding'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set project status to 'canceled'
        project.status = 'canceled' # Corrected: Use 'status' field
        project.save()

        # TODO: Implement actual refund logic here! This is CRITICAL for a real application.
        # This would typically involve iterating through donations and processing refunds.

        return Response({'message': 'Project cancelled successfully'}, status=status.HTTP_200_OK)

    # @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    # def report(self, request, pk=None):
    #     """
    #     Report inappropriate project.
    #     Note: This action is commented out because the 'Report' model is abstract,
    #     and 'ProjectReport' is not defined as a concrete model in your models.py.
    #     To use this, you need a concrete 'ProjectReport' model that inherits from 'Report'.
    #     """
    #     return Response(
    #         {'error': 'Reporting functionality is currently unavailable (model not defined).'},
    #         status=status.HTTP_501_NOT_IMPLEMENTED # Use 501 if feature not implemented
    #     )


    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def similar(self, request, pk=None):
        """Get similar projects based on tags (PDF requirement: 4 similar projects)"""
        project = self.get_object()

        # Get projects with similar tags, exclude the current project, and filter by active status
        similar_projects = Project.objects.filter(
            tags__in=project.tags.all(),
            status='active' # Corrected: filter by 'status'
        ).exclude(id=project.id).annotate(
            total_donations_annotated=Sum('donations__amount'),
            average_rating_annotated=Avg('ratings__value') # Corrected: Avg('value')
        ).distinct().order_by('-created_at')[:4] # Added ordering for consistent results

        serializer = ProjectListSerializer(similar_projects, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def homepage_data(self, request):
        """Get homepage data (PDF requirements: top 5 rated, latest 5, featured 5)"""
        # Annotate queryset once to avoid repetitive calculations
        base_queryset = Project.objects.filter(status='active').annotate(
            total_donations_annotated=Sum('donations__amount'),
            average_rating_annotated=Avg('ratings__value') # Corrected: Avg('value')
        )

        # Top 5 rated projects (filter for non-null average ratings)
        # Using the annotated 'average_rating_annotated'
        top_rated = base_queryset.filter(average_rating_annotated__isnull=False).order_by('-average_rating_annotated')[:5]

        # Latest 5 projects
        latest = base_queryset.order_by('-created_at')[:5]

        # Featured 5 projects (NOTE: Project model does NOT have 'is_featured' field.
        # This filter will cause an error unless you add 'is_featured' to your Project model.)
        # As 'is_featured' is not in your current models, this filter is commented out.
        # You would need to add `is_featured = models.BooleanField(default=False)` to Project model.
        featured = base_queryset.filter(status='active').order_by('-created_at')[:5] # Placeholder, remove is_featured filter

        return Response({
            'top_rated': ProjectListSerializer(top_rated, many=True, context={'request': request}).data,
            'latest': ProjectListSerializer(latest, many=True, context={'request': request}).data,
            'featured': ProjectListSerializer(featured, many=True, context={'request': request}).data,
        }, status=status.HTTP_200_OK)

