from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class HelpCenterView(LoginRequiredMixin, TemplateView):
    template_name = 'help/help_center.html'

class DocumentsView(LoginRequiredMixin, TemplateView):
    template_name = 'help/documents.html'