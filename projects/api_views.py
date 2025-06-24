from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q, Avg, Sum, Count # Import Count for annotations
from django.utils import timezone
from datetime import timedelta # Good to have for time calculations

# Import all necessary models from the current app
from .models import (
    Project, Donation, Rating, ProjectPicture, Category, Tag,
    Comment, ProjectReport, CommentReport # Include new report models
)

# Import your serializers
from .serializers import (
    ProjectListSerializer, ProjectDetailSerializer,
    ProjectCreateUpdateSerializer, DonationSerializer,
    RatingSerializer, CommentSerializer,
    ProjectReportSerializer, CommentReportSerializer # Include new report serializers
)


class ProjectViewSet(viewsets.ModelViewSet):
    """Complete project management viewset"""
    parser_classes = (MultiPartParser, FormParser, JSONParser) # Handle file uploads and JSON

    def get_serializer_class(self):
        """Returns the appropriate serializer class based on the action."""
        if self.action in ['list', 'similar', 'homepage_data']:
            return ProjectListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProjectCreateUpdateSerializer
        elif self.action == 'donate':
            return DonationSerializer
        elif self.action == 'rate':
            return RatingSerializer
        elif self.action == 'comment':
            return CommentSerializer
        elif self.action == 'report_project':
            return ProjectReportSerializer
        elif self.action == 'report_comment': # Action for reporting comments
            return CommentReportSerializer
        return ProjectDetailSerializer # Default to detail serializer

    def get_permissions(self):
        """Returns the list of permissions that the current request requires."""
        # Authenticated users can create, update, delete projects, and perform actions like donate, rate, cancel, report.
        # Anyone can view (list, retrieve, similar, homepage_data).
        if self.action in ['create', 'update', 'partial_update', 'destroy',
                           'donate', 'rate', 'cancel', 'report_project', 'report_comment']:
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        """
        Custom queryset for Project objects, optimized with select_related and prefetch_related
        for performance and annotated for aggregated data.
        Filters for active projects by default.
        """
        # Annotate total donations, average rating, and donations count for performance
        queryset = Project.objects.select_related('category', 'owner').prefetch_related(
            'pictures', 'tags', 'donations', 'ratings', 'comments', 'project_reports' # Added comments, project_reports
        ).annotate(
            total_donations_annotated=Sum('donations__amount'),
            average_rating_annotated=Avg('ratings__value'), # Corrected: 'value' field in Rating model
            donations_count_annotated=Count('donations')
        ).filter(status='active') # Filter for active campaigns

        # Apply search and filter parameters from the request
        search = self.request.query_params.get('search')
        category_name = self.request.query_params.get('category')
        title = self.request.query_params.get('title')
        tags_param = self.request.query_params.get('tags')
        min_target = self.request.query_params.get('min_target')
        max_target = self.request.query_params.get('max_target')
        is_featured = self.request.query_params.get('is_featured')

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(details__icontains=search) |
                Q(tags__name__icontains=search) # Search across tags
            ).distinct() # Use distinct to avoid duplicate projects if they have multiple matching tags

        if title:
            queryset = queryset.filter(title__icontains=title)

        if tags_param:
            tag_list = [tag.strip() for tag in tags_param.split(',') if tag.strip()]
            if tag_list:
                queryset = queryset.filter(tags__name__in=tag_list).distinct()

        if category_name:
            try:
                # Filter by category name (case-insensitive)
                category_obj = Category.objects.get(name__iexact=category_name)
                queryset = queryset.filter(category=category_obj)
            except Category.DoesNotExist:
                queryset = queryset.none() # Return empty if category not found

        if min_target:
            try:
                min_target = float(min_target)
                queryset = queryset.filter(total_target__gte=min_target)
            except ValueError:
                pass

        if max_target:
            try:
                max_target = float(max_target)
                queryset = queryset.filter(total_target__lte=max_target)
            except ValueError:
                pass

        if is_featured: # Only filter if is_featured parameter is provided
            is_featured = is_featured.lower() == 'true'
            queryset = queryset.filter(is_featured=is_featured)

        # Order by creation date to ensure consistent pagination and results
        queryset = queryset.order_by('-created_at')

        return queryset

    def create(self, request, *args, **kwargs):
        """Handle project creation, including image uploads and tag/category association."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        project = serializer.save() # Project is created here, with owner, category, tags from serializer

        # Handle multiple image uploads for the project
        images_to_process = []
        for key, file in request.FILES.items():
            if key.startswith('image_'): # Assuming image fields are named image_0, image_1, etc.
                images_to_process.append(file)

        for image_file in images_to_process:
            ProjectPicture.objects.create(
                project=project,
                image=image_file,
                # ProjectPicture model does not have 'is_main' or 'order' fields
            )

        # Return the newly created project with full details
        response_serializer = ProjectDetailSerializer(project, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Handle project updates."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Ensure only the owner can update the project
        if instance.owner != request.user:
            return Response(
                {'error': 'You do not have permission to update this project.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        project = serializer.save()

        # Handle image updates if implemented (e.g., delete existing, add new ones)
        # This part requires more complex logic and is not included here by default
        # as it depends on how the frontend sends image updates (e.g., new uploads, deletions)

        response_serializer = ProjectDetailSerializer(project, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """Handle project deletion."""
        instance = self.get_object()
        # Ensure only the owner can delete the project
        if instance.owner != request.user:
            return Response(
                {'error': 'You do not have permission to delete this project.'},
                status=status.HTTP_403_FORBIDDEN
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def donate(self, request, pk=None):
        """Handle project donations."""
        project = self.get_object()
        amount = request.data.get('amount')

        if not amount:
            return Response({'error': 'Donation amount is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = float(amount)
            if amount <= 0:
                return Response({'error': 'Donation amount must be greater than 0'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid donation amount'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if campaign is active and not ended
        if not project.is_active_campaign:
            return Response(
                {'error': f'Campaign is not active or has ended. Current status: {project.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the donation
        donation = Donation.objects.create(
            project=project,
            user=request.user, # Corrected: 'user' field in Donation model
            amount=amount
        )
        
        # Optionally, you can trigger an update to project's total_donations_collected here if it's cached
        # project.total_donations_collected = project.donations.aggregate(Sum('amount'))['amount__sum'] or 0
        # project.save(update_fields=['total_donations_collected']) # If you add this field to Project model

        serializer = DonationSerializer(donation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rate(self, request, pk=None):
        """Handle project ratings (create or update)."""
        project = self.get_object()
        rating_value = request.data.get('value') # Expect 'value' as per Rating model and serializer

        if not rating_value:
            return Response({'error': 'Rating value is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rating_value = int(rating_value)
            if not (1 <= rating_value <= 5):
                return Response({'error': 'Rating must be between 1 and 5'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid rating value'}, status=status.HTTP_400_BAD_REQUEST)

        # Update or create the rating for the user on this project
        rating, created = Rating.objects.update_or_create(
            project=project,
            user=request.user,
            defaults={'value': rating_value} # Corrected: 'value' field in Rating model
        )

        # Update cached average rating on the project
        project.update_rating_summary() # Call the method on the Project model

        serializer = RatingSerializer(rating)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """Allow project creator to cancel the project if donations are less than 25%."""
        project = self.get_object()

        # Check permission: Only owner can cancel
        if project.owner != request.user:
            return Response(
                {'error': 'You do not have permission to cancel this project.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if project is already canceled or completed
        if project.status != 'active':
            return Response(
                {'error': f'Project is already {project.status}. Cannot cancel.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check funding threshold using the model's percent_funded property
        if project.percent_funded >= 25:
            return Response(
                {'error': 'Cannot cancel project with 25% or more funding.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update project status to 'canceled'
        project.status = 'canceled'
        project.save(update_fields=['status']) # Save only the updated status field

        # TODO: Implement actual refund logic here (this is critical for production)
        # This would typically involve iterating through donations and processing refunds.

        return Response({'message': 'Project cancelled successfully.'}, status=status.HTTP_200_OK)


    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def comment(self, request, pk=None):
        """Add a comment to a project or reply to an existing comment."""
        project = self.get_object() # The project being commented on
        
        # If 'parent' ID is provided in request, it's a reply
        parent_id = request.data.get('parent_id')
        parent_comment = None
        if parent_id:
            try:
                parent_comment = Comment.objects.get(id=parent_id, project=project)
            except Comment.DoesNotExist:
                return Response({'error': 'Parent comment not found.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CommentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            # Pass project and parent_comment to the serializer's create method
            serializer.save(project=project, parent=parent_comment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        # No else branch needed due to raise_exception=True


    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def report_project(self, request, pk=None):
        """Report an inappropriate project."""
        project = self.get_object() # The project being reported

        # Check if user already reported this project
        if ProjectReport.objects.filter(project=project, reporter=request.user).exists():
            return Response(
                {'error': 'You have already reported this project.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ProjectReportSerializer(data=request.data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            serializer.save(project=project) # Save with the project instance
            return Response(
                {'message': 'Project reported successfully. It will be reviewed by admins.'},
                status=status.HTTP_201_CREATED
            )
        # No else branch needed due to raise_exception=True


    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def report_comment(self, request, pk=None):
        """Report an inappropriate comment."""
        # 'pk' here refers to the Project ID. We need the Comment ID from the request body.
        project = self.get_object() # Get the project to ensure comment belongs to it
        comment_id = request.data.get('comment_id')

        if not comment_id:
            return Response(
                {'error': 'Comment ID is required to report a comment.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            comment_to_report = Comment.objects.get(id=comment_id, project=project)
        except Comment.DoesNotExist:
            return Response(
                {'error': 'Comment not found or does not belong to this project.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user already reported this comment
        if CommentReport.objects.filter(comment=comment_to_report, reporter=request.user).exists():
            return Response(
                {'error': 'You have already reported this comment.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CommentReportSerializer(data=request.data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            serializer.save(comment=comment_to_report) # Save with the comment instance
            return Response(
                {'message': 'Comment reported successfully. It will be reviewed by admins.'},
                status=status.HTTP_201_CREATED
            )
        # No else branch needed due to raise_exception=True


    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def similar(self, request, pk=None):
        """Get similar projects based on tags (up to 4 similar projects)."""
        project = self.get_object()

        # Get projects with at least one common tag, exclude current project, and filter by active status
        similar_projects = Project.objects.filter(
            tags__in=project.tags.all(),
            status='active'
        ).exclude(id=project.id).annotate(
            total_donations_annotated=Sum('donations__amount'),
            average_rating_annotated=Avg('ratings__value')
        ).distinct().order_by('-created_at')[:4] # Order for consistent results and limit to 4

        serializer = ProjectListSerializer(similar_projects, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def homepage_data(self, request):
        """Get homepage data: top 5 rated, latest 5, featured 5 projects."""
        # Base queryset for active projects with common annotations
        base_queryset = Project.objects.filter(status='active').annotate(
            total_donations_annotated=Sum('donations__amount'),
            average_rating_annotated=Avg('ratings__value'),
            donations_count_annotated=Count('donations') # Added for consistency, though not strictly used in default serializer
        )

        # Top 5 rated projects (filter for projects that have been rated)
        top_rated = base_queryset.filter(average_rating_annotated__isnull=False).order_by('-average_rating_annotated')[:5]

        # Latest 5 projects
        latest = base_queryset.order_by('-created_at')[:5]

        # Featured 5 projects (using the new `is_featured` field)
        featured = base_queryset.filter(is_featured=True).order_by('-created_at')[:5]

        return Response({
            'top_rated': ProjectListSerializer(top_rated, many=True, context={'request': request}).data,
            'latest': ProjectListSerializer(latest, many=True, context={'request': request}).data,
            'featured': ProjectListSerializer(featured, many=True, context={'request': request}).data,
        }, status=status.HTTP_200_OK)

