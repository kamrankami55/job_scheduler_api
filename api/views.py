import time
from django.shortcuts import render
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from scrapyd_api import ScrapydAPI
from api.models import ScrapperDetails
from api.management.commands.run_scrapping import Command
from django.conf import settings
import os

User = get_user_model()

def get_results(job_status):
        if job_status == 'pending':
            job_status = 'PEN'
        elif job_status == 'running':
            job_status = 'RUN'
        else:
            job_status = 'FIN'
        return job_status

class ExecuteScrapper(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            Command.handle(self)

            # User scrapydAPI
            filename = '{}/{}_dice_jobs.csv'.format(settings.ACCEPTED_CSV,int(time.time()))
            job_detail = request.data.get('job')
            location_detail = request.data.get('location')
            scrapyd = ScrapydAPI('http://localhost:6800')
            job_id = scrapyd.schedule('artworks', 'dice_jobs', job=job_detail, location=location_detail,filename=filename)
            time.sleep(10)
            state = scrapyd.job_status('artworks', job_id)
            state = get_results(state)
            ScrapperDetails.objects.create(job_id=job_id,job=job_detail,location=location_detail,csv_path=filename, result_status=state)

            return Response({'error': '', 'error_code': '', 'data': {"job_id": job_id, "status":state}}, status=200)
        except Exception as error:
            return Response({'error': repr(error), 'error_code': 'H007'}, status=400)

class CancelScrapper(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            if request.data.get('job_id'):
                scrapyd = ScrapydAPI('http://127.0.0.1:6800/cancel.json')
                scrapyd.cancel('artworks', request.data.get('job_id'))
                return Response({'error': '', 'error_code': '', 'data': 'Job cancelled successfully....!'}, status=200)
            else:
                return Response({'error': 'Please provide job id', 'error_code': '', 'data': {}}, status=200)   
        except Exception as error:
            return Response({'error': repr(error), 'error_code': 'H007'}, status=400)

class ListScrapperDetails(APIView):
    def get(self,request):
        try:
            scrapper_details=ScrapperDetails.objects.all().values("job_id","job","location","created_on","result_status")
            return Response({'error': '', 'error_code': '', 'data': {scrapper_details}}, status=200)
        except Exception as error:
            return Response({'error': repr(error), 'error_code': 'H007'}, status=400)

class ScrapperStatus(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            if request.data.get('job_id'):
                scrapyd = ScrapydAPI('http://localhost:6800')
                job_status = scrapyd.job_status('artworks',request.data.get('job_id'))
                scrap_details=ScrapperDetails.objects.filter(job_id=request.data.get('job_id'))
                if scrap_details.exists():
                    job_status = get_results(job_status)
                    scrapper = scrap_details[0]
                    scrapper.result_status = job_status
                    scrapper.save()
                    if os.path.exists(scrapper.csv_path) and scrapper.result_status == 'FIN' :
                        return Response({'error': '', 'error_code': '', 'data': {"status": job_status,'csv_path':scrapper.csv_path}}, status=200)
                    else:
                        return Response({'error': '', 'error_code': '', 'data': {"status": job_status,'csv_path':''}}, status=200) 
                else:
                    return Response({'error': 'Given job id does not exist.', 'error_code': '', 'data': {}}, status=200)   
            else:
                return Response({'error': 'Please provide job id', 'error_code': '', 'data': {}}, status=200)   
        except Exception as error:
            return Response({'error': repr(error), 'error_code': 'H007'}, status=400)