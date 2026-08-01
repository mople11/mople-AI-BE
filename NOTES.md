# 메모

## 2026-07-30 소셜 로그인 작업

- 카카오: 이메일/닉네임 동의항목 → 사업자 인증 없이는 신청 불가. placeholder 이메일(`kakao_{id}@users.eodiganam.local`)로 대체.
- 구글: 아직 클라이언트 ID 없음. Android 앱이라 `serverClientId`엔 웹 타입 클라이언트 ID 써야 함.
- 플루터 개발자한테 요청한 것: Android 패키지명 + SHA-1 서명 인증서 (아직 안 옴)
