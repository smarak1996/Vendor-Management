from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Vendor, PurchaseOrder, HistoricalPerformance
from .serializers import VendorSerializer, PurchaseOrderSerializer, HistoricalPerformanceSerializer
from django.db.models import Avg, F
from django.http import JsonResponse, HttpResponse
from datetime import datetime


class VendorListView(APIView):
    """
    API endpoint for listing and creating vendors.
    """
    def get(self, request):
        vendors = Vendor.objects.all()
        serializer = VendorSerializer(vendors, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = VendorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VendorDetailView(APIView):
    """
    API endpoint for retrieving, updating, and deleting a specific vendor.
    """
    def get_object(self, pk):
        return get_object_or_404(Vendor, pk=pk)

    def get(self, request, pk):
        vendor = self.get_object(pk)
        serializer = VendorSerializer(vendor)
        return Response(serializer.data)

    def put(self, request, pk):
        vendor = self.get_object(pk)
        serializer = VendorSerializer(vendor, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        vendor = self.get_object(pk)
        vendor.delete()
        return Response("Deleted Successfully", status=status.HTTP_204_NO_CONTENT)

class PurchaseOrderListView(APIView):
    """
    API endpoint for listing and creating purchase orders.
    """
    def get(self, request):
        purchase_orders = PurchaseOrder.objects.all()
        serializer = PurchaseOrderSerializer(purchase_orders, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PurchaseOrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class PurchaseOrderDetailView(APIView):
    """
    API endpoint for retrieving, updating, and deleting a specific purchase order.
    """
    def get_object(self, pk):
        return get_object_or_404(PurchaseOrder, pk=pk)

    def get(self, request, pk):
        purchase_order = self.get_object(pk)
        serializer = PurchaseOrderSerializer(purchase_order)
        return Response(serializer.data)

    def put(self, request, pk):
        purchase_order = self.get_object(pk)
        serializer = PurchaseOrderSerializer(purchase_order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        purchase_order = self.get_object(pk)
        purchase_order.delete()
        return Response("Deleted Successfully", status=status.HTTP_204_NO_CONTENT)
    

class AcknowledgePurchaseOrder(APIView):
    """
    API endpoint for acknowledging a purchase order and updating related metrics.
    """
    def post(self, request, po_id):
        try:
            purchase_order = PurchaseOrder.objects.get(pk=po_id)
        except PurchaseOrder.DoesNotExist:
            return JsonResponse({'error': 'Purchase Order not found'}, status=status.HTTP_404_NOT_FOUND)

        acknowledgment_date = request.data.get('acknowledgment_date')

        if acknowledgment_date:
            purchase_order.acknowledgment_date = acknowledgment_date
            purchase_order.save()

            vendor = purchase_order.vendor
            vendor.average_response_time = VendorPerformanceView.calculate_average_response_time(vendor=vendor)
            vendor.save()

            return JsonResponse({'message': 'Purchase Order acknowledged successfully'}, status=status.HTTP_200_OK)
        else:
            return JsonResponse({'error': 'Acknowledge date is required'}, status=status.HTTP_400_BAD_REQUEST)
        

    

class VendorPerformanceView(APIView):

    """
    API endpoint for retrieving performance metrics for a specific vendor.
    """
    def get(self, request, pk):
        import json
        vendor = self.get_object(pk)
        performance_metrics = {
            'on_time_delivery_rate': self.calculate_on_time_delivery_rate(vendor),
            'quality_rating_avg': self.calculate_quality_rating_avg(vendor),
            'average_response_time': self.calculate_average_response_time(vendor),
            'fulfillment_rate': self.calculate_fulfillment_rate(vendor),
        }
        self.update_historical_performance(vendor, performance_metrics)
        response = {"message": "Updated Historical Performance Table", "data":performance_metrics}
        return HttpResponse(json.dumps(response), content_type='application/json')

    def get_object(self, pk):
        try:
            return Vendor.objects.get(pk=pk)
        except Vendor.DoesNotExist:
            raise JsonResponse({'error': 'Vendor not found'}, status=status.HTTP_404_NOT_FOUND)

    @staticmethod
    def calculate_on_time_delivery_rate(vendor):
        """
         Calculate the on-time delivery rate for a vendor.
        """
        completed_pos = PurchaseOrder.objects.filter(vendor=vendor, status='completed')
        on_time_deliveries = completed_pos.filter(delivery_date__lte=F('acknowledgment_date')).count()
        total_completed_pos = completed_pos.count()
        return (on_time_deliveries / total_completed_pos) * 100 if total_completed_pos > 0 else 0
    
    @staticmethod
    def calculate_quality_rating_avg(vendor):
        """
        Calculate the average quality rating for a vendor.
        """
        completed_pos = PurchaseOrder.objects.filter(vendor=vendor, status='completed').exclude(quality_rating__isnull=True)
        return completed_pos.aggregate(Avg('quality_rating'))['quality_rating__avg'] or 0.0

    @staticmethod
    def calculate_average_response_time(vendor):
        """
        Calculate the average response time for a vendor.
        """
        acknowledged_pos = PurchaseOrder.objects.filter(vendor=vendor, acknowledgment_date__isnull=False)
        response_times = [(pos.acknowledgment_date - pos.issue_date).total_seconds() for pos in acknowledged_pos]
        return sum(response_times) / len(response_times) if len(response_times) > 0 else 0.0

    @staticmethod
    def calculate_fulfillment_rate(vendor):
        """
        Calculate the fulfillment rate for a vendor.
        """
        total_pos = PurchaseOrder.objects.filter(vendor=vendor)
        successful_fulfillments = total_pos.filter(status='completed').count()
        return (successful_fulfillments / total_pos.count()) * 100 if total_pos.count() > 0 else 0
    

    def update_historical_performance(self, vendor, metrics):
        """
        Update or create historical performance records for a vendor.

        """
        date_today = datetime.now()

        # Check if historical record for today exists, if not, create one
        historical_record, created = HistoricalPerformance.objects.get_or_create(
            vendor=vendor,
            date=date_today,
            defaults={
                'on_time_delivery_rate': metrics['on_time_delivery_rate'],
                'quality_rating_avg': metrics['quality_rating_avg'],
                'average_response_time': metrics['average_response_time'],
                'fulfillment_rate': metrics['fulfillment_rate'],
            }
        )

        if not created:
            # If record exists, update the metrics
            historical_record.on_time_delivery_rate = metrics['on_time_delivery_rate']
            historical_record.quality_rating_avg = metrics['quality_rating_avg']
            historical_record.average_response_time = metrics['average_response_time']
            historical_record.fulfillment_rate = metrics['fulfillment_rate']
            historical_record.save()

