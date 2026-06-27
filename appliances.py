import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone, timedelta

# --- [UI 디자인] 미니멀하고 깔끔한 와이드 레이아웃 설정 ---
st.set_page_config(
    page_title="시장 최저가 & 포지셔닝 분석 대시보드", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- [보안] API 인증 정보 가져오기 ---
CLIENT_ID = st.secrets.get("NAVER_CLIENT_ID", "")
CLIENT_SECRET = st.secrets.get("NAVER_CLIENT_SECRET", "")

def get_naver_shopping(query):
    if not CLIENT_ID or not CLIENT_SECRET:
        st.error("⚠️ Naver API 키가 설정되지 않았습니다.")
        return []
    
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    params = {
        "query": query,
        "display": 50, 
        "sort": "sim"  
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json().get('items', [])
        else:
            st.error(f"❌ API 호출 실패 (오류 코드: {response.status_code})")
            return []
    except Exception as e:
        st.error(f"⚠️ 네트워크 오류가 발생했습니다: {e}")
        return []

# --- 메인 헤더 ---
st.title("🔍 가전 시장 최저가 & 포지셔닝 분석 대시보드")

with st.expander("💡 대시보드 100% 활용 가이드 (클릭하여 펼치기)"):
    st.markdown("""
    - **검색:** 분석이 필요한 모델명이나 키워드(예: 에스프레소 머신, 초고속 블렌더)를 입력하세요.
    - **자동 정렬:** 검색된 모든 결과는 기본적으로 **'최저가 순'**으로 깔끔하게 정렬되어 표시됩니다.
    - **사이드바 필터:** 좌측 메뉴를 통해 원하는 예산 범위나 특정 유통 채널, 브랜드만 쏙쏙 골라볼 수 있습니다.
    - **리포트 추출:** 필터링된 결과는 테이블 상단의 엑셀 다운로드 버튼을 눌러 기획안이나 보고서에 즉시 활용하세요.
    """)
st.markdown("---")

# --- 검색어 입력 영역 ---
search_query = st.text_input("분석할 가전 모델명 또는 키워드를 입력하세요", placeholder="예: 에스프레소 머신, 포터블 믹서기")

if search_query:
    with st.spinner("네이버 쇼핑에서 최신 시장 데이터를 분석 중입니다..."):
        items = get_naver_shopping(search_query)
        
        if items:
            parsed_data = []
            for item in items:
                clean_title = item['title'].replace('<b>', '').replace('</b>', '')
                try:
                    price = int(item['lprice'])
                except:
                    price = 0
                    
                parsed_data.append({
                    "이미지": item['image'],
                    "상품명": clean_title,
                    "최저가(원)": price,
                    "브랜드": item.get('brand', '기타') if item.get('brand') else '기타',
                    "제조사": item.get('maker', '기타') if item.get('maker') else '기타',
                    "쇼핑몰": item['mallName'] if item['mallName'] else '오픈마켓',
                    "링크": item['link']
                })
            
            df = pd.DataFrame(parsed_data)
            df = df[df["최저가(원)"] > 0]
            
            df = df.sort_values(by="최저가(원)", ascending=True).reset_index(drop=True)
            
            if not df.empty:
                st.sidebar.header("🎯 시장 데이터 필터링")
                
                min_p = int(df["최저가(원)"].min())
                max_p = int(df["최저가(원)"].max())
                if min_p < max_p:
                    price_range = st.sidebar.slider("가격대 범위 설정 (원)", min_value=min_p, max_value=max_p, value=(min_p, max_p), step=1000)
                else:
                    price_range = (min_p, max_p)
                
                all_brands = sorted(list(df["브랜드"].unique()))
                selected_brands = st.sidebar.multiselect("분석 브랜드 선택", options=all_brands, default=all_brands)
                
                all_malls = sorted(list(df["쇼핑몰"].unique()))
                selected_malls = st.sidebar.multiselect("유통 채널 선택", options=all_malls, default=all_malls)
                
                filtered_df = df[
                    (df["최저가(원)"] >= price_range[0]) &
                    (df["최저가(원)"] <= price_range[1]) &
                    (df["브랜드"].isin(selected_brands)) &
                    (df["쇼핑몰"].isin(selected_malls))
                ].reset_index(drop=True)
                
                if not filtered_df.empty:
                    # [기능 추가] 한국 시간(KST) 기준 검색 일시 생성
                    kst = timezone(timedelta(hours=9))
                    current_time = datetime.now(kst).strftime("%Y년 %m월 %d일 %H:%M:%S")
                    
                    # 캡션 형태로 깔끔하게 우측 정렬 텍스트처럼 표시
                    st.caption(f"⏱️ 데이터 갱신 일시: {current_time} (KST)")
                    
                    avg_price = int(filtered_df["최저가(원)"].mean())
                    min_price = int(filtered_df["최저가(원)"].min())
                    max_price = int(filtered_df["최저가(원)"].max())
                    total_count = len(filtered_df)
                    
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("분석 상품 수", f"{total_count} 개")
                    m2.metric("시장 최저가", f"{min_price:,} 원")
                    m3.metric("평균 시장가", f"{avg_price:,} 원")
                    m4.metric("시장 최고가", f"{max_price:,} 원")
                    
                    st.markdown("---")
                    
                    tab1, tab2 = st.tabs(["📋 실시간 가격 비교 테이블", "📈 시장 포지셔닝 차트 분석"])
                    
                    with tab1:
                        st.subheader("📋 상세 상품 및 가격 리스트 (최저가순)")
                        
                        csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button("📥 현재 필터링된 결과 엑셀(CSV) 다운로드", data=csv_data, file_name=f"market_analysis_{search_query}.csv", mime="text/csv")
                        
                        st.dataframe(
                            filtered_df,
                            column_config={
                                "이미지": st.column_config.ImageColumn("제품 이미지", width="small"),
                                "상품명": st.column_config.TextColumn("상품명", width="large"),
                                "최저가(원)": st.column_config.ProgressColumn(
                                    "최저가(원)", 
                                    help="전체 가격대비 해당 상품의 가격 수준",
                                    format="%d 원",
                                    min_value=0,
                                    max_value=max_price
                                ),
                                "링크": st.column_config.LinkColumn("바로가기", display_text="이동")
                            },
                            use_container_width=True,
                            hide_index=True
                        )
                        
                    with tab2:
                        st.subheader("📊 유통 채널별 가격 포지셔닝 분석")
                        
                        fig_scatter = px.scatter(
                            filtered_df,
                            x="쇼핑몰",
                            y="최저가(원)",
                            color="브랜드",
                            hover_name="상품명",
                            title=f"'{search_query}' 유통 채널 및 브랜드별 가격 분포",
                            labels={"최저가(원)": "가격 (원)", "쇼핑몰": "유통 채널"},
                            template="plotly_white",
                            marginal_y="box" 
                        )
                        fig_scatter.update_traces(marker=dict(size=12, opacity=0.75))
                        st.plotly_chart(fig_scatter, use_container_width=True)
                        
                        fig_hist = px.histogram(
                            filtered_df,
                            x="최저가(원)",
                            nbins=20, 
                            title="전체 데이터 가격 구간별 상품 집중도",
                            labels={"최저가(원)": "가격 구간 (원)", "count": "상품 빈도수"},
                            template="plotly_white",
                            color_discrete_sequence=['#3A6073']
                        )
                        st.plotly_chart(fig_hist, use_container_width=True)
                        
                else:
                    st.warning("⚠️ 필터 조건에 부합하는 데이터가 없습니다. 사이드바 설정을 변경해 주세요.")
            else:
                st.info("검색된 제품들의 올바른 가격 데이터를 파싱하지 못했습니다.")
        else:
            st.info("검색 결과가 없거나 API 응답 값이 비어 있습니다. 검색어를 구체적으로 입력해 보세요.")
else:
    st.info("💡 대시보드 상단의 검색창에 분석을 원하시는 가전 키워드를 입력하면 실시간 모니터링이 시작됩니다.")
