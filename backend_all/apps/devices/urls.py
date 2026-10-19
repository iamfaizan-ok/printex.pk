from django.urls import path
from .views import (
    AgentHeartbeatView,
    AgentClaimJobView,
    AgentJobDownloadView,
    AgentJobStatusUpdateView,
)

urlpatterns = [
    path('heartbeat/', AgentHeartbeatView.as_view(), name='agent-heartbeat'),
    path('claim-job/', AgentClaimJobView.as_view(), name='agent-claim-job'),
    path('jobs/<str:job_id>/download/', AgentJobDownloadView.as_view(), name='agent-job-download'),
    path('jobs/<str:job_id>/status/', AgentJobStatusUpdateView.as_view(), name='agent-job-status'),
]
