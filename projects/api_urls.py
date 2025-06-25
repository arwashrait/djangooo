

from django.urls import path
# Import your ProjectViewSet and other necessary API views
from .api_views import ProjectViewSet

# Define app_name for namespacing (optional but good practice)
app_name = 'projects_api' # Using a different app_name to avoid conflict with web urls

urlpatterns = [
    # List and Create Projects (GET, POST)
    path('', ProjectViewSet.as_view({'get': 'list', 'post': 'create'}), name='project-list-create'),
    path('homepage_data/', ProjectViewSet.as_view({'get': 'homepage_data'}), name='project-homepage-data'),


    # Retrieve, Update, Delete Projects (GET, PUT, PATCH, DELETE)
    path('<int:pk>/', ProjectViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='project-detail'),

    path('<int:pk>/donate/', ProjectViewSet.as_view({'post': 'donate'}), name='project-donate'),
    path('<int:pk>/rate/', ProjectViewSet.as_view({'post': 'rate'}), name='project-rate'),
    path('<int:pk>/cancel/', ProjectViewSet.as_view({'post': 'cancel'}), name='project-cancel'),
    path('<int:pk>/comment/', ProjectViewSet.as_view({'post': 'comment'}), name='project-comment'),
    path('<int:pk>/report_project/', ProjectViewSet.as_view({'post': 'report_project'}), name='project-report-project'),
    path('<int:pk>/similar/', ProjectViewSet.as_view({'get': 'similar'}), name='project-similar'),


    
    path('<int:pk>/report_comment/', ProjectViewSet.as_view({'post': 'report_comment'}), name='project-report-comment'),

]
