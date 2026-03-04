from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count

from references.models import Rcdg, Cdc


def _require_rescom(request):
    if request.user.role != 'RESCOM':
        messages.error(request, 'Access denied.')
        return False
    return True


# ════════════════════════════════════════════════════════════════
# RCDG CRUD
# ════════════════════════════════════════════════════════════════

@login_required
def rcdg_list(request):
    if not _require_rescom(request):
        return redirect('dashboard')
    q = request.GET.get('q', '').strip()
    rcdgs = Rcdg.objects.annotate(cdc_count=Count('cdc')).order_by('rcdg_desc')
    if q:
        rcdgs = rcdgs.filter(
            Q(rcdg_desc__icontains=q) |
            Q(rcdg_address__icontains=q) |
            Q(rcdg_commander__icontains=q)
        )
    return render(request, 'references/rcdg_list.html', {
        'rcdgs': rcdgs,
        'search_query': q,
    })


@login_required
def rcdg_create(request):
    if not _require_rescom(request):
        return redirect('dashboard')
    if request.method == 'POST':
        rcdg = Rcdg(
            rcdg_desc=request.POST.get('rcdg_desc', '').strip(),
            rcdg_address=request.POST.get('rcdg_address', '').strip(),
            rcdg_commander=request.POST.get('rcdg_commander', '').strip(),
            cp_no=request.POST.get('cp_no', '').strip() or None,
            latitude=request.POST.get('latitude', '').strip() or None,
            longitude=request.POST.get('longitude', '').strip() or None,
        )
        try:
            rcdg.save()
            messages.success(request, f'RCDG "{rcdg.rcdg_desc}" created successfully.')
            return redirect('ref_rcdg_list')
        except Exception as e:
            messages.error(request, f'Error creating RCDG: {e}')
    return render(request, 'references/rcdg_form.html', {
        'title': 'Create RCDG',
        'submit_label': 'Create RCDG',
    })


@login_required
def rcdg_edit(request, pk):
    if not _require_rescom(request):
        return redirect('dashboard')
    rcdg = get_object_or_404(Rcdg, pk=pk)
    if request.method == 'POST':
        rcdg.rcdg_desc = request.POST.get('rcdg_desc', '').strip()
        rcdg.rcdg_address = request.POST.get('rcdg_address', '').strip()
        rcdg.rcdg_commander = request.POST.get('rcdg_commander', '').strip()
        rcdg.cp_no = request.POST.get('cp_no', '').strip() or None
        rcdg.latitude = request.POST.get('latitude', '').strip() or None
        rcdg.longitude = request.POST.get('longitude', '').strip() or None
        try:
            rcdg.save()
            messages.success(request, f'RCDG "{rcdg.rcdg_desc}" updated.')
            return redirect('ref_rcdg_list')
        except Exception as e:
            messages.error(request, f'Error updating RCDG: {e}')
    return render(request, 'references/rcdg_form.html', {
        'title': 'Edit RCDG',
        'submit_label': 'Save Changes',
        'rcdg': rcdg,
    })


@login_required
def rcdg_delete(request, pk):
    if not _require_rescom(request):
        return redirect('dashboard')
    rcdg = get_object_or_404(Rcdg, pk=pk)
    if request.method == 'POST':
        name = rcdg.rcdg_desc
        rcdg.delete()
        messages.success(request, f'RCDG "{name}" deleted.')
    return redirect('ref_rcdg_list')


# ════════════════════════════════════════════════════════════════
# CDC CRUD
# ════════════════════════════════════════════════════════════════

@login_required
def cdc_list(request):
    if not _require_rescom(request):
        return redirect('dashboard')
    q = request.GET.get('q', '').strip()
    cdcs = Cdc.objects.select_related('rcdg').order_by('cdc_code')
    if q:
        cdcs = cdcs.filter(
            Q(cdc_code__icontains=q) |
            Q(cdc_desc__icontains=q) |
            Q(cdc_address__icontains=q) |
            Q(cdc_director__icontains=q) |
            Q(rcdg__rcdg_desc__icontains=q)
        )
    rcdg_filter = request.GET.get('rcdg', '')
    if rcdg_filter:
        cdcs = cdcs.filter(rcdg_id=rcdg_filter)
    return render(request, 'references/cdc_list.html', {
        'cdcs': cdcs,
        'search_query': q,
        'rcdgs': Rcdg.objects.all().order_by('rcdg_desc'),
        'selected_rcdg': rcdg_filter,
    })


@login_required
def cdc_create(request):
    if not _require_rescom(request):
        return redirect('dashboard')
    if request.method == 'POST':
        rcdg_id = request.POST.get('rcdg')
        cdc = Cdc(
            rcdg_id=rcdg_id,
            cdc_code=request.POST.get('cdc_code', '').strip(),
            cdc_desc=request.POST.get('cdc_desc', '').strip() or None,
            cdc_address=request.POST.get('cdc_address', '').strip() or None,
            cdc_director=request.POST.get('cdc_director', '').strip() or None,
            cp_no=request.POST.get('cp_no', '').strip() or None,
            latitude=request.POST.get('latitude', '').strip() or None,
            longitude=request.POST.get('longitude', '').strip() or None,
        )
        try:
            cdc.save()
            messages.success(request, f'CDC "{cdc.cdc_code}" created successfully.')
            return redirect('ref_cdc_list')
        except Exception as e:
            messages.error(request, f'Error creating CDC: {e}')
    return render(request, 'references/cdc_form.html', {
        'title': 'Create CDC',
        'submit_label': 'Create CDC',
        'rcdgs': Rcdg.objects.all().order_by('rcdg_desc'),
    })


@login_required
def cdc_edit(request, pk):
    if not _require_rescom(request):
        return redirect('dashboard')
    cdc = get_object_or_404(Cdc, pk=pk)
    if request.method == 'POST':
        cdc.rcdg_id = request.POST.get('rcdg')
        cdc.cdc_code = request.POST.get('cdc_code', '').strip()
        cdc.cdc_desc = request.POST.get('cdc_desc', '').strip() or None
        cdc.cdc_address = request.POST.get('cdc_address', '').strip() or None
        cdc.cdc_director = request.POST.get('cdc_director', '').strip() or None
        cdc.cp_no = request.POST.get('cp_no', '').strip() or None
        cdc.latitude = request.POST.get('latitude', '').strip() or None
        cdc.longitude = request.POST.get('longitude', '').strip() or None
        try:
            cdc.save()
            messages.success(request, f'CDC "{cdc.cdc_code}" updated.')
            return redirect('ref_cdc_list')
        except Exception as e:
            messages.error(request, f'Error updating CDC: {e}')
    return render(request, 'references/cdc_form.html', {
        'title': 'Edit CDC',
        'submit_label': 'Save Changes',
        'cdc': cdc,
        'rcdgs': Rcdg.objects.all().order_by('rcdg_desc'),
    })


@login_required
def cdc_delete(request, pk):
    if not _require_rescom(request):
        return redirect('dashboard')
    cdc = get_object_or_404(Cdc, pk=pk)
    if request.method == 'POST':
        code = cdc.cdc_code
        cdc.delete()
        messages.success(request, f'CDC "{code}" deleted.')
    return redirect('ref_cdc_list')
