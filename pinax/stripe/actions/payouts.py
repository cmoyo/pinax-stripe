import stripe

from .. import models, utils


def during(year, month):
    """
    Return a queryset of pinax.stripe.models.Transfer objects for the provided
    year and month.

    Args:
        year: 4-digit year
        month: month as a integer, 1=January through 12=December
    """
    return models.Payout.objects.filter(
        date__year=year,
        date__month=month
    )


def sync_payouts():
    for payout in stripe.Payout.auto_paging_iter():
        sync_payout(payout)

def sync_payout(payout, event=None):
    """
    Synchronize a payout from the Stripe API

    Args:
        payout: data from Stripe API representing payout
        event: the event associated with the payout
    """
    defaults = {
        "amount": utils.convert_amount_for_db(
            payout["amount"], payout["currency"]
        ),
        "amount_reversed": utils.convert_amount_for_db(
            payout["amount_reversed"], payout["currency"]
        ) if payout.get("amount_reversed") else None,
        "created": utils.convert_tstamp(payout["created"]) if payout.get("created") else None,
        "currency": payout["currency"],
        "arrival_date": utils.convert_tstamp(payout.get("arrival_date")),
        "destination": payout.get("destination"),
        "event": event,
        "failure_code": payout.get("failure_code"),
        "failure_message": payout.get("failure_message"),
        "livemode": payout.get("livemode"),
        "metadata": dict(payout.get("metadata", {})),
        "method": payout.get("method"),
        "source_type": payout.get("source_type"),
        "statement_descriptor": payout.get("statement_descriptor"),
        "status": payout.get("status"),
        "transfer_group": payout.get("transfer_group"),
        "type": payout.get("type")
    }
    obj, created = models.Payout.objects.update_or_create(
        stripe_id=payout["id"],
        defaults=defaults
    )
    if not created:
        obj.status = payout["status"]
        obj.save()
    return obj


def update_status(payout):
    """
    Update the status of a pinax.stripe.models.Payout object from Stripe API

    Args:
        payout: a pinax.stripe.models.Payout object to update
    """
    payout.status = stripe.Payout.retrieve(payout.stripe_id).status
    payout.save()


def create(amount, currency, destination, description, transfer_group=None,
           stripe_account=None, **kwargs):
    """
    Create a payout.

    Args:
        amount: quantity of money to be sent
        currency: currency for the payout
        destination: stripe_id of either a connected Stripe Account or Bank Account
        transfer_group: a string that identifies this payout as part of a group
        stripe_account: the stripe_id of a Connect account if creating a payout on
            their behalf
    """
    kwargs.update(dict(
        amount=utils.convert_amount_for_api(amount, currency),
        currency=currency,
        destination=destination
    ))
    if transfer_group:
        kwargs["transfer_group"] = transfer_group
    if stripe_account:
        kwargs["stripe_account"] = stripe_account
    payout = stripe.Payout.create(**kwargs)
    return sync_payout(payout)
