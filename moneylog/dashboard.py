import calendar
from datetime import date
from dateutil.relativedelta import relativedelta
from django.db.models import Sum, Q
from django.utils import timezone
from .models import Account, Movement, Category, Provision, Setting

def dashboard_callback(request, context):
    """
    Unfold dashboard callback. Computes statistics for the dashboard
    and injects them into the context.
    """
    if not request.user.is_authenticated:
        return context

    user = request.user
    
    # 1. Configuration & Time range
    setting = Setting.for_user(user)
    months_window = setting.months

    try:
        req_year = int(request.GET.get('year'))
        req_month = int(request.GET.get('month'))
        reference_date = date(req_year, req_month, 1)
    except (TypeError, ValueError):
        # Default to the most recent movement date, or current date
        last_movement = Movement.objects.filter(account__user=user).order_by('-date').first()
        if last_movement:
            reference_date = date(last_movement.date.year, last_movement.date.month, 1)
        else:
            now = timezone.now().date()
            reference_date = date(now.year, now.month, 1)

    # Next / Prev month
    prev_month = reference_date - relativedelta(months=1)
    next_month = reference_date + relativedelta(months=1)

    # 2. Total Assets
    active_accounts = user.accounts.exclude(status='closed')
    accounts_data = []
    total_balance = 0.0
    for acc in active_accounts:
        bal = acc.movements.aggregate(total=Sum('amount'))['total'] or 0.0
        accounts_data.append({
            'name': acc.name,
            'balance': float(bal),
            'status': acc.status,
            'id': acc.id
        })
        total_balance += float(bal)

    # Spendable Total (Totale Spendibile)
    category_movements_sum = Movement.objects.filter(
        account__user=user, 
        category__isnull=False
    ).aggregate(total=Sum('amount'))['total'] or 0.0
    
    provisions_sum_total = Provision.objects.filter(
        user=user
    ).aggregate(total=Sum('amount'))['total'] or 0.0
    
    provisioned_total = float(category_movements_sum) + float(provisions_sum_total)
    spendable_total = total_balance - provisioned_total

    # 3. Monthly Metrics
    monthly_movements = Movement.objects.filter(
        account__user=user,
        date__year=reference_date.year,
        date__month=reference_date.month
    )
    month_income = monthly_movements.filter(amount__gt=0).aggregate(total=Sum('amount'))['total'] or 0.0
    month_expense = monthly_movements.filter(amount__lt=0).aggregate(total=Sum('amount'))['total'] or 0.0
    
    month_income = float(month_income)
    month_expense = abs(float(month_expense))
    month_savings = month_income - month_expense

    # 4. Monthly Trend (Last 6 Months ending in reference_date)
    trend_data = []
    for i in reversed(range(6)):
        d = reference_date - relativedelta(months=i)
        movs = Movement.objects.filter(account__user=user, date__year=d.year, date__month=d.month)
        inc = movs.filter(amount__gt=0).aggregate(total=Sum('amount'))['total'] or 0.0
        exp = movs.filter(amount__lt=0).aggregate(total=Sum('amount'))['total'] or 0.0
        trend_data.append({
            'month_label': d.strftime("%m/%Y"),
            'income': float(inc),
            'expense': abs(float(exp)),
        })

    # max value for chart scaling
    max_trend_value = 0
    if trend_data:
        max_trend_value = max([max(t['income'], t['expense']) for t in trend_data])

    if max_trend_value == 0:
        max_trend_value = 1  # prevent div by zero
        
    for t in trend_data:
        t['income_pct'] = int((t['income'] / max_trend_value) * 100)
        t['expense_pct'] = int((t['expense'] / max_trend_value) * 100)

    # 5. Category Breakdown for the Last N Months
    cat_breakdown = []
    start_date = (reference_date - relativedelta(months=months_window - 1)).replace(day=1)
    last_day = calendar.monthrange(reference_date.year, reference_date.month)[1]
    end_date = reference_date.replace(day=last_day)

    for cat in user.categories.filter(active=True):
        spending = cat.movements.filter(
            date__gte=start_date, 
            date__lte=end_date,
            amount__lt=0
        ).aggregate(total=Sum('amount'))['total'] or 0.0
        if spending < 0:
            cat_breakdown.append({
                'name': cat.name,
                'amount': abs(float(spending))
            })
    
    # Sort category breakdown desc
    cat_breakdown = sorted(cat_breakdown, key=lambda x: x['amount'], reverse=True)
    total_month_cat_expense = sum(c['amount'] for c in cat_breakdown)
    for c in cat_breakdown:
        c['pct'] = int((c['amount'] / total_month_cat_expense * 100)) if total_month_cat_expense > 0 else 0

    # 6. Provisioning Stats (If Enabled)
    provisioning_stats = None
    if setting.provisioning:
        provisions_sum = user.provisions.aggregate(total=Sum('amount'))['total'] or 0.0
        
        cat_stats = []
        total_monthly_needed = 0.0
        for cat in user.categories.filter(active=True):
            avg = cat.average(months_window)
            avg_needed = abs(avg) if avg < 0 else 0.0
            
            curr_spending = cat.movements.filter(
                date__year=reference_date.year, 
                date__month=reference_date.month
            ).aggregate(total=Sum('amount'))['total'] or 0.0
            
            if avg_needed > 0 or abs(float(curr_spending)) > 0:
                total_monthly_needed += avg_needed
                cat_stats.append({
                    'name': cat.name,
                    'avg': avg_needed,
                    'actual': abs(float(curr_spending)),
                    'status': 'ok' if abs(float(curr_spending)) <= avg_needed else 'over'
                })

        cat_stats = sorted(cat_stats, key=lambda x: x['status'], reverse=True) # Over first
                
        provisioning_stats = {
            'total_provisions': float(provisions_sum),
            'total_monthly_needed': total_monthly_needed,
            'categories': cat_stats
        }

    # Add custom variables to the context
    context.update({
        'reference_date': reference_date,
        'prev_month': f"?year={prev_month.year}&month={prev_month.month}",
        'next_month': f"?year={next_month.year}&month={next_month.month}",
        
        'total_balance': total_balance,
        'provisioned_total': provisioned_total,
        'spendable_total': spendable_total,
        'accounts': accounts_data,
        
        'month_income': month_income,
        'month_expense': month_expense,
        'month_savings': month_savings,
        
        'trend_data': trend_data,
        
        'cat_breakdown': cat_breakdown,
        'provisioning_stats': provisioning_stats,
        'setting': setting
    })

    return context
