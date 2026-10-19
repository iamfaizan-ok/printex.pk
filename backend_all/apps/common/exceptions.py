import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Standard exception handler for DRF:
    - Never leaks server internal stack traces or secrets to the client.
    - Formats all error responses consistently as:
      {
        "success": false,
        "message": "...",
        "errors": { ... }
      }
    """
    response = exception_handler(exc, context)

    if response is not None:
        custom_data = {
            "success": False,
            "message": "Validation or request processing error.",
            "errors": {}
        }

        if isinstance(response.data, dict):
            if "detail" in response.data:
                custom_data["message"] = str(response.data["detail"])
            else:
                custom_data["errors"] = response.data
                first_key = next(iter(response.data))
                first_val = response.data[first_key]
                if isinstance(first_val, list) and len(first_val) > 0:
                    custom_data["message"] = f"{first_key}: {first_val[0]}"
                else:
                    custom_data["message"] = str(first_val)
        elif isinstance(response.data, list):
            custom_data["message"] = ", ".join([str(item) for item in response.data])

        response.data = custom_data
        return response

    # Unhandled 500 exceptions
    logger.exception("Unhandled server exception: %s", exc)
    return Response(
        {
            "success": False,
            "message": "An internal server error occurred. Our engineering team has been notified.",
            "errors": {}
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
