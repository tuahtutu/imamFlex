from django.db import models


ROLE_CHOICES = [
    ('Imam', 'Imam'),
    ('Muazzin', 'Muazzin'),
    ('Siak', 'Siak'),
]

APPROVAL_CHOICES = [
    ('Pending', 'Pending'),
    ('Approved', 'Approved'),
    ('Rejected', 'Rejected'),
]

ATTENDANCE_CHOICES = [
    ('Present', 'Present'),
    ('Absent', 'Absent'),
]

PRAYER_TIMES = [
    ('Subuh', 'Subuh'),
    ('Zohor', 'Zohor'),
    ('Asar', 'Asar'),
    ('Maghrib', 'Maghrib'),
    ('Isyak', 'Isyak'),
    ('Jumaat', 'Jumaat'),
]


class MosqueStaff(models.Model):
    name = models.CharField(max_length=100)
    ic_number = models.CharField(max_length=12, unique=True)
    contact_number = models.CharField(max_length=15)
    address = models.TextField(blank=True, null=True)
    availability = models.BooleanField(default=True)
    email = models.EmailField(blank=True, null=True) 
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class Imam(MosqueStaff):
    imam_id = models.CharField(max_length=10, primary_key=True)
    password = models.CharField(max_length=20)
    is_admin = models.BooleanField(default=False)

class Muazzin(MosqueStaff):
    muazzin_id = models.CharField(max_length=10, primary_key=True)
    password = models.CharField(max_length=20)


class Siak(MosqueStaff):
    siak_id = models.CharField(max_length=10, primary_key=True)
    password = models.CharField(max_length=20)


class PrayerSchedule(models.Model):
    date = models.DateField()
    prayer_time = models.CharField(max_length=20, choices=PRAYER_TIMES)
    imam = models.ForeignKey(Imam, on_delete=models.SET_NULL, null=True, blank=True)
    muazzin = models.ForeignKey(Muazzin, on_delete=models.SET_NULL, null=True, blank=True)
    siak = models.ForeignKey(Siak, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.date} - {self.prayer_time}"


class DutySchedule(models.Model):
    schedule_id = models.AutoField(primary_key=True)
    date = models.DateField()
    prayer_time = models.CharField(max_length=20, choices=PRAYER_TIMES)
    role_type = models.CharField(max_length=20, choices=ROLE_CHOICES)
    role_id = models.CharField(max_length=10)  
    role_assigned = models.BooleanField(default=True)
    replacement_role_id = models.CharField(max_length=10, null=True, blank=True)


class Khutbah(models.Model):
    khutbah_id = models.AutoField(primary_key=True)
    date = models.DateField()
    khutbah_topic = models.CharField(max_length=200)
    content = models.TextField()
    khatib = models.ForeignKey(Imam, on_delete=models.SET_NULL, null=True, blank=True) 

    def __str__(self):
        return f"{self.khutbah_topic} ({self.date})"


class JumaatPrayer(models.Model):
    jumaat_id = models.AutoField(primary_key=True)
    khutbah = models.ForeignKey(Khutbah, on_delete=models.CASCADE)
    imam = models.ForeignKey(Imam, on_delete=models.CASCADE)


class LeaveRequest(models.Model):
    request_id = models.AutoField(primary_key=True)
    role_type = models.CharField(max_length=20, choices=ROLE_CHOICES)
    role_id = models.CharField(max_length=10)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default='Pending')
    supporting_document = models.FileField(upload_to='leave_docs/', null=True, blank=True) 
    prayer_time = models.CharField(max_length=20, null=True, blank=True)
    


class AttendanceRecord(models.Model):
    attendance_id = models.AutoField(primary_key=True)
    role_type = models.CharField(max_length=20, choices=ROLE_CHOICES)
    role_id = models.CharField(max_length=10)
    date = models.DateField()
    prayer_time = models.CharField(max_length=20, choices=PRAYER_TIMES)
    role_performed = models.CharField(max_length=100)
    attendance_status = models.CharField(max_length=20, choices=ATTENDANCE_CHOICES)
    remarks = models.TextField(null=True, blank=True)

class SpecialNotice(models.Model):
    content = models.TextField()
    notice_date = models.DateField() 
    valid_until = models.DateField(null=True, blank=True)
    