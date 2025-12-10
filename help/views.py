from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class HelpCenterView(LoginRequiredMixin, TemplateView):
    """
    World-Class Help Center View
    
    Provides comprehensive documentation and help resources for users.
    Matches the design of Assets and Maintenance pages.
    
    Features:
    - Search functionality
    - Categorized help topics
    - Role-based guides
    - Quick links
    - Responsive design
    
    URL: /help/
    Template: help/help_center_worldclass.html
    """
    template_name = 'help/help_center_worldclass.html'

class DocumentsView(LoginRequiredMixin, TemplateView):
    template_name = 'help/documents.html'