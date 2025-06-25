from django.urls import path
from . import views # Import all views functions and classes

app_name = 'projects'

urlpatterns = [
    path('', views.ProjectListView.as_view(), name='list'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='detail'),
    path('create/', views.ProjectCreateView.as_view(), name='create'), # Renamed from project-add for consistency
    path('<int:pk>/update/', views.ProjectUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='delete'),

    # Function-based views for form submissions
    # path('<int:pk>/comment/', views.add_comment, name='add_comment'),
    # path('<int:pk>/rate/', views.add_rating, name='add_rating'), # Renamed from 'rate' for clarity
    # path('<int:pk>/donate/', views.make_donation, name='make_donation'), # Renamed from 'donate' for clarity
]
