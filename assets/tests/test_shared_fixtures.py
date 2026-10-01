import pytest


@pytest.mark.django_db
def test_shared_asset_fixture_is_tenant_and_branch_scoped(asset, company, branch, regular_user):
    assert asset.company == company
    assert asset.branch == branch
    assert asset.assigned_to == regular_user
    assert regular_user.primary_branch == branch


@pytest.mark.django_db
def test_shared_transfer_fixture_uses_primary_branch_memberships(transfer, branch, branch2):
    assert transfer.from_branch == branch
    assert transfer.to_branch == branch2
    assert transfer.asset.company == transfer.company


@pytest.mark.django_db
def test_shared_permission_matrix_uses_singleton_contract(permission_matrix):
    assert permission_matrix.singleton == permission_matrix.SINGLETON_KEY
    assert permission_matrix.permissions
