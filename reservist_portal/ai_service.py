"""
AI Analytics service for TARGET system.
Uses OpenRouter API with openai/gpt-oss-120b:free model.
Compatible with the OpenAI Python SDK via custom base_url.
"""

import json
import logging
from datetime import date, timedelta
from django.conf import settings
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear

logger = logging.getLogger(__name__)


def get_incident_stats(queryset):
    """Compute incident statistics from a queryset."""
    stats = {
        'total': queryset.count(),
        'by_type': dict(
            queryset.values_list('incident_type')
            .annotate(count=Count('id'))
            .values_list('incident_type', 'count')
        ),
        'by_status': dict(
            queryset.values_list('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        ),
        'by_region': dict(
            queryset.values_list('region')
            .annotate(count=Count('id'))
            .values_list('region', 'count')
        ),
        'daily': list(
            queryset.annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
            .values('day', 'count')
        ),
        'weekly': list(
            queryset.annotate(week=TruncWeek('created_at'))
            .values('week')
            .annotate(count=Count('id'))
            .order_by('week')
            .values('week', 'count')
        ),
        'monthly': list(
            queryset.annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
            .values('month', 'count')
        ),
        'yearly': list(
            queryset.annotate(year=TruncYear('created_at'))
            .values('year')
            .annotate(count=Count('id'))
            .order_by('year')
            .values('year', 'count')
        ),
    }
    return stats


def generate_ai_summary(stats_data, period_label=''):
    """
    Generate AI summary using OpenRouter API with multi-model fallback.
    Tries several free models in sequence if one is rate-limited.
    Falls back to a basic summary if all models fail or no API key is set.
    """
    api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
    base_url = getattr(settings, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')

    if not api_key:
        return _generate_basic_summary(stats_data, period_label)

    # Free models to try in order of preference
    FREE_MODELS = [
        'meta-llama/llama-3.3-70b-instruct:free',
        'google/gemma-3-27b-it:free',
        'mistralai/mistral-small-3.1-24b-instruct:free',
        'qwen/qwen3-235b-a22b-instruct:free',
        'deepseek/deepseek-r1-0528:free',
        getattr(settings, 'OPENROUTER_MODEL', 'openai/gpt-oss-120b:free'),
    ]

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        serializable_data = _serialize_stats(stats_data)

        prompt = (
            f"You are a government emergency response analyst. "
            f"Summarize the following {period_label} incident statistics and detect trends, "
            f"unusual spikes, and high-risk regions. Provide actionable recommendations.\n\n"
            f"Data:\n{json.dumps(serializable_data, indent=2)}"
        )

        messages = [
            {'role': 'system', 'content': 'You are a government emergency response analyst for the Philippines.'},
            {'role': 'user', 'content': prompt},
        ]

        last_error = None
        for model in FREE_MODELS:
            try:
                logger.info(f"Trying OpenRouter model: {model}")
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7,
                )
                result = response.choices[0].message.content
                if result:
                    logger.info(f"Successfully generated summary with model: {model}")
                    return result
            except Exception as model_error:
                last_error = model_error
                logger.warning(f"Model {model} failed: {model_error}")
                continue

        logger.error(f"All OpenRouter models failed. Last error: {last_error}")
        return _generate_basic_summary(stats_data, period_label)

    except Exception as e:
        logger.error(f"OpenRouter AI summary generation failed: {e}")
        return _generate_basic_summary(stats_data, period_label)


def _generate_basic_summary(stats_data, period_label=''):
    """Generate a basic text summary without AI."""
    total = stats_data.get('total', 0)
    by_type = stats_data.get('by_type', {})
    by_region = stats_data.get('by_region', {})

    if total == 0:
        return f"No incidents recorded for this {period_label} period."

    # Find most common type
    top_type = max(by_type, key=by_type.get) if by_type else 'N/A'
    top_type_count = by_type.get(top_type, 0)

    # Find most affected region
    top_region = max(by_region, key=by_region.get) if by_region else 'N/A'
    top_region_count = by_region.get(top_region, 0)

    summary = (
        f"📊 {period_label.title()} Summary Report\n\n"
        f"Total Incidents: {total}\n\n"
        f"Most Common Type: {top_type.title()} ({top_type_count} incidents)\n"
        f"Most Affected Region: {top_region} ({top_region_count} incidents)\n\n"
        f"Breakdown by Type:\n"
    )
    for itype, count in sorted(by_type.items(), key=lambda x: -x[1]):
        summary += f"  • {itype.title()}: {count}\n"

    return summary


def _serialize_stats(stats):
    """Convert date objects to strings for JSON serialization."""
    serializable = {}
    for key, value in stats.items():
        if isinstance(value, list):
            serializable[key] = [
                {k: v.isoformat() if isinstance(v, date) else v for k, v in item.items()}
                for item in value
            ]
        elif isinstance(value, dict):
            serializable[key] = {
                (k.isoformat() if isinstance(k, date) else str(k)): v
                for k, v in value.items()
            }
        else:
            serializable[key] = value
    return serializable
