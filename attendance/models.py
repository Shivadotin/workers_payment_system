from django.db import models
from django.conf import settings

class Attendance(models.Model):
    STATUS_CHOICES = (
        ('PRESENT' , "present") ,
        ('ABSENT' , "absent") ,
    )

    worker = models.ForeignKey(settings.AUTH_USER_MODEL , on_delete= models.CASCADE , related_name= "attendance")
    date = models.DateField()
    status =  models.CharField(max_length= 20  , choices=STATUS_CHOICES) 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("worker" , "date")

    def __str__(self):
        return f"{ self.worker.username} - { self.date } - {self.date } - {self.status}"
