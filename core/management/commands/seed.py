from django.core.management.base import BaseCommand
from core.models import User
from hospitals.models import Hospital
from donors.models import Donor
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'Seed demo data'

    def handle(self, *args, **kwargs):
        if not User.objects.filter(username='demo').exists():
            u = User.objects.create_user(
                username='demo',
                password='demo1234',
                email='demo@lagosgeneral.com',
                first_name='Amara',
                last_name='Okafor',
            )
            Hospital.objects.create(
                user=u,
                name='Lagos General Hospital',
                license_number='LUTH',
                address='14 Marina Road, Lagos Island',
                city='Lagos',
                state='Lagos',
                phone='+2348012345678',
                email='demo@lagosgeneral.com',
                bank_name='GTBank',
                account_number='0123456789',
                account_name='Lagos General Hospital',
                is_verified=True,
            )
            self.stdout.write('Created: demo / demo1234')
        else:
            self.stdout.write('Demo user exists')

        blood_groups = ['A+','A-','B+','B-','AB+','AB-','O+','O-']
        cities = ['Lagos','Abuja','Port Harcourt','Ibadan']
        banks = ['GTBank','First Bank','Zenith Bank','Access Bank']
        names = [
            ('Chidi','Okonkwo'),('Ngozi','Adeyemi'),('Emeka','Nwankwo'),
            ('Fatima','Aliyu'),('Biodun','Adeleke'),('Sola','Adesanya'),
            ('Kemi','Bakare'),('Tunde','Fashola'),('Amaka','Obi'),
            ('Dayo','Adewale'),('Ifeanyi','Okeke'),('Aisha','Mohammed'),
            ('Segun','Williams'),('Chioma','Eze'),('Bayo','Ogundimu'),
        ]
        for fn, ln in names:
            email = f'{fn.lower()}.{ln.lower()}@example.com'
            if not Donor.objects.filter(email=email).exists():
                Donor.objects.create(
                    first_name=fn, last_name=ln, email=email,
                    phone=f'+2348{random.randint(10000000,99999999)}',
                    blood_group=random.choice(blood_groups),
                    age=random.randint(20, 45),
                    weight=round(random.uniform(55, 90), 1),
                    city=random.choice(cities), state='Lagos',
                    bank_name=random.choice(banks),
                    account_number=f'30{random.randint(10000000,99999999)}',
                    account_name=f'{fn} {ln}',
                    last_donation_date=date.today() - timedelta(days=random.randint(60,400)),
                    total_donations=random.randint(0, 10),
                    availability_score=round(random.uniform(0.5, 0.95), 2),
                    reliability_score=round(random.uniform(0.5, 0.95), 2),
                    response_rate=round(random.uniform(0.5, 0.95), 2),
                    source='n8n',
                )
        self.stdout.write(self.style.SUCCESS(f'Done. Donors: {Donor.objects.count()}'))
