import unittest
from datetime import datetime, timezone

from flux_discord_notifier.formatting import classify
from flux_discord_notifier.models import FluxEvent, InvolvedObject


def flux_event(*, kind: str, reason: str, message: str, severity: str = "info") -> FluxEvent:
    return FluxEvent(
        involvedObject=InvolvedObject(kind=kind, name="example", namespace="flux-system"),
        severity=severity,
        reason=reason,
        message=message,
        timestamp=datetime.now(timezone.utc),
    )


class ClassifyTests(unittest.TestCase):
    def test_ignores_periodic_successful_reconciliation(self) -> None:
        event = flux_event(
            kind="Kustomization",
            reason="ReconciliationSucceeded",
            message="Reconciliation finished in 48.295676ms, next run in 10m0s",
        )

        self.assertIsNone(classify(event))

    def test_reports_kustomization_resource_changes(self) -> None:
        event = flux_event(
            kind="Kustomization",
            reason="Progressing",
            message="Deployment/nebulaclient/backend configured",
        )

        style = classify(event)
        self.assertIsNotNone(style)
        self.assertEqual(style.title, "Cluster changes applied")

    def test_reports_errors_even_without_a_resource_change(self) -> None:
        event = flux_event(
            kind="Kustomization",
            reason="HealthCheckFailed",
            message="Deployment did not become ready",
            severity="error",
        )

        style = classify(event)
        self.assertIsNotNone(style)
        self.assertEqual(style.title, "Deployment failed")

    def test_ignores_unchanged_image_policy_reconciliation(self) -> None:
        event = flux_event(
            kind="ImagePolicy",
            reason="ReconciliationSucceeded",
            message="Reconciliation finished in 20ms, next run in 1m0s",
        )

        self.assertIsNone(classify(event))

    def test_reports_new_image(self) -> None:
        event = flux_event(
            kind="ImagePolicy",
            reason="Succeeded",
            message="Latest image tag updated from 1.0.0 to 1.0.1",
        )

        style = classify(event)
        self.assertIsNotNone(style)
        self.assertEqual(style.title, "New image detected")


if __name__ == "__main__":
    unittest.main()
