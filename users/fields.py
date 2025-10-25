"""
Custom form fields for user selection with enhanced display.

This module provides custom ModelChoiceField implementations that display
users with additional context like branch and company information.
"""
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class UserWithBranchChoiceField(forms.ModelChoiceField):
    """
    Custom ModelChoiceField that displays users with their primary branch.
    
    Display Format: username (role) - Branch Name @ Company
    
    Example:
        john_doe (admin) - Head Office @ TechCorp
        jane_smith (manager) - New York Branch @ TechCorp
        bob_wilson (user) - Los Angeles Branch @ TechCorp
    
    Usage:
        from users.fields import UserWithBranchChoiceField
        
        class MyForm(forms.Form):
            assigned_to = UserWithBranchChoiceField(
                queryset=User.objects.filter(company=company).prefetch_related('user_branches__branch'),
                required=False,
                empty_label="-- Not Assigned --"
            )
    
    Important:
        Ensure the queryset uses prefetch_related('user_branches__branch')
        to avoid N+1 query problems when rendering the dropdown.
    
    Inspired by:
        - ServiceNow ITAM: Shows user with location
        - IBM Maximo: Shows user with site information
        - SAP EAM: Shows user with plant/location
    """
    
    def label_from_instance(self, obj):
        """
        Customize the display label for each user option.
        
        This method is called by Django for each option in the dropdown.
        It allows us to customize how users are displayed without modifying
        the User model's __str__() method.
        
        Args:
            obj (User): User instance to display
            
        Returns:
            str: Formatted label with username, role, branch, and company
            
        Format:
            - With branch: "username (role) - Branch Name @ Company"
            - Without branch: "username (role) @ Company"
            - Without company: "username (role)"
        """
        # Get primary branch (should be prefetched to avoid N+1 queries)
        try:
            primary_branch = obj.primary_branch
            branch_label = f" - {primary_branch.name}" if primary_branch else ""
        except Exception:
            # Graceful fallback if branch access fails
            branch_label = ""
        
        # Get company name
        try:
            company_label = f" @ {obj.company.name}" if obj.company else ""
        except Exception:
            # Graceful fallback if company access fails
            company_label = ""
        
        # Format: username (role) - Branch @ Company
        return f"{obj.username} ({obj.role}){branch_label}{company_label}"
