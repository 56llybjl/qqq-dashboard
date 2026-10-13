# QQQ 6개 지표 한국어 자동 대시보드

## 실행
Python 3.10 이상 설치 후 터미널(명령 프롬프트)에서:

```bash
pip install -r requirements.txt
streamlit run app.py
```

웹브라우저에서 표시된 로컬 주소(보통 http://localhost:8501)를 여세요.

## 데이터
- QQQ·VIX: Yahoo Finance 비공식 무료 데이터(yfinance), 일봉, 15분 앱 캐시. 실시간/고정 지연 보장 없음.
- RSI(14)·200일 단순이평·볼린저(20, 2σ): QQQ 종가로 계산.
- CNN 공포탐욕지수: CNN 비공식 JSON 데이터, 앱 캐시 1시간.
- 시장폭: CNN의 **S&P500 기반 stock_price_breadth** 구성요소를 표시합니다. **나스닥100 시장폭이 아닙니다.**
- 데이터 연결 실패 시 임의 수치를 표시하지 않습니다.

## 주의
시세 API는 무료·비공식 서비스여서 접속 차단이나 서비스 변경으로 실패할 수 있습니다. 이 프로그램은 투자 판단 보조용이며 자동주문 기능이 없습니다. 실행 중 인터넷 연결이 필요합니다.

## 배포
Streamlit Community Cloud 등에 GitHub 저장소를 연결해 배포할 수 있습니다. 배포 서비스 정책과 무료 제공 범위는 변경될 수 있습니다.
