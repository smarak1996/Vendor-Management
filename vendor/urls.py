from django.urls import path
from .views import VendorListView, VendorDetailView, PurchaseOrderListView,\
    PurchaseOrderDetailView, VendorPerformanceView, AcknowledgePurchaseOrder

urlpatterns = [
    path('vendors/', VendorListView.as_view(), name='vendor-list'),
    path('vendors/<int:pk>/', VendorDetailView.as_view(), name='vendor-detail'),
    path('purchase_orders/', PurchaseOrderListView.as_view(), name='purchaseorder-list'),
    path('purchase_orders/<int:pk>/', PurchaseOrderDetailView.as_view(), name='purchaseorder-detail'),
    path('vendors/<int:pk>/performance/', VendorPerformanceView.as_view(), name='vendor-performance'),
    path('purchase_orders/<int:po_id>/acknowledge/', AcknowledgePurchaseOrder.as_view(), name='acknowledge-purchase-order'),

]