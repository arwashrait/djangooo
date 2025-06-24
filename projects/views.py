from django.views.generic.edit import DeleteView
from django.urls import reverse_lazy, reverse # Import reverse as well
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render # Ensure render is imported if you use it for templates
from django.contrib import messages
from django.forms import inlineformset_factory

from .models import Project, ProjectPicture, Comment, Rating, Donation
from .forms import ProjectForm, CommentForm, RatingForm, DonationForm


# Inline Formset for Project Pictures
# This allows pictures to be uploaded when creating/updating a project via the web form
ProjectPictureFormSet = inlineformset_factory(
    Project, ProjectPicture,
    fields=('image',), # Only 'image' field is present in ProjectPicture model
    extra=1, # Number of empty forms to display
    can_delete=True
)

class ProjectListView(ListView):
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    paginate_by = 10
    # Optional: Add an ordering to prevent UnorderedObjectListWarning if not already handled
    # queryset = Project.objects.all().order_by('-created_at')


class ProjectDetailView(DetailView):
    model = Project
    template_name = 'projects/project_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass forms for comments, ratings, and donations to the template
        context['comment_form'] = CommentForm()
        context['rating_form'] = RatingForm()
        context['donation_form'] = DonationForm()
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html' # This template should contain formset handling

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['formset'] = ProjectPictureFormSet(self.request.POST, self.request.FILES)
        else:
            data['formset'] = ProjectPictureFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        # Assign the current user as the owner before saving the project
        self.object = form.save(commit=False)
        self.object.owner = self.request.user
        self.object.save() # Save the project instance

        # Now save the formset instances, linking them to the newly created project
        if formset.is_valid():
            formset.instance = self.object # Link formset to the saved project
            formset.save() # Save ProjectPicture instances
            messages.success(self.request, "Project and pictures created successfully!")
            return redirect(self.get_success_url())
        else:
            # If formset is invalid, render the form again with errors
            # Need to re-attach the project instance to the formset for re-rendering
            formset = ProjectPictureFormSet(self.request.POST, self.request.FILES, instance=self.object)
            context['formset'] = formset
            return self.form_invalid(form) # Render form again with errors

    def get_success_url(self):
        # Redirect to the detail page of the newly created project
        return reverse('projects:detail', kwargs={'pk': self.object.pk})


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
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

        # Save the project form first
        self.object = form.save()

        # Save the inline formset instances
        if formset.is_valid():
            formset.instance = self.object
            formset.save()
            messages.success(self.request, "Project and pictures updated successfully!")
            return redirect(self.get_success_url())
        else:
            # If formset is invalid, re-render with errors
            formset = ProjectPictureFormSet(self.request.POST, self.request.FILES, instance=self.object)
            context['formset'] = formset
            return self.form_invalid(form) # Render form again with errors


    def dispatch(self, request, *args, **kwargs):
        # Ensure only the project owner can update their project
        project = self.get_object()
        if project.owner != request.user:
            messages.error(request, "You can only edit your own projects.")
            return redirect('projects:detail', pk=project.pk) # Use correct reverse name
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('projects:detail', kwargs={'pk': self.object.pk})


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'projects/project_confirm_delete.html' # You need to create this template
    success_url = reverse_lazy('projects:list')

    def dispatch(self, request, *args, **kwargs):
        # Ensure only the project owner can delete their project
        project = self.get_object()
        if project.owner != request.user:
            messages.error(request, "You can only delete your own projects.")
            return redirect('projects:detail', pk=project.pk) # Use correct reverse name
        return super().dispatch(request, *args, **kwargs)


def add_comment(request, pk):
    """Function-based view to add a comment or reply to a project."""
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.project = project
            
            # Handle replies
            parent_id = form.cleaned_data.get('parent_id')
            if parent_id:
                try:
                    parent_comment = Comment.objects.get(id=parent_id, project=project)
                    comment.parent = parent_comment
                except Comment.DoesNotExist:
                    messages.error(request, "Parent comment not found.")
                    return redirect('projects:detail', pk=pk)

            comment.save()
            messages.success(request, "Comment added successfully!")
        else:
            messages.error(request, "Error adding comment. Please check your input.")
    return redirect('projects:detail', pk=pk)


def add_rating(request, pk):
    """Function-based view to add or update a project rating."""
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            rating, created = Rating.objects.update_or_create(
                user=request.user,
                project=project,
                defaults={'value': form.cleaned_data['value']}
            )
            # Update the cached average rating on the Project model
            project.update_rating_summary()
            messages.success(request, "Rating submitted successfully!")
        else:
            messages.error(request, "Error submitting rating. Please check your input.")
    return redirect('projects:detail', pk=pk)


def make_donation(request, pk):
    """Function-based view to handle project donations."""
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = DonationForm(request.POST)
        if form.is_valid():
            donation = form.save(commit=False)
            donation.user = request.user
            donation.project = project
            donation.save()
            messages.success(request, f"Thank you for your donation of {donation.amount} EGP!")
            # Optional: Update total donations cache on Project model if you add it.
            # project.update_total_donations_cache()
        else:
            messages.error(request, "Error processing donation. Please check your amount.")
    return redirect('projects:detail', pk=pk)

