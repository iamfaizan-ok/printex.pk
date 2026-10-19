from rest_framework import authentication, exceptions
from .models import PrintStation


class PrintStationAuthentication(authentication.BaseAuthentication):
    """
    Authenticates requests coming from the Windows PC Print Agent via headers:
    - X-Station-Code
    - X-Agent-Secret
    """

    def authenticate(self, request):
        station_code = request.headers.get('X-Station-Code')
        agent_secret = request.headers.get('X-Agent-Secret')

        if not station_code or not agent_secret:
            return None  # Pass to next authenticator or leave unauthenticated

        try:
            station = PrintStation.objects.get(station_code=station_code, is_enabled=True)
        except PrintStation.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid station code or station is disabled.")

        if not station.check_token(agent_secret):
            raise exceptions.AuthenticationFailed("Invalid agent secret credential.")

        # Update heartbeat timestamp
        ip = request.META.get('REMOTE_ADDR')
        agent_version = request.headers.get('X-Agent-Version', '')
        station.update_heartbeat(agent_version=agent_version, ip=ip)

        # Return (station, auth_secret)
        return (station, agent_secret)
