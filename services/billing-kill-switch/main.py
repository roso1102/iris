# IRIS — Task 0.3: Billing Budget Interceptor.
# When the monthly budget cap is breached, removes the push endpoint from
# the ingestion subscription so no new documents enter the pipeline.
#
# Depends on google-cloud-pubsub (available in Cloud Functions gen2 runtime).

import base64
import json
import logging
import os

import functions_framework
from google.cloud import pubsub_v1
from google.protobuf import field_mask_pb2
from google.pubsub_v1 import types as pubsub_types

PROJECT = os.environ.get("GCP_PROJECT")
if not PROJECT:
    raise RuntimeError("GCP_PROJECT environment variable is required")

SUBSCRIPTION = os.environ.get("TARGET_SUBSCRIPTION")
if not SUBSCRIPTION:
    raise RuntimeError("TARGET_SUBSCRIPTION environment variable is required")

try:
    MONTHLY_CAP = float(os.environ["MONTHLY_CAP"])
except (KeyError, ValueError):
    raise RuntimeError("MONTHLY_CAP must be a numeric value in the project's billing currency")

logger = logging.getLogger("kill-switch")
logging.basicConfig(level=logging.INFO)


def _should_kill(message: dict) -> bool:
    try:
        cost = float(message.get("costAmount", 0.0))
    except (TypeError, ValueError):
        return False
    exceeded = message.get("alertThresholdExceeded")
    if exceeded is not None:
        try:
            if float(exceeded) >= 1.0:
                return True
        except (TypeError, ValueError):
            pass
    return cost >= MONTHLY_CAP


def _kill_ingestion() -> bool:
    """Set pushConfig to empty on the subscription (pull-only)."""
    subscriber = pubsub_v1.SubscriberClient()
    sub_path = f"projects/{PROJECT}/subscriptions/{SUBSCRIPTION}"

    update = pubsub_types.Subscription(
        name=sub_path,
        push_config=pubsub_types.PushConfig(),  # empty pushConfig
    )
    mask = field_mask_pb2.FieldMask(paths=["push_config"])
    subscriber.update_subscription(subscription=update, update_mask=mask)
    logger.info("Killed ingestion — push endpoint detached from %s", SUBSCRIPTION)
    return True


@functions_framework.cloud_event
def kill_switch(cloud_event) -> None:
    try:
        data = json.loads(
            base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
        )
    except Exception as exc:
        logger.error("Failed to decode budget alert: %s", exc)
        return

    if not _should_kill(data):
        logger.info("Alert below cap; costAmount=%s cap=%s",
                    data.get("costAmount"), MONTHLY_CAP)
        return

    try:
        _kill_ingestion()
    except Exception as exc:
        logger.exception("Kill switch failed: %s", exc)
