from django.urls import reverse


def test_openapi_schema_documents_auth_endpoints(api_client):
    response = api_client.get(
        reverse("schema"),
        HTTP_ACCEPT="application/json",
    )

    assert response.status_code == 200
    schema = response.json()

    signup = schema["paths"]["/api/v1/auth/signup"]["post"]
    assert signup["summary"] == "회원가입"
    assert signup["description"]
    assert signup["tags"] == ["Auth"]
    assert "examples" in signup["requestBody"]["content"]["application/json"]
    assert {"201", "400", "409", "422", "500"} <= set(signup["responses"])

    check_id = schema["paths"]["/api/v1/auth/signup/check-id"]["get"]
    assert check_id["summary"] == "아이디 중복 확인"
    assert check_id["description"]
    assert check_id["tags"] == ["Auth"]
    assert check_id["parameters"][0]["name"] == "id"
    assert check_id["parameters"][0]["required"] is True
    assert check_id["parameters"][0]["description"]
    assert {"200", "422", "500"} <= set(check_id["responses"])

    send_email_code = schema["paths"][
        "/api/v1/auth/email/verify-code"
    ]["post"]
    assert send_email_code["summary"] == "이메일 인증번호 발송"
    assert send_email_code["description"]
    assert send_email_code["tags"] == ["Auth"]
    assert "examples" in send_email_code["requestBody"]["content"][
        "application/json"
    ]
    assert {"200", "422", "500"} <= set(send_email_code["responses"])

    verify_email_code = schema["paths"][
        "/api/v1/auth/email/verify-confirm"
    ]["post"]
    assert verify_email_code["summary"] == "이메일 인증번호 확인"
    assert verify_email_code["description"]
    assert verify_email_code["tags"] == ["Auth"]
    assert "examples" in verify_email_code["requestBody"]["content"][
        "application/json"
    ]
    assert {"200", "400", "422", "500"} <= set(
        verify_email_code["responses"]
    )


def test_swagger_ui_is_available(api_client):
    response = api_client.get(reverse("swagger-ui"))

    assert response.status_code == 200
    assert b"swagger-ui" in response.content
