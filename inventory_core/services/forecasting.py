"""
Forecasting Service for Time-Series Demand Analysis.

Architectural Design:
Provides statistical and machine-learning baselines (Exponential Smoothing,
Linear Regression Trend, and Rolling Volatility) to quantify demand velocity
and demand uncertainty before passing enriched context to the LLM Demand Agent.
"""

import math
from typing import Dict, Any, List
from datetime import datetime, timedelta
import numpy as np
from django.utils import timezone
from inventory_core.models import Product, SalesHistory


class DemandForecaster:
    """
    Computes empirical demand metrics and short-term projections
    from historical SalesHistory time-series data.
    """

    @classmethod
    def analyze_product_demand(
        cls,
        product: Product,
        lookback_days: int = 90,
        forecast_horizon_days: int = 14
    ) -> Dict[str, Any]:
        """
        Extracts sales history for a product, runs statistical time-series forecasting,
        and returns demand velocity and projected daily demand.
        """
        cutoff_date = timezone.now() - timedelta(days=lookback_days)
        records = (
            SalesHistory.objects.filter(product=product, recorded_at__gte=cutoff_date)
            .order_by('recorded_at')
            .values('recorded_at', 'quantity_sold')
        )

        sales_list = list(records)

        # Handle cold-start or minimal data cases gracefully
        if not sales_list:
            fallback_daily = max(1.0, float(product.baseline_rop) / 30.0)
            return {
                "product_sku": product.sku,
                "historical_points_count": 0,
                "mean_daily_sales": round(fallback_daily, 2),
                "std_daily_sales": round(fallback_daily * 0.25, 2),
                "trend_slope": 0.0,
                "forecast_horizon_days": forecast_horizon_days,
                "forecasted_daily_demand": round(fallback_daily, 2),
                "forecasted_total_period_demand": round(fallback_daily * forecast_horizon_days, 2),
                "confidence_interval_95": (
                    round(fallback_daily * 0.8, 2),
                    round(fallback_daily * 1.2, 2)
                ),
                "demand_trend_category": "COLD_START_BASELINE",
            }

        # Aggregate sales by day
        daily_buckets: Dict[str, int] = {}
        # Pre-fill all dates in the lookback window to avoid zero-sale blindness
        start_date = cutoff_date.date()
        end_date = timezone.now().date()
        curr = start_date
        while curr <= end_date:
            daily_buckets[curr.strftime('%Y-%m-%d')] = 0
            curr += timedelta(days=1)

        for item in sales_list:
            dt_key = item['recorded_at'].strftime('%Y-%m-%d')
            daily_buckets[dt_key] = daily_buckets.get(dt_key, 0) + item['quantity_sold']

        daily_quantities = np.array(list(daily_buckets.values()), dtype=np.float64)
        n = len(daily_quantities)

        mean_sales = float(np.mean(daily_quantities))
        std_sales = float(np.std(daily_quantities))

        # Linear regression trend calculation over chronological indices
        x = np.arange(n, dtype=np.float64)
        if n > 1 and np.var(x) > 0:
            slope, intercept = np.polyfit(x, daily_quantities, deg=1)
        else:
            slope, intercept = 0.0, mean_sales

        # Holt-Winters / Exponential weighted moving average proxy for short-term projection
        alpha = 0.3  # Smoothing factor favoring recent velocity
        ewma = daily_quantities[0]
        for val in daily_quantities[1:]:
            ewma = alpha * val + (1 - alpha) * ewma

        # Factor in trend momentum into the projected horizon
        projected_daily = max(0.1, ewma + (slope * (forecast_horizon_days / 2.0)))
        projected_total = projected_daily * forecast_horizon_days

        # 95% Confidence Interval based on empirical standard error
        margin_of_error = 1.96 * (std_sales / math.sqrt(n if n > 0 else 1))
        ci_lower = max(0.0, projected_daily - margin_of_error)
        ci_upper = projected_daily + margin_of_error

        # Determine trend label
        if slope > 0.05:
            trend_category = "EXPANDING_GROWTH"
        elif slope < -0.05:
            trend_category = "CONTRACTING_DECAY"
        else:
            trend_category = "STEADY_STABLE"

        return {
            "product_sku": product.sku,
            "product_name": product.name,
            "historical_points_count": n,
            "mean_daily_sales": round(mean_sales, 2),
            "std_daily_sales": round(std_sales, 2),
            "trend_slope": round(float(slope), 4),
            "forecast_horizon_days": forecast_horizon_days,
            "forecasted_daily_demand": round(float(projected_daily), 2),
            "forecasted_total_period_demand": round(float(projected_total), 2),
            "confidence_interval_95": (round(ci_lower, 2), round(ci_upper, 2)),
            "demand_trend_category": trend_category,
            "recent_ewma_velocity": round(float(ewma), 2),
        }
