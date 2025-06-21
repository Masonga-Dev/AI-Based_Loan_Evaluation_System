from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from apps.loan_application.models import LoanApplication
from apps.ai_evaluation.models import PredictionResult


def health_check(request):
    """
    Health check endpoint for monitoring
    """
    return JsonResponse({
        'status': 'healthy',
        'timestamp': '2024-01-01T00:00:00Z',
        'version': '1.0.0'
    })


class ApplicationAPIView(APIView):
    """
    API view for loan applications
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get list of applications
        """
        if request.user.role == 'applicant':
            applications = LoanApplication.objects.filter(applicant=request.user)
        else:
            applications = LoanApplication.objects.all()

        data = []
        for app in applications[:20]:  # Limit to 20 for performance
            data.append({
                'id': str(app.id),
                'application_number': app.application_number,
                'applicant_name': app.applicant.get_full_name(),
                'loan_amount': str(app.loan_amount),
                'status': app.status,
                'created_at': app.created_at.isoformat(),
                'ai_score': str(app.ai_score) if app.ai_score else None,
                'risk_level': app.risk_level,
            })

        return Response({
            'count': len(data),
            'results': data
        })


class PredictionAPIView(APIView):
    """
    API view for AI predictions
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get list of predictions
        """
        if request.user.role not in ['officer', 'manager', 'admin']:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        predictions = PredictionResult.objects.all()[:20]

        data = []
        for pred in predictions:
            data.append({
                'id': str(pred.id),
                'application_id': str(pred.application.id),
                'application_number': pred.application.application_number,
                'prediction_type': pred.prediction_type,
                'confidence_score': str(pred.confidence_score),
                'created_at': pred.created_at.isoformat(),
                'model_version': pred.model_version,
            })

        return Response({
            'count': len(data),
            'results': data
        })
