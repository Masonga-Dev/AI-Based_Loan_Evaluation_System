from django.shortcuts import render

def loan_applications(request):
    # You can add context with real data later
    return render(request, 'admin_dashboard/loan_applications.html')

def uploaded_documents(request):
    return render(request, 'admin_dashboard/uploaded_documents.html')

def ocr_data(request):
    return render(request, 'admin_dashboard/ocr_data.html')

def ai_predictions(request):
    return render(request, 'admin_dashboard/ai_predictions.html')

def approve_reject(request):
    return render(request, 'admin_dashboard/approve_reject.html')

def flag_documents(request):
    return render(request, 'admin_dashboard/flag_documents.html')
