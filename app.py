import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timezone
import plotly.graph_objects as go

st.set_page_config(page_title='QQQ 6대 지표 | 한국어', page_icon='📊', layout='wide')
st.title('📊 QQQ 투자 보조지표 — 한국어 자동 대시보드')
st.caption('QQQ 일봉 기반 · 무료 데이터 · 투자 판단 보조용 (실시간 거래용 아님)')

@st.cache_data(ttl=900, show_spinner=False)
def load_prices():
    result = {}
    for symbol in ['QQQ', '^VIX']:
        df = yf.download(symbol, period='2y', interval='1d', auto_adjust=True, progress=False, threads=False)
        if df is None or df.empty:
            raise ValueError(f'{symbol} 가격 데이터가 비어 있습니다.')
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna(subset=['Close']).sort_index()
        result[symbol] = df
    return result

@st.cache_data(ttl=3600, show_spinner=False)
def load_fear():
    url='https://production.dataviz.cnn.io/index/fearandgreed/graphdata'
    headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/123.0 Safari/537.36', 'Referer':'https://www.cnn.com/markets/fear-and-greed', 'Accept':'application/json'}
    r=requests.get(url,headers=headers,timeout=12)
    r.raise_for_status()
    data=r.json()
    fg=data.get('fear_and_greed',{})
    score=fg.get('score')
    if score is None: raise ValueError('CNN 점수 필드 없음')
    breadth=data.get('stock_price_breadth',{})
    # CNN breadth is S&P 500 McClellan-volume breadth, NOT Nasdaq 100 breadth.
    return {'score':float(score), 'timestamp':fg.get('timestamp'), 'breadth':breadth, 'source':'CNN'}

def compute(df):
    c=df['Close'].astype(float)
    out=df.copy()
    out['SMA200']=c.rolling(200).mean()
    out['BB_mid']=c.rolling(20).mean()
    out['BB_std']=c.rolling(20).std(ddof=0)
    out['BB_upper']=out['BB_mid']+2*out['BB_std']
    out['BB_lower']=out['BB_mid']-2*out['BB_std']
    delta=c.diff()
    up=delta.clip(lower=0)
    down=-delta.clip(upper=0)
    # Wilder RSI: seeded 14-period simple averages, then Wilder smoothing.
    period=14
    avg_up=pd.Series(np.nan,index=c.index,dtype=float)
    avg_dn=pd.Series(np.nan,index=c.index,dtype=float)
    if len(c)>period:
        avg_up.iloc[period]=up.iloc[1:period+1].mean()
        avg_dn.iloc[period]=down.iloc[1:period+1].mean()
        for i in range(period+1,len(c)):
            avg_up.iloc[i]=(avg_up.iloc[i-1]*(period-1)+up.iloc[i])/period
            avg_dn.iloc[i]=(avg_dn.iloc[i-1]*(period-1)+down.iloc[i])/period
    rs=avg_up/avg_dn.replace(0,np.nan)
    out['RSI14']=100-100/(1+rs)
    out.loc[(avg_dn==0)&(avg_up>0),'RSI14']=100
    out.loc[(avg_dn==0)&(avg_up==0),'RSI14']=50
    return out

if st.button('🔄 데이터 다시 확인'):
    load_prices.clear();load_fear.clear();st.rerun()

try:
    with st.spinner('QQQ·VIX 데이터를 가져오는 중...'):
        prices=load_prices()
        q=compute(prices['QQQ'])
        v=prices['^VIX']
except Exception as e:
    st.error(f'시세 연결 실패: {e}')
    st.info('Yahoo Finance 비공식 데이터 연결이 일시적으로 차단될 수 있습니다. 잠시 후 새로고침하거나 네트워크를 확인하세요.')
    st.stop()

try:
    fear=load_fear(); fear_error=None
except Exception as e:
    fear=None;fear_error=str(e)

last=q.iloc[-1];prev=q.iloc[-2];vlast=v.iloc[-1]
qdate=q.index[-1].strftime('%Y-%m-%d');vdate=v.index[-1].strftime('%Y-%m-%d')
st.caption(f'QQQ 기준일 {qdate} | VIX 기준일 {vdate} | 앱 확인 시각 {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} | 장중 실시간 보장 없음')

cols=st.columns(6)
values=[('QQQ 종가',f'${last["Close"]:,.2f}',f'{(last["Close"]/prev["Close"]-1)*100:+.2f}%'),('200일선',f'${last["SMA200"]:,.2f}','상단' if last['Close']>=last['SMA200'] else '하단'),('RSI (14)',f'{last["RSI14"]:.1f}','과매도' if last['RSI14']<30 else '과매수' if last['RSI14']>70 else '중립'),('VIX',f'{vlast["Close"]:.1f}','공포 확대' if vlast['Close']>=30 else '주의' if vlast['Close']>=20 else '보통'),('볼린저밴드', '하단 아래' if last['Close']<last['BB_lower'] else '상단 위' if last['Close']>last['BB_upper'] else '밴드 안', '20일·2σ'),('공포탐욕',f'{fear["score"]:.1f}' if fear else '연결 실패','CNN' if fear else '확인 필요')]
for col,(label,value,sub) in zip(cols,values):
    col.metric(label,value,sub)

st.subheader('① QQQ 가격 · 200일선 · 볼린저밴드')
window=st.select_slider('차트 기간',options=[90,180,365,500],value=365,format_func=lambda x:f'최근 {x}거래일')
view=q.tail(window)
fig=go.Figure()
fig.add_trace(go.Scatter(x=view.index,y=view['BB_upper'],name='볼린저 상단',line=dict(color='rgba(124,58,237,.55)',width=1)))
fig.add_trace(go.Scatter(x=view.index,y=view['BB_lower'],name='볼린저 하단',fill='tonexty',fillcolor='rgba(124,58,237,.08)',line=dict(color='rgba(124,58,237,.55)',width=1)))
fig.add_trace(go.Scatter(x=view.index,y=view['SMA200'],name='200일 SMA',line=dict(color='#f59e0b',width=2)))
fig.add_trace(go.Scatter(x=view.index,y=view['Close'],name='QQQ 종가',line=dict(color='#2563eb',width=2)))
fig.update_layout(height=420,margin=dict(l=10,r=10,t=10,b=10),legend=dict(orientation='h'),hovermode='x unified')
st.plotly_chart(fig,use_container_width=True)

left,right=st.columns(2)
with left:
    st.subheader('② RSI (14)')
    fig2=go.Figure(go.Scatter(x=view.index,y=view['RSI14'],name='RSI 14',line=dict(color='#0d9488')))
    fig2.add_hline(y=70,line_dash='dash',line_color='red',annotation_text='과매수 70')
    fig2.add_hline(y=30,line_dash='dash',line_color='green',annotation_text='과매도 30')
    fig2.update_layout(height=280,yaxis_range=[0,100],margin=dict(l=10,r=10,t=10,b=10))
    st.plotly_chart(fig2,use_container_width=True)
with right:
    st.subheader('③ VIX 변동성 지수')
    vv=v.tail(window)
    fig3=go.Figure(go.Scatter(x=vv.index,y=vv['Close'],name='VIX',line=dict(color='#d97706')))
    fig3.add_hline(y=20,line_dash='dash',line_color='orange',annotation_text='20')
    fig3.add_hline(y=30,line_dash='dash',line_color='red',annotation_text='30')
    fig3.update_layout(height=280,margin=dict(l=10,r=10,t=10,b=10))
    st.plotly_chart(fig3,use_container_width=True)

st.subheader('④ 시장폭 · ⑤ 공포탐욕')
a,b=st.columns(2)
with a:
    st.markdown('**시장폭: CNN S&P500 기반 지표 (나스닥100 직접 시장폭 아님)**')
    if fear and isinstance(fear['breadth'],dict) and fear['breadth']:
        breadth=fear['breadth']
        for k in ['score','rating','timestamp']:
            if breadth.get(k) is not None: st.write(f'{k}: {breadth[k]}')
        st.caption('CNN 구성요소는 S&P500 시장폭 기반입니다. QQQ 구성종목의 상승·하락 비율과 혼동하지 마세요.')
    else:
        st.warning('시장폭 데이터를 현재 가져올 수 없습니다. 임의로 점수를 채우지 않습니다.')
with b:
    if fear:
        st.metric('CNN Fear & Greed',f'{fear["score"]:.1f} / 100')
        st.caption(f'원본 갱신 시각: {fear["timestamp"] or "확인 불가"}')
    else:
        st.warning('CNN 데이터 연결 실패 — 공포탐욕/시장폭 신호는 판단에서 제외합니다.')
        st.caption(f'오류: {fear_error}')
    st.link_button('CNN 공식 페이지', 'https://www.cnn.com/markets/fear-and-greed')

st.subheader('⑥ 교차 점검 (참고용)')
trend='상승 추세권' if last['Close']>=last['SMA200'] else '장기 추세 주의'
rsi='과매도' if last['RSI14']<30 else '과매수' if last['RSI14']>70 else '중립'
band='하단 이탈' if last['Close']<last['BB_lower'] else '상단 돌파' if last['Close']>last['BB_upper'] else '밴드 내부'
vol='높은 변동성' if vlast['Close']>=30 else '변동성 경계' if vlast['Close']>=20 else '낮은 변동성'
sentiment='극단적 공포' if fear and fear['score']<25 else '극단적 탐욕' if fear and fear['score']>75 else '중간 구간' if fear else '확인 불가'
st.info(f'장기추세: **{trend}** · RSI: **{rsi}** · 볼린저: **{band}** · VIX: **{vol}** · 투자심리: **{sentiment}**')
st.write('지표 간 상관관계가 높으므로 일치 개수를 매수 성공 확률로 해석하지 마세요. 과매도는 추가 하락과 양립할 수 있습니다.')
st.download_button('QQQ 지표 CSV 다운로드',data=q[['Close','SMA200','RSI14','BB_mid','BB_upper','BB_lower']].to_csv().encode('utf-8-sig'),file_name='QQQ_indicators.csv',mime='text/csv')
with st.expander('데이터 출처 · 업데이트 지연 · 한계'):
    st.markdown('''- **QQQ·VIX:** Yahoo Finance의 비공식 데이터 인터페이스를 사용하는 `yfinance`. 무료이며 로그인/API 키는 필요 없지만 연결이 불안정할 수 있습니다. **고정된 15분 지연을 보장하지 않습니다.** 이 앱은 **일봉**을 사용하므로 거래소 장중 체결가 대신 최신 제공 일봉을 보여줍니다. 15분 캐시를 적용합니다.
- **RSI·200일선·볼린저밴드:** QQQ 일봉 종가로 앱에서 직접 계산합니다. 원본 가격 데이터보다 빠를 수 없습니다.
- **공포탐욕·시장폭:** CNN 비공식 JSON 엔드포인트를 사용합니다. 원본 갱신 시각을 표시하며 앱에서는 최대 1시간 캐시합니다. API는 사전 통보 없이 중단될 수 있습니다.
- **시장폭 주의:** CNN의 `stock_price_breadth`는 S&P500 기반 구성요소로, **나스닥100 시장폭의 대체 지표**입니다. 별도 나스닥100 전 종목 데이터 제공자가 연결되지 않은 상태에서 이를 동일한 지표라고 표시하지 않습니다.
- **실시간 시세/자동주문 기능 없음.** 투자 권유나 수익 보장이 아닙니다.''')
