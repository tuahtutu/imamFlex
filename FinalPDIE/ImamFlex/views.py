from django.shortcuts import render,redirect,get_object_or_404
from .models import Imam, Muazzin, Siak,PrayerSchedule,PRAYER_TIMES,DutySchedule,LeaveRequest,Khutbah,JumaatPrayer,AttendanceRecord,SpecialNotice   
from django.contrib import messages
from django.db.models import Q
from calendar import monthrange
import calendar
import datetime
from datetime import datetime,date,timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.timezone import now
import requests



def login(request):
    if request.method == 'POST':
        user_id = request.POST.get('username')
        password = request.POST.get('password')

       
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

        
        try:
            muazzin = Muazzin.objects.get(muazzin_id=user_id, password=password)
            request.session['user_id'] = muazzin.muazzin_id
            request.session['role'] = 'muazzin'
            return redirect('muazzinDash')
        except Muazzin.DoesNotExist:
            pass

        
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
    
    request.session.flush()

    
    messages.success(request, "Anda telah berjaya logout.")

    
    return redirect('login') 


def admin_dashboard(request):
    today = timezone.now().date()

    
    imam_schedule_today = DutySchedule.objects.filter(
    date=today, role_type='Imam'
)


   
    latest_khutbah = Khutbah.objects.order_by('-date').first()

   
    pending_leaves = LeaveRequest.objects.filter(approval_status='Pending')

    
    imam_count = Imam.objects.count()
    muazzin_count = Muazzin.objects.count()
    siak_count = Siak.objects.count()

    
    next_jumaat_khutbah = Khutbah.objects.filter(
    date__gt=today
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

        
        replacement_assigned = DutySchedule.objects.filter(
    role_type=leave.role_type,
    role_id=leave.role_id,
    date__range=[leave.start_date, leave.end_date],
    prayer_time=leave.prayer_time  
).exclude(replacement_role_id__isnull=True).exists()


        leave.replacement_assigned = replacement_assigned

        if replacement_assigned:
            replacement = DutySchedule.objects.filter(
    role_type=leave.role_type,
    role_id=leave.role_id,
    date__range=[leave.start_date, leave.end_date],
    prayer_time=leave.prayer_time
).exclude(replacement_role_id__isnull=True).first()


            
            replacement_model = {'Imam': Imam, 'Muazzin': Muazzin, 'Siak': Siak}.get(leave.role_type)
            if replacement_model:
                rep_staff = replacement_model.objects.filter(pk=replacement.replacement_role_id).first()
                leave.replacement_name = rep_staff.name if rep_staff else 'Tidak Dikenali'
            else:
                leave.replacement_name = 'Tidak Dikenali'
        else:
            leave.replacement_name = None

    context = {'leaves': leaves}
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



def assign_replacement(request, request_id):
    leave = get_object_or_404(LeaveRequest, request_id=request_id)

    RoleModel = {
        'Imam': Imam,
        'Muazzin': Muazzin,
        'Siak': Siak
    }.get(leave.role_type)

    if not RoleModel:
        messages.error(request, "Invalid role type.")
        return redirect('admin_leave_list')

    if request.method == 'POST':
        replacement_id = request.POST.get('replacement')

        DutySchedule.objects.filter(
            role_type=leave.role_type,
            role_id=leave.role_id,
            date__range=[leave.start_date, leave.end_date],
            prayer_time=leave.prayer_time
        ).update(replacement_role_id=replacement_id)

        
        try:
            replacement = RoleModel.objects.get(**{f"{leave.role_type.lower()}_id": replacement_id})
            replacement_name = replacement.name
        except:
            replacement_name = "Pengganti"

        
        current_date = leave.start_date
        while current_date <= leave.end_date:
            notice_text = f"{leave.role_type} bagi solat {leave.prayer_time} pada {current_date.strftime('%d/%m/%Y')} telah digantikan oleh {replacement_name}."

            SpecialNotice.objects.create(
                content=notice_text,
                notice_date=current_date ,
                valid_until=current_date 
            )
            current_date += timedelta(days=1)

        messages.success(request, f'Pengganti berjaya ditugaskan untuk {leave.role_type}.')
        return redirect('admin_leave_list')

    staff_list = RoleModel.objects.exclude(**{f"{leave.role_type.lower()}_id": leave.role_id})

    return render(request, 'admin/assignReplacement.html', {
        'leave': leave,
        'staff_list': staff_list,
    })


#Part Imam SIDEEEE
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
        email = request.POST.get('email')
        contact_number = request.POST.get('contact_number')
        address = request.POST.get('address')
        password = request.POST.get('password')

        Imam.objects.create(
            imam_id=imam_id,
            name=name,
            ic_number=ic_number,
            email=email,
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

    # ni utk simpan/publish schedule imam tu
    if request.method == 'POST':
        if 'publishMonthBtn' in request.POST:
            duty_qs = DutySchedule.objects.filter(
                date__year=year,
                date__month=month,
                role_type='Imam'
            )
            duty_qs.update(role_assigned=True)

            
            for duty in duty_qs:
                
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
                        imam_id = schedule.replacement_role_id if schedule.replacement_role_id else schedule.role_id
                        imam = Imam.objects.filter(imam_id=imam_id).first()
                        daily_prayers[schedule.prayer_time] = imam.name if imam else "?"

                week_data.append({'date': day, 'prayers': daily_prayers})
            else:
                week_data.append(None)
        calendar_data.append(week_data)

  #utk year dengan month dropdown
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
        khutbah_topic = request.POST.get('khutbah_topic')
        content = request.POST.get('content')
        imam_id = request.POST.get('imam_id')

        imam = get_object_or_404(Imam, imam_id=imam_id)  

        khutbah = Khutbah.objects.create(
            date=date,
            khutbah_topic=khutbah_topic,
            content=content,
            khatib=imam  
        )

        from .models import JumaatPrayer
        JumaatPrayer.objects.create(khutbah=khutbah, imam=imam)

        messages.success(request, 'Khutbah berjaya ditambah!')
        return redirect('khutbah_list')

    imams = Imam.objects.all()
    return render(request, 'admin/addKhutbah.html', {'imams': imams})


def edit_khutbah(request, khutbah_id):
    khutbah = get_object_or_404(Khutbah, pk=khutbah_id)
    jumaat = khutbah.jumaatprayer_set.first()

    if request.method == 'POST':
        khutbah.date = request.POST.get('date')
        khutbah.khutbah_topic = request.POST.get('khutbah_topic')
        khutbah.content = request.POST.get('content')

        imam_id = request.POST.get('imam_id')
        imam = get_object_or_404(Imam, imam_id=imam_id)

        khutbah.khatib = imam  
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



def delete_khutbah(request, khutbah_id):
    khutbah = get_object_or_404(Khutbah, pk=khutbah_id)
    khutbah.delete()
    messages.warning(request, 'Khutbah telah dipadam.')
    return redirect('khutbah_list')


#===================REPORT=============
def admin_attendance_report(request):
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    selected_staff_id = request.GET.get('staff_id', '')

    selected_type = ''
    selected_id = ''
    filtered_attendance = []

    
    staff_list = []

    for imam in Imam.objects.all():
        staff_list.append({
            'role_type': 'Imam',
            'role_id': imam.imam_id,
            'name': imam.name
        })

    for muazzin in Muazzin.objects.all():
        staff_list.append({
            'role_type': 'Muazzin',
            'role_id': muazzin.muazzin_id,
            'name': muazzin.name
        })

    for siak in Siak.objects.all():
        staff_list.append({
            'role_type': 'Siak',
            'role_id': siak.siak_id,
            'name': siak.name
        })

    # ni nak filter attendance
    if selected_staff_id:
        try:
            selected_type, selected_id = selected_staff_id.split('-')
            selected_type = selected_type.capitalize()
            selected_id = selected_id.upper()

            filtered_attendance = AttendanceRecord.objects.filter(
                role_type__iexact=selected_type,
                role_id__iexact=selected_id,
                date__year=year,
                date__month=month
            ).order_by('date', 'prayer_time')
        except ValueError:
            filtered_attendance = []
    else:
        filtered_attendance = AttendanceRecord.objects.filter(
            date__year=year,
            date__month=month
        ).order_by('date', 'prayer_time')

    return render(request, 'admin/adminAttendance.html', {
        'attendance_records': filtered_attendance,
        'staff_list': staff_list,
        'selected_type': selected_type,
        'selected_id': selected_id,
        'month': month,
        'year': year,
        'month_list': range(1, 13),
        'month_name': calendar.month_name[month],
    })

#=!!!!!IMAM SIDE!!!!=#

def imam_dashboard(request):
    imam_id = request.session.get('user_id')
    if not imam_id:
        return redirect('login')

    imam = Imam.objects.get(imam_id=imam_id)
    today = date.today()

    imam_schedule_today = PrayerSchedule.objects.filter(date=today, imam=imam)

    first_day = today.replace(day=1)
    last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    replacement_this_month = DutySchedule.objects.filter(
        role_type='Imam',
        replacement_role_id=imam_id,
        date__range=(first_day, last_day),
        role_assigned=True
    ).order_by('date')

    upcoming_khutbah = Khutbah.objects.filter(
        khatib=imam,
        date__gte=today
    ).order_by('date').first()

    return render(request, 'imam/imamDash.html', {
        'imam': imam,
        'imam_schedule_today': imam_schedule_today,
        'replacement_this_month': replacement_this_month,
        'upcoming_khutbah': upcoming_khutbah,
        'month_name': calendar.month_name[today.month],
        'today': today,
    })


def imam_profile(request):
    imam_id = request.session.get('user_id')
    imam = Imam.objects.get(imam_id=imam_id)

    if request.method == 'POST':
        imam.name = request.POST.get('name')
        imam.contact_number = request.POST.get('contact_number')
        imam.email = request.POST.get('email')
        imam.address = request.POST.get('address')

        if 'profile_picture' in request.FILES:
            imam.profile_picture = request.FILES['profile_picture']

        imam.save()
        return redirect('imam_profile')

    context = {
        'imam': imam,
        'today': date.today()
    }
    return render(request, 'imam/imamProfile.html', context)

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
        date__range=(first_day, last_day),
        role_assigned=True
    ).filter(
        Q(role_id=imam_id) | Q(replacement_role_id=imam_id)
    )

    
    leave_requests = LeaveRequest.objects.filter(
        role_type='Imam',
        role_id=imam_id,
        approval_status='Approved',
        start_date__lte=last_day,
        end_date__gte=first_day
    )

    leave_dates = set()
    for leave in leave_requests:
        current = leave.start_date
        while current <= leave.end_date:
            leave_dates.add((current, leave.prayer_time))
            current += timedelta(days=1)

    
    cal = calendar.Calendar(firstweekday=6)
    month_matrix = cal.monthdatescalendar(year, month)

    calendar_data = []
    for week in month_matrix:
        week_data = []
        for day in week:
            if day.month == month:
                daily_duties = []
                for sched in schedules:
                    if sched.date == day and (sched.role_id == imam_id or sched.replacement_role_id == imam_id):
                        
                        if (day, sched.prayer_time) in leave_dates:
                            continue

                        duty = {
                            'prayer_time': sched.prayer_time,
                            'is_replacement': sched.replacement_role_id == imam_id
                        }
                        daily_duties.append(duty)
                week_data.append({'date': day, 'duties': daily_duties})
            else:
                week_data.append(None)
        calendar_data.append(week_data)

    years = list(range(today.year, today.year + 5))
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]
    show_modal_success = request.GET.get('status') == 'success'


    return render(request, 'imam/Schedule.html', {
        'calendar': calendar_data,
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'years': years,
        'months': months,
        'show_modal_success': show_modal_success,
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
            supporting_document=doc,
            prayer_time=prayer,
        )

       
        base_url = reverse('imam_schedule_side')
        query = urlencode({'status': 'success'})
        return redirect(f"{base_url}?{query}")

    messages.error(request, "Kaedah permintaan tidak sah.")
    return redirect('imam_schedule_sided')

def imam_leave_history(request):
    imam_id = request.session.get('user_id')
    if not imam_id:
        return redirect('login')  

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
                'attendance_status': '',  
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
        remarks = request.POST.get('remarks', '')

        if attendance_id and status in ['Present', 'Absent']:
            record = get_object_or_404(AttendanceRecord, attendance_id=attendance_id)
            record.attendance_status = status
            if status == 'Absent':
                record.remarks = remarks  
            record.save()
            messages.success(request, f"Kehadiran untuk {record.prayer_time} pada {record.date} dikemaskini.")
        else:
            messages.error(request, "Maklumat tidak lengkap untuk kemaskini kehadiran.")
    
    return redirect('imam_attendance')

#=========MUAZZIN SIDE=============
def muazzin_dashboard(request):
    muazzin_id = request.session.get('user_id')
    if not muazzin_id:
        return redirect('login')

    muazzin = Muazzin.objects.get(muazzin_id=muazzin_id)
    today = date.today()

    muazzin_schedule_today = DutySchedule.objects.filter(
       date=today,
       role_type='Muazzin',
       role_id=muazzin_id,
       role_assigned=True
     )

    first_day = today.replace(day=1)
    last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    replacement_this_month = DutySchedule.objects.filter(
        role_type='Muazzin',
        replacement_role_id=muazzin_id,
        date__range=(first_day, last_day),
        role_assigned=True
    ).order_by('date')

    return render(request, 'muazzin/muazzinDash.html', {
        'muazzin': muazzin,
        'muazzin_schedule_today': muazzin_schedule_today,
        'replacement_this_month': replacement_this_month,
        'month_name': calendar.month_name[today.month],
        'today': today,
    })

def muazzin_profile(request):
    muazzin_id = request.session.get('user_id')
    muazzin = Muazzin.objects.get(muazzin_id=muazzin_id)

    if request.method == 'POST':
        muazzin.name = request.POST.get('name')
        muazzin.contact_number = request.POST.get('contact_number')
        muazzin.email = request.POST.get('email')
        muazzin.address = request.POST.get('address')

        if 'profile_picture' in request.FILES:
            muazzin.profile_picture = request.FILES['profile_picture']

        muazzin.save()
        return redirect('muazzin_profile')

    context = {
        'muazzin': muazzin,
        'today': date.today()
    }
    return render(request, 'muazzin/muazzinProfile.html', context)


def muazzin_schedule_side(request):
    muazzin_id = request.session.get('user_id')
    muazzin = get_object_or_404(Muazzin, muazzin_id=muazzin_id)

    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    schedules = DutySchedule.objects.filter(
        role_type='Muazzin',
        date__range=(first_day, last_day),
        role_assigned=True
    ).filter(
        Q(role_id=muazzin_id) | Q(replacement_role_id=muazzin_id)
    )

    leave_requests = LeaveRequest.objects.filter(
        role_type='Muazzin',
        role_id=muazzin_id,
        approval_status='Approved',
        start_date__lte=last_day,
        end_date__gte=first_day
    )

    leave_dates = set()
    for leave in leave_requests:
        current = leave.start_date
        while current <= leave.end_date:
            leave_dates.add((current, leave.prayer_time))
            current += timedelta(days=1)

    cal = calendar.Calendar(firstweekday=6)
    month_matrix = cal.monthdatescalendar(year, month)

    calendar_data = []
    for week in month_matrix:
        week_data = []
        for day in week:
            if day.month == month:
                daily_duties = []
                for sched in schedules:
                    if sched.date == day and (sched.role_id == muazzin_id or sched.replacement_role_id == muazzin_id):
                        if (day, sched.prayer_time) in leave_dates:
                            continue
                        duty = {
                            'prayer_time': sched.prayer_time,
                            'is_replacement': sched.replacement_role_id == muazzin_id
                        }
                        daily_duties.append(duty)
                week_data.append({'date': day, 'duties': daily_duties})
            else:
                week_data.append(None)
        calendar_data.append(week_data)

    years = list(range(today.year, today.year + 5))
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]
    show_modal_success = request.GET.get('status') == 'success'

    return render(request, 'muazzin/muazzinScheduleSide.html', {
        'calendar': calendar_data,
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'years': years,
        'months': months,
        'show_modal_success': show_modal_success,
    })

def apply_leave_muazzin(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        prayer = request.POST.get('prayer_time')
        reason = request.POST.get('reason')
        doc = request.FILES.get('supporting_document')

        if not (date_str and prayer and reason):
            messages.error(request, "Sila lengkapkan semua maklumat permohonan.")
            return redirect('muazzin_schedule_side')

        try:
            date_obj = datetime.strptime(date_str, "%B %d, %Y").date()
        except ValueError:
            messages.error(request, "Tarikh tidak sah.")
            return redirect('muazzin_schedule_side')

        muazzin_id = request.session.get('user_id')
        LeaveRequest.objects.create(
            role_type='Muazzin',
            role_id=muazzin_id,
            start_date=date_obj,
            end_date=date_obj,
            reason=reason,
            supporting_document=doc,
            prayer_time=prayer,
        )

        base_url = reverse('muazzin_schedule_side')
        query = urlencode({'status': 'success'})
        return redirect(f"{base_url}?{query}")

    messages.error(request, "Kaedah permintaan tidak sah.")
    return redirect('muazzin_schedule_side')

def muazzin_leave_history(request):
    muazzin_id = request.session.get('user_id')
    if not muazzin_id:
        return redirect('login')  

    leave_requests = LeaveRequest.objects.filter(
        role_type='Muazzin',
        role_id=muazzin_id
    ).order_by('-start_date')
    
    return render(request, 'muazzin/muazzinLeave.html', {
        'leave_requests': leave_requests
    })

def muazzin_attendance(request):
    muazzin_id = request.session.get('user_id')
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    duty_schedules = DutySchedule.objects.filter(
        role_type='Muazzin',
        role_id=muazzin_id,
        role_assigned=True,
        date__range=(first_day, last_day)
    ).order_by('date', 'prayer_time')

    attendance_records = []
    for duty in duty_schedules:
        record, created = AttendanceRecord.objects.get_or_create(
            role_type='Muazzin',
            role_id=muazzin_id,
            date=duty.date,
            prayer_time=duty.prayer_time,
            defaults={
                'role_performed': 'Muazzin',
                'attendance_status': '',
            }
        )
        attendance_records.append(record)

    return render(request, 'muazzin/muazzinAttendance.html', {
        'attendance_records': attendance_records,
        'month': month,
        'year': year,
        'month_name': calendar.month_name[month],
    })


def mark_attendance_muazzin(request):
    if request.method == 'POST':
        attendance_id = request.POST.get('attendance_id')
        status = request.POST.get('status')
        remarks = request.POST.get('remarks', '')

        if attendance_id and status in ['Present', 'Absent']:
            record = get_object_or_404(AttendanceRecord, attendance_id=attendance_id)
            if record.role_type != 'Muazzin':
                messages.error(request, "Rekod ini bukan milik Muazzin.")
                return redirect('muazzin_attendance')
            
            record.attendance_status = status
            if status == 'Absent':
                record.remarks = remarks
            record.save()
            messages.success(request, f"Kehadiran untuk {record.prayer_time} pada {record.date} dikemaskini.")
        else:
            messages.error(request, "Maklumat tidak lengkap untuk kemaskini kehadiran.")

    return redirect('muazzin_attendance')


#===SIAK SIDE=====
def siak_dashboard(request):
    siak_id = request.session.get('user_id')
    if not siak_id:
        return redirect('login')

    siak = Siak.objects.get(siak_id=siak_id)
    today = date.today()

    siak_schedule_today = DutySchedule.objects.filter(
    date=today,
    role_type='Siak',
    role_id=siak_id,
    role_assigned=True
)


    first_day = today.replace(day=1)
    last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    replacement_this_month = DutySchedule.objects.filter(
        role_type='Siak',
        replacement_role_id=siak_id,
        date__range=(first_day, last_day),
        role_assigned=True
    ).order_by('date')

    return render(request, 'siak/siakDash.html', {
        'siak': siak,
        'siak_schedule_today': siak_schedule_today,
        'replacement_this_month': replacement_this_month,
        'month_name': calendar.month_name[today.month],
        'today': today,
    })

def siak_profile(request):
    siak_id = request.session.get('user_id')
    siak = Siak.objects.get(siak_id=siak_id)

    if request.method == 'POST':
        siak.name = request.POST.get('name')
        siak.contact_number = request.POST.get('contact_number')
        siak.email = request.POST.get('email')
        siak.address = request.POST.get('address')

        if 'profile_picture' in request.FILES:
            siak.profile_picture = request.FILES['profile_picture']

        siak.save()
        return redirect('siak_profile')

    context = {
        'siak': siak,
        'today': date.today()
    }
    return render(request, 'siak/siakProfile.html', context)

def siak_schedule_side(request):
    siak_id = request.session.get('user_id')
    siak = get_object_or_404(Siak, siak_id=siak_id)

    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    schedules = DutySchedule.objects.filter(
        role_type='Siak',
        date__range=(first_day, last_day),
        role_assigned=True
    ).filter(
        Q(role_id=siak_id) | Q(replacement_role_id=siak_id)
    )

    leave_requests = LeaveRequest.objects.filter(
        role_type='Siak',
        role_id=siak_id,
        approval_status='Approved',
        start_date__lte=last_day,
        end_date__gte=first_day
    )

    leave_dates = set()
    for leave in leave_requests:
        current = leave.start_date
        while current <= leave.end_date:
            leave_dates.add((current, leave.prayer_time))
            current += timedelta(days=1)

    cal = calendar.Calendar(firstweekday=6)
    month_matrix = cal.monthdatescalendar(year, month)

    calendar_data = []
    for week in month_matrix:
        week_data = []
        for day in week:
            if day.month == month:
                daily_duties = []
                for sched in schedules:
                    if sched.date == day and (sched.role_id == siak_id or sched.replacement_role_id == siak_id):
                        if (day, sched.prayer_time) in leave_dates:
                            continue
                        duty = {
                            'prayer_time': sched.prayer_time,
                            'is_replacement': sched.replacement_role_id == siak_id
                        }
                        daily_duties.append(duty)
                week_data.append({'date': day, 'duties': daily_duties})
            else:
                week_data.append(None)
        calendar_data.append(week_data)

    show_modal_success = request.GET.get('status') == 'success'

    return render(request, 'siak/siakScheduleSide.html', {
        'calendar': calendar_data,
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'show_modal_success': show_modal_success,
    })

def apply_leave_siak(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        prayer = request.POST.get('prayer_time')
        reason = request.POST.get('reason')
        doc = request.FILES.get('supporting_document')

        if not (date_str and prayer and reason):
            messages.error(request, "Sila lengkapkan semua maklumat permohonan.")
            return redirect('siak_schedule_side')

        try:
            date_obj = datetime.strptime(date_str, "%B %d, %Y").date()
        except ValueError:
            messages.error(request, "Tarikh tidak sah.")
            return redirect('siak_schedule_side')

        siak_id = request.session.get('user_id')
        LeaveRequest.objects.create(
            role_type='Siak',
            role_id=siak_id,
            start_date=date_obj,
            end_date=date_obj,
            reason=reason,
            supporting_document=doc,
            prayer_time=prayer,
        )

        base_url = reverse('siak_schedule_side')
        query = urlencode({'status': 'success'})
        return redirect(f"{base_url}?{query}")

    messages.error(request, "Kaedah permintaan tidak sah.")
    return redirect('siak_schedule_side')

def siak_leave_history(request):
    siak_id = request.session.get('user_id')
    if not siak_id:
        return redirect('login')

    leave_requests = LeaveRequest.objects.filter(
        role_type='Siak',
        role_id=siak_id
    ).order_by('-start_date')

    return render(request, 'siak/siakLeave.html', {
        'leave_requests': leave_requests
    })

def siak_attendance(request):
    siak_id = request.session.get('user_id')
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    duty_schedules = DutySchedule.objects.filter(
        role_type='Siak',
        role_id=siak_id,
        role_assigned=True,
        date__range=(first_day, last_day)
    ).order_by('date', 'prayer_time')

    attendance_records = []
    for duty in duty_schedules:
        record, created = AttendanceRecord.objects.get_or_create(
            role_type='Siak',
            role_id=siak_id,
            date=duty.date,
            prayer_time=duty.prayer_time,
            defaults={
                'role_performed': 'Siak',
                'attendance_status': '',
            }
        )
        attendance_records.append(record)

    return render(request, 'siak/siakAttendance.html', {
        'attendance_records': attendance_records,
        'month': month,
        'year': year,
        'month_name': calendar.month_name[month],
    })


def mark_attendance_siak(request):
    if request.method == 'POST':
        attendance_id = request.POST.get('attendance_id')
        status = request.POST.get('status')
        remarks = request.POST.get('remarks', '')

        if attendance_id and status in ['Present', 'Absent']:
            record = get_object_or_404(AttendanceRecord, attendance_id=attendance_id)
            if record.role_type != 'Siak':
                messages.error(request, "Rekod ini bukan milik Siak.")
                return redirect('siak_attendance')
            
            record.attendance_status = status
            if status == 'Absent':
                record.remarks = remarks
            record.save()
            messages.success(request, f"Kehadiran untuk {record.prayer_time} pada {record.date} dikemaskini.")
        else:
            messages.error(request, "Maklumat tidak lengkap untuk kemaskini kehadiran.")

    return redirect('siak_attendance')



#====JEMAAH SIDE======


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
    solat_times = get_solat_api_aladhan()

    prayer_slots = ["Subuh", "Zohor", "Asar", "Maghrib", "Isyak"]
    duty_by_prayer = {}

    for waktu in prayer_slots:
        tugas = DutySchedule.objects.filter(date=today, prayer_time=waktu, role_assigned=True)
        
        imam = muazzin = siak = None

        for t in tugas:
            id_to_use = t.replacement_role_id if t.replacement_role_id else t.role_id

            if t.role_type == 'Imam':
                imam = Imam.objects.filter(imam_id=id_to_use).first()
            elif t.role_type == 'Muazzin':
                muazzin = Muazzin.objects.filter(muazzin_id=id_to_use).first()
            elif t.role_type == 'Siak':
                siak = Siak.objects.filter(siak_id=id_to_use).first()

        duty_by_prayer[waktu] = {
            'imam': imam,
            'muazzin': muazzin,
            'siak': siak
        }

    notices = SpecialNotice.objects.filter(notice_date=today)

    return render(request, 'jemaah/homepage.html', {
        'solat_times': solat_times,
        'duty_by_prayer': duty_by_prayer,
        'notices': notices
    })

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


from django.core.mail import send_mail

def send_manual_reminder(request):
    if request.method == 'POST':
        today = date.today()
        duties = DutySchedule.objects.filter(date=today)

        for duty in duties:
            recipient = None
            name = ""
            role = duty.role_type

            if role == 'Imam':
                recipient = Imam.objects.filter(imam_id=duty.role_id).first()
                name = recipient.name if recipient else ""
            elif role == 'Muazzin':
                recipient = Muazzin.objects.filter(muazzin_id=duty.role_id).first()
                name = recipient.name if recipient else ""
            elif role == 'Siak':
                recipient = Siak.objects.filter(siak_id=duty.role_id).first()
                name = recipient.name if recipient else ""

            if recipient and recipient.email:
                # Send email
                send_mail(
                    subject='[ImamFlex] Peringatan Tugas Hari Ini',
                    message=f'Assalamualaikum {name},\n\nAnda dijadualkan bertugas sebagai {role} hari ini untuk waktu solat {duty.prayer_time}.\n\nSila hadir tepat pada waktunya.\n\nBarakallahu fiikum.',
                    from_email='irdinaizzraimy@gmail.com',  
                    recipient_list=[recipient.email],  
                    fail_silently=True
                )

        messages.success(request, "Peringatan berjaya dihantar kepada semua petugas hari ini.")
        return redirect('adminDash')

def ajk_info(request):
    imam_list = Imam.objects.all()
    muazzin_list = Muazzin.objects.all()
    siak_list = Siak.objects.all()

    return render(request, 'jemaah/ajkInfo.html', {
        'imam_list': imam_list,
        'muazzin_list': muazzin_list,
        'siak_list': siak_list,
    })
