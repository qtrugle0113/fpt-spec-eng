"""T017 domain expectations for T031; no DB connection or fake state machine.

Test-first interface: authorizations.transition_authorization(state, event,
scope=..., commit_verified=False, terminal_verified=False,
retry_possible=False, commit_unknown=False) -> state string; illegal -> ValueError.
This is a proposed internal seam, not a change to public API/Data Model.
"""

import importlib
import unittest


def authorization_module():
    try:
        return importlib.import_module('aat_metadata.repositories.authorizations')
    except ModuleNotFoundError as exc:
        if exc.name not in {'aat_metadata.repositories', 'aat_metadata.repositories.authorizations'}:
            raise
        raise AssertionError('T031 authorization repository/state implementation is missing') from None


class AuthorizationStateTests(unittest.TestCase):
    def transition(self, state, event, **context):
        module = authorization_module()
        self.assertTrue(hasattr(module, 'transition_authorization'), 'T031 pure transition seam missing')
        return module.transition_authorization(state, event, **context)

    def test_once_reserves_and_safe_extraction_retry_keeps_reservation(self):
        self.assertEqual(self.transition('GRANTED', 'reserve', scope='ONCE'), 'RESERVED')
        self.assertEqual(self.transition('RESERVED', 'extraction_retry', scope='ONCE'), 'RESERVED')

    def test_reserved_once_never_returns_to_granted(self):
        for event in ('release', 'reset', 'reserve'):
            with self.subTest(event=event), self.assertRaises(ValueError):
                self.transition('RESERVED', event, scope='ONCE')

    def test_only_verified_commit_consumes_once(self):
        self.assertEqual(self.transition('RESERVED', 'reconcile_commit', scope='ONCE', commit_verified=True), 'CONSUMED')
        with self.assertRaises(ValueError):
            self.transition('RESERVED', 'reconcile_commit', scope='ONCE', commit_verified=False)

    def test_close_requires_terminal_no_retry_and_known_outcome(self):
        self.assertEqual(self.transition('RESERVED', 'close', scope='ONCE',
                                         terminal_verified=True, retry_possible=False, commit_unknown=False), 'CLOSED')
        for context in ({'terminal_verified': False},
                        {'terminal_verified': True, 'retry_possible': True},
                        {'terminal_verified': True, 'commit_unknown': True}):
            with self.subTest(context=context), self.assertRaises(ValueError):
                self.transition('RESERVED', 'close', scope='ONCE', **context)

    def test_revoked_invalidated_consumed_closed_never_grant_new_work(self):
        for state in ('REVOKED', 'INVALIDATED', 'CONSUMED', 'CLOSED'):
            for event in ('reserve', 'admit', 'reset'):
                with self.subTest(state=state, event=event), self.assertRaises(ValueError):
                    self.transition(state, event, scope='ONCE')

    def test_revoke_and_invalidate_block_future_admission(self):
        for state in ('GRANTED', 'RESERVED'):
            self.assertEqual(self.transition(state, 'revoke', scope='ONCE'), 'REVOKED')
            self.assertEqual(self.transition(state, 'invalidate', scope='ONCE'), 'INVALIDATED')

    def test_revoked_unknown_commit_cannot_close_but_verified_commit_can_reconcile(self):
        with self.assertRaises(ValueError):
            self.transition('REVOKED', 'close', scope='ONCE', terminal_verified=True, commit_unknown=True)
        self.assertEqual(self.transition('REVOKED', 'reconcile_commit', scope='ONCE', commit_verified=True), 'CONSUMED')

    def test_scheduled_success_does_not_consume_schedule_grant(self):
        self.assertEqual(self.transition('GRANTED', 'reconcile_commit', scope='SCHEDULED', commit_verified=True), 'GRANTED')

    def replacement_transition(self, name, state, event):
        try:
            module = importlib.import_module('aat_metadata.repositories.replacement_runs')
        except ModuleNotFoundError as exc:
            if exc.name not in {'aat_metadata.repositories', 'aat_metadata.repositories.replacement_runs'}:
                raise
            raise AssertionError('T031 RunIntent/admission state implementation is missing') from None
        self.assertTrue(hasattr(module, name), 'T031 replacement transition seam missing: ' + name)
        return getattr(module, name)(state, event)

    def test_intent_submission_timeout_requires_reconciliation_not_new_reservation(self):
        self.assertEqual(self.replacement_transition('transition_run_intent', 'RESERVED', 'submit'), 'SUBMITTING')
        self.assertEqual(self.replacement_transition('transition_run_intent', 'SUBMITTING', 'timeout'), 'NEEDS_RECONCILIATION')
        with self.assertRaises(ValueError):
            self.replacement_transition('transition_run_intent', 'NEEDS_RECONCILIATION', 'reset')

    def test_intent_created_and_verified_rejection_are_distinct(self):
        self.assertEqual(self.replacement_transition('transition_run_intent', 'SUBMITTING', 'created_verified'), 'CREATED')
        self.assertEqual(self.replacement_transition('transition_run_intent', 'NEEDS_RECONCILIATION', 'rejection_verified'), 'REJECTED')
        with self.assertRaises(ValueError):
            self.replacement_transition('transition_run_intent', 'CREATED', 'reserve')

    def test_admission_unknown_outcome_requires_verification(self):
        self.assertEqual(self.replacement_transition('transition_admission', 'ADMITTED', 'unknown_outcome'), 'NEEDS_RECONCILIATION')
        for event, state in [('commit_verified', 'COMMIT_VERIFIED'), ('rollback_verified', 'ROLLBACK_VERIFIED')]:
            self.assertEqual(self.replacement_transition('transition_admission', 'NEEDS_RECONCILIATION', event), state)

    def test_completed_admission_is_never_reused_for_dml(self):
        for state in ('COMMIT_VERIFIED', 'ROLLBACK_VERIFIED', 'NEEDS_RECONCILIATION'):
            with self.subTest(state=state), self.assertRaises(ValueError):
                self.replacement_transition('transition_admission', state, 'admit')


if __name__ == '__main__':
    unittest.main()
