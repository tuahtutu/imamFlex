from django.shortcuts import render,redirect,get_object_or_404
from .models import Imam, Muazzin, Siak,PrayerSchedule,PRAYER_TIMES,DutySchedule,LeaveRequest,Khutbah,JumaatPrayer,AttendanceRecord
from django.contrib import messages
from calendar import monthrange
from django.db.models import Q
from calendar import monthrange
import calendar
import datetime
from datetime import datetime,date
import calendar
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

def home(request):
    return render(request, 'index.html')
  # make sure 'main.html' is your jemaah homepage



def login(request):
    if request.method == 'POST':
        user_id = request.POST.get('username')
        password = request.POST.get('password')

        # Check Admin Imam
        try:
            imam = Imam.objects.get(imam_id=user_id, password=password)
            if imam.is_admin:
                request.session['user_id'] = imam.imam_id
                request.session['role'] = 'admin'
                return redirect('adminDash')
            else:
                request.session['user_id'] = imam.imam_id
                request.session['role'] = 'imam'
                return redirect('imamDash')
        except Imam.DoesNotExist:
            pass

        # Check Muazzin
        try:
            muazzin = Muazzin.objects.get(muazzin_id=user_id, password=password)
            request.session['user_id'] = muazzin.muazzin_id
            request.session['role'] = 'muazzin'
            return redirect('muazzinDash')
        except Muazzin.DoesNotExist:
            pass

        # Check Siak
        try:
            siak = Siak.objects.get(siak_id=user_id, password=password)
            request.session['user_id'] = siak.siak_id
            request.session['role'] = 'siak'
            return redirect('siakDash')
        except Siak.DoesNotExist:
            pass

        
        return render(request, 'login.html', {'error': 'ID atau kata laluan salah.'})

    return render(request, 'login.html')

def logout(request):
    # Clear all session data
    request.session.flush()

    # Optional: Add a message
    messages.success(request, "Anda telah berjaya logout.")

    # Redirect to login page (adjust URL name if needed)
    return redirect('login')  # or whatever your login URL is

#Untuk belah admin dulu
def admin_dashboard(request):
    today = timezone.now().date()

    # Imam schedule today
    imam_schedule_today = DutySchedule.objects.filter(
    date=today, role_type='Imam'
)


    # Khutbah terbaru
    latest_khutbah = Khutbah.objects.order_by('-date').first()

    # Cuti belum lulus
    pending_leaves = LeaveRequest.objects.filter(approval_status='Pending')

    # Total Imam, Muazzin, Siak
    imam_count = Imam.objects.count()
    muazzin_count = Muazzin.objects.count()
    siak_count = Siak.objects.count()

    # Next khutbah untuk Jumaat sahaja
    next_jumaat_khutbah = Khutbah.objects.filter(
        event_type__icontains='Jumaat', date__gt=today
    ).order_by('date').first()

    context = {
        'imam_schedule_today': imam_schedule_today,
        'latest_khutbah': latest_khutbah,
        'pending_leaves': pending_leaves,
        'imam_count': imam_count,
        'muazzin_count': muazzin_count,
        'siak_count': siak_count,
        'next_jumaat_khutbah': next_jumaat_khutbah,
        'imams': Imam.objects.all(),

    }

    return render(request, 'admin/adminDashboard.html', context)


def admin_leave_list(request):
    leaves = LeaveRequest.objects.all().order_by('-start_date')

    for leave in leaves:
        model = {'Imam': Imam, 'Muazzin': Muazzin, 'Siak': Siak}.get(leave.role_type)
        if model:
            staff = model.objects.filter(pk=leave.role_id).first()
            leave.staff_name = staff.name if staff else 'Tidak Dikenali'
        else:
            leave.staff_name = 'Tidak Dikenali'

    context = {
        'leaves': leaves
    }
    return render(request, 'admin/adminLeave.html', context)
def approve_leave(request, request_id):
    leave = get_object_or_404(LeaveRequest, request_id=request_id)
    leave.approval_status = 'Approved'
    leave.save()
    messages.success(request, f'Permohonan cuti {leave.role_type} telah diluluskan.')
    return redirect('admin_leave_list')

def reject_leave(request, request_id):
    leave = get_object_or_404(LeaveRequest, request_id=request_id)
    leave.approval_status = 'Rejected'
    leave.save()
    messages.error(request, f'Permohonan cuti {leave.role_type} telah ditolak.')
    return redirect('admin_leave_list')
#Part Imam
def imam_management(request):
    imams = Imam.objects.all()
    context = {
        'imams': imams
    }
    return render(request, 'admin/imamManagement.html', context)

def add_imam(request):
    if request.method == 'POST':
        imam_id = request.POST.get('imam_id')
        name = request.POST.get('name')
        ic_number = request.POST.get('ic_number')
        contact_number = request.POST.get('contact_number')
        address = request.POST.get('address')
        password = request.POST.get('password')

        Imam.objects.create(
            imam_id=imam_id,
            name=name,
            ic_number=ic_number,
            contact_number=contact_number,
            address=address,
            password=password
        )
        return redirect('imam_management')
    
    return render(request, 'admin/addImam.html') 

    
def edit_imam(request, imam_id):
    imam = get_object_or_404(Imam, imam_id=imam_id)

    if request.method == 'POST':
        imam.name = request.POST.get('name')
        imam.ic_number = request.POST.get('ic_number')
        imam.contact_number = request.POST.get('contact_number')
        imam.save()
        return redirect('imam_management')

    return render(request, 'admin/editImam.html', {'imam': imam})

def delete_imam(request, imam_id):
    if request.session.get('imam_id') == imam_id:
        messages.error(request, "Anda tidak boleh delete diri sendiri.")
        return redirect('imam_management')

    imam = get_object_or_404(Imam, imam_id=imam_id)
    if request.method == "POST":
        imam.delete()
        messages.success(request, f"Imam {imam_id} berjaya dipadam.")
        return redirect('imam_management')
    

def imam_schedule(request):
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    # Simpan/Publish Logic (if POST)
    if request.method == 'POST':
        if 'publishMonthBtn' in request.POST:
            duty_qs = DutySchedule.objects.filter(
                date__year=year,
                date__month=month,
                role_type='Imam'
            )
            duty_qs.update(role_assigned=True)

            # Sync DutySchedule ➜ PrayerSchedule
            for duty in duty_qs:
                # check if already exists
                ps, created = PrayerSchedule.objects.get_or_create(
                    date=duty.date,
                    prayer_time=duty.prayer_time,
                    defaults={'imam': Imam.objects.filter(imam_id=duty.role_id).first()}
                )
                if not created:
                    ps.imam = Imam.objects.filter(imam_id=duty.role_id).first()
                    ps.save()

            messages.success(request, f'Jadual Imam bulan {calendar.month_name[month]} telah diterbitkan.')
        else:
            messages.success(request, f'Jadual Imam bulan {calendar.month_name[month]} telah disimpan.')

    # Data schedule
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    all_schedules = DutySchedule.objects.filter(date__range=[first_day, last_day], role_type='Imam')
    cal = calendar.Calendar(firstweekday=6)
    month_matrix = cal.monthdatescalendar(year, month)

    prayers = ['Subuh', 'Zohor', 'Asar', 'Maghrib', 'Isyak']
    calendar_data = []
    for week in month_matrix:
        week_data = []
        for day in week:
            if day.month == month:
                daily_prayers = {prayer: None for prayer in prayers}
                for schedule in all_schedules:
                    if schedule.date == day and schedule.prayer_time in daily_prayers:
                        imam = Imam.objects.filter(imam_id=schedule.role_id).first()
                        daily_prayers[schedule.prayer_time] = imam.name if imam else "?"
                week_data.append({'date': day, 'prayers': daily_prayers})
            else:
                week_data.append(None)
        calendar_data.append(week_data)

    years = list(range(today.year, today.year + 5))
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]

    context = {
        'calendar': calendar_data,
        'month': month,
        'month_name': calendar.month_name[month],
        'year': year,
        'imam_list': Imam.objects.all(),
        'prayers': prayers,
        'years': years,
        'months': months,
    }
    return render(request, 'admin/imamSchedule.html', context)

    # Year & Month dropdown options (e.g. from 2023 - 2027)
    years = list(range(today.year, today.year + 5))
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]

    context = {
        'calendar': calendar_data,
        'month': month,
        'month_name': calendar.month_name[month],
        'year': year,
        'imam_list': Imam.objects.all(),
        'prayers': prayers,
        'years': years,
        'months': months,
    }
    return render(request, 'admin/imamSchedule.html', context)





@csrf_exempt
def assign_schedule_ajax(request, date):
    if request.method == 'POST':
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
            prayers = ['Subuh', 'Zohor', 'Asar', 'Maghrib', 'Isyak']
            response_data = {}

            for prayer in prayers:
                imam_id = request.POST.get(prayer)
                if imam_id:
                    schedule, created = DutySchedule.objects.get_or_create(
                        date=target_date,
                        prayer_time=prayer,
                        role_type='Imam',
                        defaults={'role_id': imam_id, 'role_assigned': True}
                    )
                    if not created:
                        schedule.role_id = imam_id
                        schedule.role_assigned = True
                        schedule.save()
                    imam = Imam.objects.filter(imam_id=imam_id).first()
                    response_data[prayer] = imam.name if imam else '?'
                else:
                    response_data[prayer] = '-'
            
            return JsonResponse({'status': 'success', 'data': response_data})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

# ========== MUAZZIN MANAGEMENT ==========

def muazzin_management(request):
    muazzins = Muazzin.objects.all()
    context = {
        'muazzins': muazzins
    }
    return render(request, 'admin/muazzinManage.html', context)

def add_muazzin(request):
    if request.method == 'POST':
        muazzin_id = request.POST.get('muazzin_id')
        name = request.POST.get('name')
        ic_number = request.POST.get('ic_number')
        contact_number = request.POST.get('contact_number')
        address = request.POST.get('address')
        password = request.POST.get('password')

        Muazzin.objects.create(
            muazzin_id=muazzin_id,
            name=name,
            ic_number=ic_number,
            contact_number=contact_number,
            address=address,
            password=password
        )
        return redirect('muazzin_management')
    
    return render(request, 'admin/addMuazzin.html')

def edit_muazzin(request, muazzin_id):
    muazzin = get_object_or_404(Muazzin, muazzin_id=muazzin_id)

    if request.method == 'POST':
        muazzin.name = request.POST.get('name')
        muazzin.ic_number = request.POST.get('ic_number')
        muazzin.contact_number = request.POST.get('contact_number')
        muazzin.address = request.POST.get('address')
        muazzin.save()
        return redirect('muazzin_management')

    return render(request, 'admin/editMuazzin.html', {'muazzin': muazzin})

def delete_muazzin(request, muazzin_id):
    muazzin = get_object_or_404(Muazzin, muazzin_id=muazzin_id)
    if request.method == "POST":
        muazzin.delete()
        messages.success(request, f"Muazzin {muazzin_id} berjaya dipadam.")
        return redirect('muazzin_management')
    
def muazzin_schedule(request):
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    # Simpan/Publish Logic
    if request.method == 'POST':
        if 'publishMonthBtn' in request.POST:
            DutySchedule.objects.filter(
                date__year=year,
                date__month=month,
                role_type='Muazzin'
            ).update(role_assigned=True)
            messages.success(request, f'Jadual Muazzin bulan {calendar.month_name[month]} telah diterbitkan.')
        else:
            messages.success(request, f'Jadual Muazzin bulan {calendar.month_name[month]} telah disimpan.')

    # Prepare calendar
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    all_schedules = DutySchedule.objects.filter(date__range=[first_day, last_day], role_type='Muazzin')
    cal = calendar.Calendar(firstweekday=6)
    month_matrix = cal.monthdatescalendar(year, month)

    prayers = ['Subuh', 'Zohor', 'Asar', 'Maghrib', 'Isyak']
    calendar_data = []
    for week in month_matrix:
        week_data = []
        for day in week:
            if day.month == month:
                daily_prayers = {prayer: None for prayer in prayers}
                for schedule in all_schedules:
                    if schedule.date == day and schedule.prayer_time in daily_prayers:
                        muazzin = Muazzin.objects.filter(muazzin_id=schedule.role_id).first()
                        daily_prayers[schedule.prayer_time] = muazzin.name if muazzin else "?"
                week_data.append({'date': day, 'prayers': daily_prayers})
            else:
                week_data.append(None)
        calendar_data.append(week_data)

    context = {
        'calendar': calendar_data,
        'month': month,
        'month_name': calendar.month_name[month],
        'year': year,
        'muazzin_list': Muazzin.objects.all(),
        'prayers': prayers,
        'years': list(range(today.year, today.year + 5)),
        'months': [(i, calendar.month_name[i]) for i in range(1, 13)],
    }
    return render(request, 'admin/muazzinSchedule.html', context)


@csrf_exempt
def assign_muazzin_schedule_ajax(request, date):
    if request.method == 'POST':
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
            prayers = ['Subuh', 'Zohor', 'Asar', 'Maghrib', 'Isyak']
            response_data = {}

            for prayer in prayers:
                muazzin_id = request.POST.get(prayer)
                if muazzin_id:
                    schedule, created = DutySchedule.objects.get_or_create(
                        date=target_date,
                        prayer_time=prayer,
                        role_type='Muazzin',
                        defaults={'role_id': muazzin_id, 'role_assigned': True}
                    )
                    if not created:
                        schedule.role_id = muazzin_id
                        schedule.role_assigned = True
                        schedule.save()
                    muazzin = Muazzin.objects.filter(muazzin_id=muazzin_id).first()
                    response_data[prayer] = muazzin.name if muazzin else '?'
                else:
                    response_data[prayer] = '-'

            return JsonResponse({'status': 'success', 'data': response_data})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

# ========== SIAK MANAGEMENT ==========
def siak_management(request):
    siaks = Siak.objects.all()
    return render(request, 'admin/siakManagement.html', {'siaks': siaks})

def add_siak(request):
    if request.method == 'POST':
        siak_id = request.POST.get('siak_id')
        name = request.POST.get('name')
        ic_number = request.POST.get('ic_number')
        contact_number = request.POST.get('contact_number')
        address = request.POST.get('address')
        password = request.POST.get('password')

        Siak.objects.create(
            siak_id=siak_id,
            name=name,
            ic_number=ic_number,
            contact_number=contact_number,
            address=address,
            password=password
        )
        return redirect('siak_management')
    return render(request, 'admin/addSiak.html')

def edit_siak(request, siak_id):
    siak = get_object_or_404(Siak, siak_id=siak_id)
    if request.method == 'POST':
        siak.name = request.POST.get('name')
        siak.ic_number = request.POST.get('ic_number')
        siak.contact_number = request.POST.get('contact_number')
        siak.address = request.POST.get('address')
        siak.save()
        return redirect('siak_management')
    return render(request, 'admin/editSiak.html', {'siak': siak})

def delete_siak(request, siak_id):
    siak = get_object_or_404(Siak, siak_id=siak_id)
    if request.method == 'POST':
        siak.delete()
        messages.success(request, f"Siak {siak_id} berjaya dipadam.")
        return redirect('siak_management')

def siak_schedule(request):
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    if request.method == 'POST':
        if 'publishMonthBtn' in request.POST:
            DutySchedule.objects.filter(
                date__year=year,
                date__month=month,
                role_type='Siak'
            ).update(role_assigned=True)
            messages.success(request, f'Jadual Siak bulan {calendar.month_name[month]} telah diterbitkan.')
        else:
            messages.success(request, f'Jadual Siak bulan {calendar.month_name[month]} telah disimpan.')

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    all_schedules = DutySchedule.objects.filter(date__range=[first_day, last_day], role_type='Siak')

    cal = calendar.Calendar(firstweekday=6)
    month_matrix = cal.monthdatescalendar(year, month)

    prayers = ['Subuh', 'Zohor', 'Asar', 'Maghrib', 'Isyak']
    calendar_data = []
    for week in month_matrix:
        week_data = []
        for day in week:
            if day.month == month:
                daily_prayers = {prayer: None for prayer in prayers}
                for schedule in all_schedules:
                    if schedule.date == day and schedule.prayer_time in daily_prayers:
                        siak = Siak.objects.filter(siak_id=schedule.role_id).first()
                        daily_prayers[schedule.prayer_time] = siak.name if siak else "?"
                week_data.append({'date': day, 'prayers': daily_prayers})
            else:
                week_data.append(None)
        calendar_data.append(week_data)

    years = list(range(today.year, today.year + 5))
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]

    context = {
        'calendar': calendar_data,
        'month': month,
        'month_name': calendar.month_name[month],
        'year': year,
        'siak_list': Siak.objects.all(),
        'prayers': prayers,
        'years': years,
        'months': months,
    }
    return render(request, 'admin/siakSchedule.html', context)


@csrf_exempt
def assign_siak_schedule_ajax(request, date):
    if request.method == 'POST':
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
            prayers = ['Subuh', 'Zohor', 'Asar', 'Maghrib', 'Isyak']
            response_data = {}

            for prayer in prayers:
                siak_id = request.POST.get(prayer)
                if siak_id:
                    schedule, created = DutySchedule.objects.get_or_create(
                        date=target_date,
                        prayer_time=prayer,
                        role_type='Siak',
                        defaults={'role_id': siak_id, 'role_assigned': True}
                    )
                    if not created:
                        schedule.role_id = siak_id
                        schedule.role_assigned = True
                        schedule.save()
                    siak = Siak.objects.filter(siak_id=siak_id).first()
                    response_data[prayer] = siak.name if siak else '?'
                else:
                    response_data[prayer] = '-'

            return JsonResponse({'status': 'success', 'data': response_data})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

#===================KHUTBAH=============#
def khutbah_list(request):
    khutbahs = Khutbah.objects.all().order_by('-date')
    return render(request, 'admin/adminKhutbah.html', {'khutbahs': khutbahs})

def add_khutbah(request):
    if request.method == 'POST':
        date = request.POST.get('date')
        event_type = request.POST.get('event_type')
        khutbah_topic = request.POST.get('khutbah_topic')
        content = request.POST.get('content')
        imam_id = request.POST.get('imam_id')

        imam = get_object_or_404(Imam, imam_id=imam_id)  # Pindah ni naik atas

        khutbah = Khutbah.objects.create(
            date=date,
            event_type=event_type,
            khutbah_topic=khutbah_topic,
            content=content,
            khatib=imam  # sekarang imam dah wujud
        )

        from .models import JumaatPrayer
        JumaatPrayer.objects.create(khutbah=khutbah, imam=imam)

        messages.success(request, 'Khutbah berjaya ditambah!')
        return redirect('khutbah_list')

    imams = Imam.objects.all()
    return render(request, 'admin/addKhutbah.html', {'imams': imams})

# Edit khutbah
def edit_khutbah(request, khutbah_id):
    khutbah = get_object_or_404(Khutbah, pk=khutbah_id)
    jumaat = khutbah.jumaatprayer_set.first()

    if request.method == 'POST':
        khutbah.date = request.POST.get('date')
        khutbah.event_type = request.POST.get('event_type')
        khutbah.khutbah_topic = request.POST.get('khutbah_topic')
        khutbah.content = request.POST.get('content')

        imam_id = request.POST.get('imam_id')
        imam = get_object_or_404(Imam, imam_id=imam_id)

        khutbah.khatib = imam  # ✅ update the khatib
        khutbah.save()

        if jumaat:
            jumaat.imam = imam
            jumaat.save()
        else:
            JumaatPrayer.objects.create(khutbah=khutbah, imam=imam)

        messages.success(request, 'Khutbah berjaya dikemaskini!')
        return redirect('khutbah_list')

    imams = Imam.objects.all()
    selected_imam = jumaat.imam.imam_id if jumaat else (khutbah.khatib.imam_id if khutbah.khatib else None)

    return render(request, 'admin/editKhutbah.html', {
        'khutbah': khutbah,
        'imams': imams,
        'selected_imam': selected_imam
    })


# Delete khutbah
def delete_khutbah(request, khutbah_id):
    khutbah = get_object_or_404(Khutbah, pk=khutbah_id)
    khutbah.delete()
    messages.warning(request, 'Khutbah telah dipadam.')
    return redirect('khutbah_list')

#=!!!!!IMAM SIDE!!!!=#
def imam_dashboard(request):
    imam_id = request.session.get('user_id')
    if not imam_id:
        return redirect('login')  # fallback just in case

    imam = Imam.objects.get(imam_id=imam_id)

    # Jadual untuk hari ini
    today = date.today()
    imam_schedule_today = PrayerSchedule.objects.filter(date=today, imam=imam)

    # Khutbah akan datang
    upcoming_khutbah = JumaatPrayer.objects.filter(
        imam=imam,
        khutbah__date__gte=today
    ).order_by('khutbah__date').first()

    return render(request, 'imam/imamDash.html', {
        'imam': imam,
        'imam_schedule_today': imam_schedule_today,
        'upcoming_khutbah': upcoming_khutbah.khutbah if upcoming_khutbah else None,
    })

def imam_schedule_side(request):
    imam_id = request.session.get('user_id')
    imam = get_object_or_404(Imam, imam_id=imam_id)

    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    schedules = DutySchedule.objects.filter(
        role_type='Imam',
        role_id=imam_id,
        date__range=(first_day, last_day),
        role_assigned=True
    )

    prayers = ['Subuh', 'Zohor', 'Asar', 'Maghrib', 'Isyak']
    cal = calendar.Calendar(firstweekday=6)
    month_matrix = cal.monthdatescalendar(year, month)

    calendar_data = []
    for week in month_matrix:
        week_data = []
        for day in week:
            if day.month == month:
                daily_prayers = {prayer: False for prayer in prayers}
                for sched in schedules:
                    if sched.date == day and sched.prayer_time in prayers:
                        daily_prayers[sched.prayer_time] = True
                week_data.append({'date': day, 'prayers': daily_prayers})
            else:
                week_data.append(None)
        calendar_data.append(week_data)

    years = list(range(today.year, today.year + 5))
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]
    status = request.GET.get('status') 

    return render(request, 'imam/Schedule.html', {
        'calendar': calendar_data,
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'years': years,
        'months': months,
        'status': status,
    
    })

from django.utils.http import urlencode
from django.urls import reverse
def apply_leave(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        prayer = request.POST.get('prayer_time')
        reason = request.POST.get('reason')
        doc = request.FILES.get('supporting_document')

        if not (date_str and prayer and reason):
            messages.error(request, "Sila lengkapkan semua maklumat permohonan.")
            return redirect('imam_schedule_side')

        try:
            date_obj = datetime.strptime(date_str, "%B %d, %Y").date()
        except ValueError:
            messages.error(request, "Tarikh tidak sah.")
            return redirect('imam_schedule_side')

        imam_id = request.session.get('user_id')
        LeaveRequest.objects.create(
            role_type='Imam',
            role_id=imam_id,
            start_date=date_obj,
            end_date=date_obj,
            reason=reason,
            supporting_document=doc
        )

        # Redirect with query param
        base_url = reverse('imam_schedule_side')
        query = urlencode({'status': 'success'})
        return redirect(f"{base_url}?{query}")

    messages.error(request, "Kaedah permintaan tidak sah.")
    return redirect('imam_schedule_sided')

def imam_leave_history(request):
    imam_id = request.session.get('user_id')
    if not imam_id:
        return redirect('login')  # redirect kalau tak login

    leave_requests = LeaveRequest.objects.filter(role_type='Imam', role_id=imam_id).order_by('-start_date')
    
    return render(request, 'imam/imamLeave.html', {
        'leave_requests': leave_requests
    })

def imam_attendance(request):
    imam_id = request.session.get('user_id')
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    # Dapatkan schedule imam untuk bulan ni
    duty_schedules = DutySchedule.objects.filter(
        role_type='Imam',
        role_id=imam_id,
        role_assigned=True,
        date__range=(first_day, last_day)
    ).order_by('date', 'prayer_time')

    attendance_records = []
    for duty in duty_schedules:
        record, created = AttendanceRecord.objects.get_or_create(
            role_type='Imam',
            role_id=imam_id,
            date=duty.date,
            prayer_time=duty.prayer_time,
            defaults={
                'role_performed': 'Imam',
                'attendance_status': '',  # belum ditandakan
            }
        )
        attendance_records.append(record)

    return render(request, 'imam/imamAttendance.html', {
        'attendance_records': attendance_records,
        'month': month,
        'year': year,
        'month_name': calendar.month_name[month],
    })

def mark_attendance(request):
    if request.method == 'POST':
        attendance_id = request.POST.get('attendance_id')
        status = request.POST.get('status')

        if attendance_id and status in ['Present', 'Absent']:
            record = get_object_or_404(AttendanceRecord, attendance_id=attendance_id)
            record.attendance_status = status
            record.save()
            messages.success(request, f"Kehadiran untuk {record.prayer_time} pada {record.date} dikemaskini.")
        else:
            messages.error(request, "Maklumat tidak lengkap untuk kemaskini kehadiran.")

    return redirect('imam_attendance')


#====JEMAAH SIDE======
from django.utils.timezone import now
import requests
from datetime import date
from django.shortcuts import render

def get_solat_api_aladhan():
    try:
        response = requests.get('https://api.aladhan.com/v1/timingsByAddress', params={
            'address': 'Arau, Perlis',
            'method': 3
        })
        if response.status_code == 200:
            data = response.json()['data']['timings']
            return {
                'Subuh': data['Fajr'],
                'Zohor': data['Dhuhr'],
                'Asar': data['Asr'],
                'Maghrib': data['Maghrib'],
                'Isyak': data['Isha']
            }
    except:
        pass

    return {
        'Subuh': 'N/A',
        'Zohor': 'N/A',
        'Asar': 'N/A',
        'Maghrib': 'N/A',
        'Isyak': 'N/A'
    }

def jemaah_home(request):
    today = date.today()
    jadual_today = PrayerSchedule.objects.filter(date=today)
    solat_times = get_solat_api_aladhan()

    # asing tugasan ikut waktu solat
    duty_by_prayer = {pt: None for pt in ["Subuh", "Zohor", "Asar", "Maghrib", "Isyak"]}
    for jadual in jadual_today:
        duty_by_prayer[jadual.prayer_time] = jadual

    context = {
        'solat_times': solat_times,
        'duty_by_prayer': duty_by_prayer,
    }
    return render(request, 'jemaah/homepage.html', context)

def jemaah_khutbah(request):
    today = now().date()
    upcoming = Khutbah.objects.filter(date__gte=today).order_by('date')
    past = Khutbah.objects.filter(date__lt=today).order_by('-date')

    return render(request, 'jemaah/khutbah.html', {
        'upcoming_khutbah': upcoming,
        'past_khutbah': past,
    })

def khutbah_detail(request, khutbah_id):
    khutbah = get_object_or_404(Khutbah, pk=khutbah_id)
    return render(request, 'jemaah/khutbahDetail.html', {'khutbah': khutbah})
