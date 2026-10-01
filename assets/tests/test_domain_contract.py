from django.test import SimpleTestCase

from assets.domain_contract import (
    ASSET_TRANSITIONS,
    IDENTIFIER_POLICY,
    OFFLINE_CONFLICT_POLICY,
    ROLE_PERMISSION_BASELINES,
    ROLE_SCOPES,
    AssetState,
    DataScope,
    Role,
    can_transition,
    validate_contract,
)


class DomainContractTests(SimpleTestCase):
    def test_contract_is_complete_and_consistent(self):
        validate_contract()
        self.assertEqual(set(ASSET_TRANSITIONS), set(AssetState))

    def test_registration_assignment_requires_acceptance(self):
        self.assertTrue(
            can_transition(AssetState.DRAFT, AssetState.PENDING_ACCEPTANCE)
        )
        self.assertTrue(
            can_transition(AssetState.PENDING_ACCEPTANCE, AssetState.ASSIGNED)
        )
        self.assertFalse(can_transition(AssetState.DRAFT, AssetState.ASSIGNED))

    def test_return_recovery_and_disposal_are_explicit(self):
        self.assertTrue(
            can_transition(AssetState.ASSIGNED, AssetState.INSPECTION_REQUIRED)
        )
        self.assertTrue(
            can_transition(AssetState.LOST, AssetState.INSPECTION_REQUIRED)
        )
        self.assertFalse(can_transition(AssetState.RETIRED, AssetState.DISPOSED))
        self.assertEqual(ASSET_TRANSITIONS[AssetState.DISPOSED], frozenset())

    def test_fixed_roles_have_fail_closed_scopes(self):
        self.assertEqual(ROLE_SCOPES[Role.ASSET_MANAGER], DataScope.TENANT)
        self.assertEqual(
            ROLE_SCOPES[Role.BRANCH_MANAGER], DataScope.ASSIGNED_BRANCHES
        )
        self.assertEqual(
            ROLE_SCOPES[Role.PLATFORM_SUPER_ADMIN],
            DataScope.PLATFORM_SUPPORT_SESSION,
        )
        self.assertEqual(
            ROLE_PERMISSION_BASELINES[Role.PLATFORM_SUPER_ADMIN], frozenset()
        )

    def test_identifier_and_offline_conflict_policies_are_safe(self):
        self.assertFalse(IDENTIFIER_POLICY["numeric_database_id_public"])
        self.assertEqual(
            IDENTIFIER_POLICY["asset_tag"],
            "unique_per_tenant_forever_when_present",
        )
        self.assertTrue(OFFLINE_CONFLICT_POLICY["server_is_source_of_truth"])
        self.assertTrue(
            OFFLINE_CONFLICT_POLICY["never_use_blind_last_write_wins"]
        )
