from django.urls import path
from . import views
from .views import (
    ProjectListView, ProjectDetailView,
    ProjectCreateView, ProjectUpdateView,
    add_comment, add_rating, make_donation
)
app_name = 'projects' 

urlpatterns = [
    # path('',views.home ),
    # path('', ProjectListView.as_view(), name='project-list'),
    # path('<int:pk>/', ProjectDetailView.as_view(), name='project-detail'),
    # path('create/', ProjectCreateView.as_view(), name='project-create'),
    # path('<int:pk>/update/', ProjectUpdateView.as_view(), name='project-update'),
    # path('<int:pk>/comment/', add_comment, name='add-comment'),
    # path('<int:pk>/rate/', add_rating, name='add-rating'),
    # path('<int:pk>/donate/', make_donation, name='make-donation'),
    #     path('add/', views.create_project_view, name='project-add'),
        path('', views.ProjectListView.as_view(), name='list'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='detail'),
    path('create/', views.ProjectCreateView.as_view(), name='project-add'), # Mapped from previous discussion
    path('<int:pk>/update/', views.ProjectUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='delete'), # <--- CONFIRM THIS LINE IS EXACT
    path('<int:pk>/comment/', views.add_comment, name='add_comment'),
    path('<int:pk>/rate/', views.add_rating, name='rate'),
    path('<int:pk>/donate/', views.make_donation, name='donate'),

]
