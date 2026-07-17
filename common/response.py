from rest_framework.response import Response


class ApiResponse(Response):
    def __init__(self, data=None, status=200):
        super().__init__(
            {"success": True, "data": data, "error": None},
            status=status,
        )
