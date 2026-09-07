from django.contrib import admin

from .models import Imam, Muazzin, Siak, PrayerSchedule, DutySchedule, Khutbah, JumaatPrayer, LeaveRequest, AttendanceRecord
admin.site.register(Imam)
admin.site.register(Muazzin)
admin.site.register(Siak)
admin.site.register(PrayerSchedule)
admin.site.register(DutySchedule)
admin.site.register(Khutbah)
admin.site.register(JumaatPrayer)
admin.site.register(LeaveRequest)
admin.site.register(AttendanceRecord)
