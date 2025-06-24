# from django.shortcuts import render
# from django.http import HttpResponse
# Create your views here.


# def home (request):
#     return HttpResponse('home pageee')

from django.views.generic.edit import DeleteView
from django.urls import reverse_lazy # For redirecting after success
# projects/views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from .models import *
from .forms import ProjectForm, CommentForm, RatingForm, DonationForm

class ProjectListView(ListView):
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    paginate_by = 10

class ProjectDetailView(DetailView):
    model = Project
    template_name = 'projects/project_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_form'] = CommentForm()
        context['rating_form'] = RatingForm()
        context['donation_form'] = DonationForm()
        return context

class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    
    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Project created successfully!")
        return response

class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Ensure only owner can update
        if self.get_object().owner != request.user:
            messages.error(request, "You can only edit your own projects")
            return redirect('project-detail', pk=self.get_object().pk)
        return super().dispatch(request, *args, **kwargs)

def add_comment(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.project = project
            comment.save()
            messages.success(request, "Comment added!")
    return redirect('project-detail', pk=pk)

def add_rating(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            rating, created = Rating.objects.update_or_create(
                user=request.user,
                project=project,
                defaults={'value': form.cleaned_data['value']}
            )
            messages.success(request, "Rating submitted!")
    return redirect('project-detail', pk=pk)

def make_donation(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = DonationForm(request.POST)
        if form.is_valid():
            donation = form.save(commit=False)
            donation.user = request.user
            donation.project = project
            donation.save()
            messages.success(request, f"Thank you for your donation of {donation.amount} EGP!")
    return redirect('project-detail', pk=pk)


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'projects/project_confirm_delete.html' # Create this template
    success_url = reverse_lazy('projects:list')

    def dispatch(self, request, *args, **kwargs):
        if self.get_object().owner != request.user:
            messages.error(request, "You can only delete your own projects")
            return redirect('projects:detail', pk=self.get_object().pk)
        return super().dispatch(request, *args, **kwargs)

from django.forms import inlineformset_factory
# ... other imports ...

ProjectPictureFormSet = inlineformset_factory(Project,ProjectPicture, fields=('image', 'project'), extra=1, can_delete=True)

class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['formset'] = ProjectPictureFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            data['formset'] = ProjectPictureFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        if formset.is_valid():
            self.object = form.save(commit=False)
            self.object.owner = self.request.user
            self.object.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, "Project created successfully!")
            return redirect(self.get_success_url()) # Use get_success_url for consistency
        else:
            return self.form_invalid(form) # Render form again with errors

    def get_success_url(self):
        return reverse('projects:detail', kwargs={'pk': self.object.pk}) # Redirect to detail page
    