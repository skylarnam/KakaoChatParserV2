# KakaoTalk Chatroom Dashboard

카카오톡 채팅방 CSV 데이터를 업로드하여 월간 통계, 채팅 추이, 비활성 사용자, 사용자별 메시지 수 등을 시각적으로 확인할 수 있는 Flask 기반 대시보드입니다.

## 주요 기능
- CSV 파일 업로드로 카카오톡 채팅 데이터 분석
- 월간 사용자별 채팅 통계 (상위 10명)
- 전체 채팅량 추이(일별)
- 비활성 사용자 필터 (30/60/90일, 날짜 범위 지정)
- 사용자별 월간 메시지 수 확인
- 내보내진/퇴장한 사용자는 자동 제외 (재입장 시 정상 처리)

## 설치 및 실행 방법
1. **Python 3.10+ 권장**
2. 가상환경 생성 및 활성화
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows는 venv\Scripts\activate
   ```
3. 필요 패키지 설치
   ```bash
   pip install -r requirements.txt
   ```
4. 서버 실행
   ```bash
   flask run
   ```
   또는
   ```bash
   python app.py
   ```
5. 웹 브라우저에서 [http://localhost:5000](http://localhost:5000) 접속

## CSV 파일 포맷 예시
| Date                | User              | Message                                 |
|---------------------|-------------------|-----------------------------------------|
| 2025-03-06 06:57:00 | 안녕/95/F/시애틀     | 안녕!                                    |

- **User**: 발화자 또는 시스템 메시지의 주체
- **Message**: 실제 메시지 또는 시스템 이벤트

## 환경 변수 및 기타
- 환경 변수(.env)는 필요시 직접 추가/관리하세요.
- 업로드된 파일 및 DB는 `.gitignore`로 깃헙에 올라가지 않습니다.

## 라이선스
MIT 