from __future__ import annotations

from typing import Any, Dict, Optional

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from assets.models import Asset, AssetTransfer
from tenancy.models import Branch

User = get_user_model()


class InitiateTransferForm(forms.Form):
    asset_uuid = forms.UUIDField(required=False)
    asset_id = forms.IntegerField(required=False)
    to_user_id = forms.IntegerField(required=True)
    to_branch_id = forms.IntegerField(required=False)
    initiator_comment = forms.CharField(required=False, max_length=500)
    context = forms.JSONField(required=False)

    def __init__(self, *, user, company, data: Optional[Dict[str, Any]] = None):
        self.request_user = user
        self.company = company
        super().__init__(data=data)

    def clean(self):
        cleaned = super().clean()
        company_id = getattr(self.company, "id", None) or getattr(self.request_user, "company_id", None)
        if not company_id:
            raise ValidationError("Company context is required to initiate transfers.")

        asset = self._resolve_asset(cleaned)
        if asset.company_id != company_id:
            raise ValidationError("Asset does not belong to the current company.")

        to_user_id = cleaned.get("to_user_id")
        try:
            to_user = User.objects.get(pk=to_user_id)
        except (User.DoesNotExist, TypeError, ValueError) as exc:
            raise ValidationError("Recipient user not found.") from exc

        to_branch_id = cleaned.get("to_branch_id")
        to_branch: Optional[Branch] = None
        if to_branch_id not in (None, ""):
            try:
                to_branch = Branch.objects.get(pk=to_branch_id)
            except (Branch.DoesNotExist, TypeError, ValueError) as exc:
                raise ValidationError("Destination branch not found.") from exc

        if getattr(to_user, "company_id", company_id) != company_id:
            raise ValidationError("Recipient must belong to the same company as the asset.")

        if to_branch and to_branch.company_id != company_id:
            raise ValidationError("Destination branch must belong to the same company as the asset.")

        cleaned["asset"] = asset
        cleaned["to_user"] = to_user
        cleaned["to_branch"] = to_branch
        cleaned["company_id"] = company_id
        return cleaned

    def clean_context(self):
        context = self.cleaned_data.get("context")
        if context in (None, ""):
            return {}
        if not isinstance(context, dict):
            raise ValidationError("Context must be a JSON object.")
        return context

    def _resolve_asset(self, cleaned: Dict[str, Any]) -> Asset:
        asset_uuid = cleaned.get("asset_uuid")
        asset_id = cleaned.get("asset_id")
        asset: Optional[Asset] = None
        if asset_uuid:
            asset = Asset.objects.filter(uuid=asset_uuid).first()
        if asset is None and asset_id:
            asset = Asset.objects.filter(pk=asset_id).first()
        if asset is None:
            raise ValidationError("Asset could not be found with the supplied identifiers.")
        return asset

    def clean_to_user(self):  # pragma: no cover - guard for Django form internals
        return self.cleaned_data["to_user"]

    def clean_to_branch(self):  # pragma: no cover
        return self.cleaned_data["to_branch"]


class ReceiverDecisionForm(forms.Form):
    transfer_id = forms.IntegerField(required=True)
    decision = forms.ChoiceField(choices=AssetTransfer.Decision.choices)
    comment = forms.CharField(required=False, max_length=500)

    def __init__(self, *, user, data: Optional[Dict[str, Any]] = None):
        self.request_user = user
        super().__init__(data=data)

    def clean(self):
        cleaned = super().clean()
        transfer = self._resolve_transfer(cleaned.get("transfer_id"))
        if transfer.to_user_id != self.request_user.id:
            raise ValidationError("You are not the designated recipient for this transfer.")
        cleaned["transfer"] = transfer
        return cleaned

    def _resolve_transfer(self, transfer_id: Optional[int]) -> AssetTransfer:
        try:
            return AssetTransfer.objects.select_related("asset", "to_user").get(pk=transfer_id)
        except AssetTransfer.DoesNotExist as exc:
            raise ValidationError("Transfer not found.") from exc


class AdminReviewForm(forms.Form):
    transfer_id = forms.IntegerField(required=True)
    decision = forms.ChoiceField(choices=AssetTransfer.Decision.choices)
    comment = forms.CharField(required=False, max_length=500)

    def __init__(self, *, user, company, data: Optional[Dict[str, Any]] = None):
        self.request_user = user
        self.company = company
        super().__init__(data=data)

    def clean(self):
        cleaned = super().clean()
        company_id = getattr(self.company, "id", None) or getattr(self.request_user, "company_id", None)
        if not company_id:
            raise ValidationError("Company context is required for administrative review.")

        transfer = self._resolve_transfer(cleaned.get("transfer_id"))
        if transfer.company_id != company_id:
            raise ValidationError("Transfer does not belong to the current company.")

        cleaned["transfer"] = transfer
        cleaned["company_id"] = company_id
        return cleaned

    def _resolve_transfer(self, transfer_id: Optional[int]) -> AssetTransfer:
        try:
            return AssetTransfer.objects.select_related("asset", "to_user", "initiator").get(pk=transfer_id)
        except AssetTransfer.DoesNotExist as exc:
            raise ValidationError("Transfer not found.") from exc
