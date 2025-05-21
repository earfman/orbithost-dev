"""
Billing service for OrbitHost.
This is part of the private components that implement monetization features.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

import stripe
from stripe.error import StripeError

from app.core.config import settings
from app.models.user import User, SubscriptionTier, SubscriptionStatus

logger = logging.getLogger(__name__)

# Initialize Stripe with API key
stripe.api_key = settings.STRIPE_API_KEY

# Define price IDs for each subscription tier
PRICE_IDS = {
    SubscriptionTier.PRO: settings.STRIPE_PRO_PRICE_ID,
    SubscriptionTier.BUSINESS: settings.STRIPE_BUSINESS_PRICE_ID,
}

# Define features for each tier
TIER_FEATURES = {
    SubscriptionTier.FREE: {
        "custom_domains_allowed": 0,
        "team_members_allowed": 1,
    },
    SubscriptionTier.PRO: {
        "custom_domains_allowed": 3,
        "team_members_allowed": 1,
    },
    SubscriptionTier.BUSINESS: {
        "custom_domains_allowed": 10,
        "team_members_allowed": 5,
    },
}


class BillingService:
    """
    Service for managing billing and subscriptions using Stripe.
    """
    
    async def create_customer(self, user: User) -> str:
        """
        Create a Stripe customer for a user.
        
        Args:
            user: User object
            
        Returns:
            Stripe customer ID
        """
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name or ''} {user.last_name or ''}".strip() or None,
                metadata={
                    "user_id": user.id
                }
            )
            
            return customer.id
            
        except StripeError as e:
            logger.error(f"Error creating Stripe customer for user {user.id}: {str(e)}")
            raise
    
    async def create_subscription(
        self, 
        user: User, 
        tier: SubscriptionTier,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """
        Create a subscription for a user.
        
        Args:
            user: User object
            tier: Subscription tier
            payment_method_id: Stripe payment method ID
            
        Returns:
            Subscription details
        """
        if tier == SubscriptionTier.FREE:
            # Free tier doesn't need a Stripe subscription
            return {
                "tier": SubscriptionTier.FREE,
                "status": SubscriptionStatus.ACTIVE,
                "stripe_customer_id": None,
                "stripe_subscription_id": None,
                "current_period_start": datetime.now().isoformat(),
                "current_period_end": None,
                "cancel_at_period_end": False,
                "custom_domains_allowed": TIER_FEATURES[SubscriptionTier.FREE]["custom_domains_allowed"],
                "team_members_allowed": TIER_FEATURES[SubscriptionTier.FREE]["team_members_allowed"]
            }
        
        try:
            # Get or create Stripe customer
            stripe_customer_id = user.subscription.stripe_customer_id
            if not stripe_customer_id:
                stripe_customer_id = await self.create_customer(user)
            
            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=stripe_customer_id
            )
            
            # Set as default payment method
            stripe.Customer.modify(
                stripe_customer_id,
                invoice_settings={
                    "default_payment_method": payment_method_id
                }
            )
            
            # Create subscription
            subscription = stripe.Subscription.create(
                customer=stripe_customer_id,
                items=[
                    {
                        "price": PRICE_IDS[tier]
                    }
                ],
                expand=["latest_invoice.payment_intent"]
            )
            
            # Return subscription details
            return {
                "tier": tier,
                "status": subscription.status,
                "stripe_customer_id": stripe_customer_id,
                "stripe_subscription_id": subscription.id,
                "current_period_start": datetime.fromtimestamp(subscription.current_period_start).isoformat(),
                "current_period_end": datetime.fromtimestamp(subscription.current_period_end).isoformat(),
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "custom_domains_allowed": TIER_FEATURES[tier]["custom_domains_allowed"],
                "team_members_allowed": TIER_FEATURES[tier]["team_members_allowed"]
            }
            
        except StripeError as e:
            logger.error(f"Error creating subscription for user {user.id}: {str(e)}")
            raise
    
    async def cancel_subscription(self, user: User, at_period_end: bool = True) -> Dict[str, Any]:
        """
        Cancel a user's subscription.
        
        Args:
            user: User object
            at_period_end: Whether to cancel at the end of the billing period
            
        Returns:
            Updated subscription details
        """
        if not user.subscription.stripe_subscription_id:
            # User doesn't have a paid subscription
            return user.subscription.dict()
        
        try:
            # Cancel subscription
            subscription = stripe.Subscription.modify(
                user.subscription.stripe_subscription_id,
                cancel_at_period_end=at_period_end
            )
            
            if not at_period_end:
                # If canceling immediately, delete the subscription
                subscription = stripe.Subscription.delete(
                    user.subscription.stripe_subscription_id
                )
                
                # Return free tier details
                return {
                    "tier": SubscriptionTier.FREE,
                    "status": SubscriptionStatus.CANCELED,
                    "stripe_customer_id": user.subscription.stripe_customer_id,
                    "stripe_subscription_id": None,
                    "current_period_start": user.subscription.current_period_start,
                    "current_period_end": user.subscription.current_period_end,
                    "cancel_at_period_end": False,
                    "custom_domains_allowed": TIER_FEATURES[SubscriptionTier.FREE]["custom_domains_allowed"],
                    "team_members_allowed": TIER_FEATURES[SubscriptionTier.FREE]["team_members_allowed"]
                }
            
            # Return updated subscription details
            return {
                "tier": user.subscription.tier,
                "status": subscription.status,
                "stripe_customer_id": user.subscription.stripe_customer_id,
                "stripe_subscription_id": subscription.id,
                "current_period_start": datetime.fromtimestamp(subscription.current_period_start).isoformat(),
                "current_period_end": datetime.fromtimestamp(subscription.current_period_end).isoformat(),
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "custom_domains_allowed": user.subscription.custom_domains_allowed,
                "team_members_allowed": user.subscription.team_members_allowed
            }
            
        except StripeError as e:
            logger.error(f"Error canceling subscription for user {user.id}: {str(e)}")
            raise
    
    async def change_subscription_tier(self, user: User, tier: SubscriptionTier) -> Dict[str, Any]:
        """
        Change a user's subscription tier.
        
        Args:
            user: User object
            tier: New subscription tier
            
        Returns:
            Updated subscription details
        """
        if not user.subscription.stripe_subscription_id and tier != SubscriptionTier.FREE:
            # User doesn't have a paid subscription and is upgrading
            raise ValueError("User must have a payment method to upgrade")
        
        if tier == SubscriptionTier.FREE:
            # Downgrading to free tier
            return await self.cancel_subscription(user)
        
        try:
            # Get current subscription
            subscription = stripe.Subscription.retrieve(
                user.subscription.stripe_subscription_id
            )
            
            # Update subscription items
            stripe.Subscription.modify(
                user.subscription.stripe_subscription_id,
                items=[
                    {
                        "id": subscription["items"]["data"][0].id,
                        "price": PRICE_IDS[tier]
                    }
                ]
            )
            
            # Get updated subscription
            updated_subscription = stripe.Subscription.retrieve(
                user.subscription.stripe_subscription_id
            )
            
            # Return updated subscription details
            return {
                "tier": tier,
                "status": updated_subscription.status,
                "stripe_customer_id": user.subscription.stripe_customer_id,
                "stripe_subscription_id": updated_subscription.id,
                "current_period_start": datetime.fromtimestamp(updated_subscription.current_period_start).isoformat(),
                "current_period_end": datetime.fromtimestamp(updated_subscription.current_period_end).isoformat(),
                "cancel_at_period_end": updated_subscription.cancel_at_period_end,
                "custom_domains_allowed": TIER_FEATURES[tier]["custom_domains_allowed"],
                "team_members_allowed": TIER_FEATURES[tier]["team_members_allowed"]
            }
            
        except StripeError as e:
            logger.error(f"Error changing subscription tier for user {user.id}: {str(e)}")
            raise
    
    async def create_billing_portal_session(self, user: User, return_url: str) -> str:
        """
        Create a Stripe billing portal session for a user.
        
        Args:
            user: User object
            return_url: URL to return to after the session
            
        Returns:
            Billing portal URL
        """
        if not user.subscription.stripe_customer_id:
            raise ValueError("User does not have a Stripe customer ID")
        
        try:
            session = stripe.billing_portal.Session.create(
                customer=user.subscription.stripe_customer_id,
                return_url=return_url
            )
            
            return session.url
            
        except StripeError as e:
            logger.error(f"Error creating billing portal session for user {user.id}: {str(e)}")
            raise
    
    async def create_checkout_session(
        self, 
        user: User, 
        tier: SubscriptionTier,
        success_url: str,
        cancel_url: str
    ) -> str:
        """
        Create a Stripe checkout session for a user to subscribe.
        
        Args:
            user: User object
            tier: Subscription tier
            success_url: URL to redirect to on success
            cancel_url: URL to redirect to on cancel
            
        Returns:
            Checkout session URL
        """
        if tier == SubscriptionTier.FREE:
            raise ValueError("Cannot create checkout session for free tier")
        
        try:
            # Get or create Stripe customer
            stripe_customer_id = user.subscription.stripe_customer_id
            if not stripe_customer_id:
                stripe_customer_id = await self.create_customer(user)
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=stripe_customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": PRICE_IDS[tier],
                        "quantity": 1
                    }
                ],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": user.id,
                    "tier": tier
                }
            )
            
            return session.url
            
        except StripeError as e:
            logger.error(f"Error creating checkout session for user {user.id}: {str(e)}")
            raise
    
    async def handle_webhook_event(self, event_data: Dict[str, Any]) -> None:
        """
        Handle Stripe webhook events.
        
        Args:
            event_data: Webhook event data
        """
        event_type = event_data.get("type")
        
        if event_type == "customer.subscription.created":
            # Handle subscription created
            pass
        elif event_type == "customer.subscription.updated":
            # Handle subscription updated
            pass
        elif event_type == "customer.subscription.deleted":
            # Handle subscription deleted
            pass
        elif event_type == "invoice.payment_succeeded":
            # Handle invoice payment succeeded
            pass
        elif event_type == "invoice.payment_failed":
            # Handle invoice payment failed
            pass
