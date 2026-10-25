import logging
from django.utils import timezone
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.common.storage import private_storage
from apps.audit.services import record_audit_event
from apps.printing.models import PrintJob, PrintJobAttempt
from apps.printing.serializers import AgentJobClaimSerializer
from apps.printing.services import claim_next_job_for_station
from apps.printing.state_machine import transition_job_status
from .models import PrintStation
from .authentication import PrintStationAuthentication

logger = logging.getLogger(__name__)


class AgentBaseView(APIView):
    """
    Base view requiring Windows PC Print Agent credentials.
    """
    authentication_classes = [PrintStationAuthentication]

    def check_permissions(self, request):
        if not request.user or not isinstance(request.user, PrintStation):
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed("Valid station authentication headers (X-Station-Code and X-Agent-Secret) required.")


class AgentHeartbeatView(AgentBaseView):
    """
    POST /api/v1/agent/heartbeat/
    Windows Agent reports station health, version, and active local printer names.
    """
    @extend_schema(summary="Agent heartbeat & health update")
    def post(self, request):
        station: PrintStation = request.user
        local_printers = request.data.get('local_printers', [])
        agent_version = request.data.get('agent_version', '')

        if local_printers and isinstance(local_printers, list):
            # Only update allowlisted printers or record active printers
            station.allowed_printers = local_printers

        station.update_heartbeat(
            agent_version=agent_version,
            ip=request.META.get('REMOTE_ADDR')
        )

        record_audit_event(
            event_type='agent_heartbeat',
            actor_type='agent',
            actor_identifier=station.station_code,
            station_id=str(station.id),
            metadata={'version': agent_version, 'printers_detected': len(local_printers)}
        )

        return Response({
            "success": True,
            "station_code": station.station_code,
            "status": station.status,
            "server_time": station.last_heartbeat_at.isoformat(),
        })


class AgentClaimJobView(AgentBaseView):
    """
    POST /api/v1/agent/claim-job/
    Atomically claims the next eligible print job for this station.
    Returns 200 with job payload or 204 No Content if nothing to print.
    """
    @extend_schema(summary="Atomic claim of next available queued print job")
    def post(self, request):
        station: PrintStation = request.user
        job = claim_next_job_for_station(station)

        if not job:
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = AgentJobClaimSerializer(job, context={'request': request})
        return Response({
            "success": True,
            "job": serializer.data,
        })


class AgentJobDownloadView(AgentBaseView):
    """
    GET /api/v1/agent/jobs/{job_id}/download/
    Authenticated streaming download of the PDF file from private storage.
    Ensures only the claimed station can download the file.
    """
    @extend_schema(summary="Download claimed job PDF file")
    def get(self, request, job_id):
        station: PrintStation = request.user

        try:
            job = PrintJob.objects.get(id=job_id)
        except (PrintJob.DoesNotExist, ValueError):
            raise Http404("Job not found.")

        # Ensure station authorization
        if job.assigned_station != station:
            return Response(
                {"success": False, "message": "This job is not assigned to your station."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Blocked jobs must never be released to agent
        if job.approval_status == 'blocked':
            return Response(
                {"success": False, "message": "This job has been blocked by an administrator."},
                status=status.HTTP_403_FORBIDDEN
            )


        if not private_storage.file_exists(job.storage_key):
            logger.error(f"Storage file missing for job {job.job_number}: {job.storage_key}")
            raise Http404("Document file missing in private storage.")

        file_path = private_storage.get_full_path(job.storage_key)
        record_audit_event(
            event_type='job_downloaded',
            actor_type='agent',
            actor_identifier=station.station_code,
            job_id=str(job.id),
            station_id=str(station.id)
        )

        return FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=job.original_filename,
            content_type='application/pdf'
        )


class AgentJobStatusUpdateView(AgentBaseView):
    """
    POST /api/v1/agent/jobs/{job_id}/status/
    Agent reports state transitions:
    downloading -> ready_to_print -> submitting_to_printer -> submitted_to_printer -> completed / failed / outcome_unknown
    """
    @extend_schema(summary="Report job execution status from PC print agent")
    def post(self, request, job_id):
        station: PrintStation = request.user

        try:
            job = PrintJob.objects.get(id=job_id)
        except (PrintJob.DoesNotExist, ValueError):
            raise Http404("Job not found.")

        if job.assigned_station != station:
            return Response(
                {"success": False, "message": "Station is not authorized for this job."},
                status=status.HTTP_403_FORBIDDEN
            )

        new_status = request.data.get('status')
        error_code = request.data.get('error_code', '')
        error_message = request.data.get('error_message', '')
        diagnostic = request.data.get('diagnostic_details', '')

        # Execute validated state transition
        transition_job_status(
            job=job,
            new_status=new_status,
            error_code=error_code,
            error_message=error_message,
            actor=f"Agent:{station.station_code}"
        )

        # Update attempt record
        latest_attempt = job.attempts.order_by('-started_at').first()
        if latest_attempt:
            latest_attempt.status = new_status
            if diagnostic:
                latest_attempt.diagnostic_details = diagnostic
            if new_status in ['completed', 'failed', 'outcome_unknown']:
                latest_attempt.finished_at = timezone.now()
            latest_attempt.save()

        record_audit_event(
            event_type='job_status_updated',
            actor_type='agent',
            actor_identifier=station.station_code,
            job_id=str(job.id),
            station_id=str(station.id),
            metadata={'status': new_status, 'error_code': error_code}
        )

        return Response({
            "success": True,
            "job_number": job.job_number,
            "status": job.status,
        })
