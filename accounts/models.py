from django.db import models
from django.contrib.auth.models import AbstractUser
import random

class User(AbstractUser):
    ROLE_CHOICES =  (
        ('ADMIN' , 'admin') ,
        ('SUPERWISER' , 'superwiser') ,
        ('WORKER' , 'worker')
    )

    role = models.CharField(max_length=50 , choices=ROLE_CHOICES , default = 'WORKER')
    superwiser = models.ForeignKey( "self" , on_delete= models.SET_NULL , null=True , blank =True, related_name= "workers" , limit_choices_to =  {'role': 'SUPERWISER'})
    superwiser_code = models.CharField(max_length = 5 , unique= True , null= True)
    phone_number = models.CharField(max_length=10 , null=True)
    worker_id = models.CharField(max_length=8, unique=True, null =True , blank = True)
    


    def save(self, *args , **kwargs):
        if self.role == "SUPERWISER" and not self.superwiser_code:

            while True:
                new_id = self.superwiser_code =str(random.randint(10000,99999))

                if not User.objects.filter(superwiser_id = new_id).exists():
                    self.superwiser_code = new_id
                    break


        if self.role == "WORKER"  and not self.worker_id:

            while True:
                new_id = self.worker_id = str(random.randint(10000000 , 99999999))

                if not User.objects.filter(worker_id = new_id).exists():
                    self.worker_id = new_id
                    break
        
        return super().save(*args , **kwargs)

    def __str__(self):
        return self.username

    


