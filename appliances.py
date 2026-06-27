import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- [UI 디자인] 미니멀하고 깔끔한 와이드 레이아웃 설정 ---
st.set_page_config(
    page_title="시장 최저가 & 포지셔닝 분석 대시보드", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- [보안] API 인증 정보 가져오기 (Streamlit Secrets) ---
CLIENT_ID = st.secrets.get("NAVER_CLIENT_ID", "")
CLIENT_SECRET = st.secrets.get("NAVER_CLIENT_SECRET", "")

def get_naver_shopping(query):
    if not CLIENT_ID or not CLIENT_SECRET:
        st.error("⚠️ Naver API 키가 설정되지 않았습니다. Streamlit Cloud의 Advanced Settings에서 Secrets를 설정해주세요.")
        return []
    
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    # 더 정밀한 분포도 분석을 위해 데이터 수집 단위를 50개로 확장
    params = {
        "query": query,
        "display": 50, 
        "sort": "sim"  # 정확도순 정렬
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
st.markdown("네이버 쇼핑 API 데이터를 실시간으로 파싱하여 가격 분포와 유통 채널별 포지션을 시각화합니다.")
st.markdown("---")

# --- 검색어 입력 영역 ---
search_query = st.text_input("분석할 가전 모델명 또는 키워드를 입력하세요", placeholder="예: 에스프레소 머신, 포터블 믹서기")

if search_query:
    with st.spinner("네이버 쇼핑에서 최신 시장 데이터를 분석 중입니다..."):
        items = get_naver_shopping(search_query)
        
        if items:
            # 1. 원본 데이터 파싱 및 정제
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
            df = df[df["최저가(원)"] > 0].reset_index(drop=True)  # 가격 정보가 정상적인 데이터만 필터링
            
            if not df.empty:
                # --- 2. [기능 추가] 사이드바 인터랙티브 필터 구성 ---
                st.sidebar.header("🎯 시장 데이터 필터링")
                
                # 가격 범위 슬라이더 설정
                min_p = int(df["최저가(원)"].min())
                max_p = int(df["최저가(원)"].max())
                if min_p < max_p:
                    price_range = st.sidebar.slider(
                        "가격대 범위 설정 (원)",
                        min_value=min_p,
                        max_value=max_p,
                        value=(min_p, max_p),
                        step=1000
                    )
                else:
                    price_range = (min_p, max_p)
                
                # 브랜드 멀티 셀렉트
                all_brands = sorted(list(df["브랜드"].unique()))
                selected_brands = st.sidebar.multiselect("분석 브랜드 선택", options=all_brands, default=all_brands)
                
                # 쇼핑몰 멀티 셀렉트
                all_malls = sorted(list(df["쇼핑몰"].unique()))
                selected_malls = st.sidebar.multiselect("유통 채널 선택", options=all_malls, default=all_malls)
                
                # 필터링 최종 적용 데이터
                filtered_df = df[
                    (df["최저가(원)"] >= price_range[0]) &
                    (df["최저가(원)"] <= price_range[1]) &
                    (df["브랜드"].isin(selected_brands)) &
                    (df["쇼핑몰"].isin(selected_malls))
                ].reset_index(drop=True)
                
                # --- 3. 상단 핵심 지표 요약 (Metrics) ---
                if not filtered_df.empty:
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
                    
                    # --- 4. [기능 추가] 탭 레이아웃 분할 ---
                    tab1, tab2 = st.tabs(["📋 실시간 가격 비교 테이블", "📈 시장 포지셔닝 차트 분석"])
                    
                    with tab1:
                        st.subheader("📋 상세 상품 및 가격 리스트")
                        
                        # [기능 추가] 엑셀(CSV) 다운로드 버튼 기능
                        # Excel에서 한글 깨짐을 방지하기 위해 utf-8-sig 인코딩 처리
                        csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="📥 현재 필터링된 결과 엑셀(CSV) 다운로드",
                            data=csv_data,
                            file_name=f"market_analysis_{search_query}.csv",
                            mime="text/csv"
                        )
                        
                        # [기능 추가] 이미지 노출 및 중앙 정렬 서식 적용 테이블
                        st.dataframe(
                            filtered_df,
                            column_config={
                                "이미지": st.column_config.ImageColumn("제품 이미지", width="small"),
                                "상품명": st.column_config.TextColumn("상품명", width="large"),
                                "최저가(원)": st.column_config.NumberColumn("최저가(원)", format="%d 원"),
                                "링크": st.column_config.LinkColumn("바로가기", display_text="이동")
                            },
                            use_container_width=True,
                            hide_index=True
                        )
                        
                    with tab2:
                        st.subheader("📊 브랜드별 가격 포지셔닝 분석")
                        st.markdown("현재 시장에 진입해 있는 브랜드들의 가격 포지션 및 유통 채널 분포를 시각화합니다.")
                        
                        # [기능 추가] Plotly 기반 브랜드별 가격대 산점도(Positioning Map)
                        fig_scatter = px.scatter(
                            filtered_df,
                            x="브랜드",
                            y="최저가(원)",
                            color="쇼핑몰",
                            hover_name="상품명",
                            title=f"'{search_query}' 브랜드별 시장 가격 분포",
                            labels={"최저가(원)": "가격 (원)", "브랜드": "브랜드명"},
                            template="plotly_white"
                        )
                        fig_scatter.update_traces(marker=dict(size=12, opacity=0.75))
                        st.plotly_chart(fig_scatter, use_container_width=True)
                        
                        # [기능 추가] 전체 상품 가격대 빈도 분포 히스토그램
                        fig_hist = px.histogram(
                            filtered_df,
                            x="최저가(원)",
                            nbins=15,
                            title="전체 데이터 가격 구간별 상품 집중도",
                            labels={"최저가(원)": "가격 구간 (원)", "count": "상품 빈도수"},
                            template="plotly_white",
                            color_discrete_sequence=['#3A6073']
                        )
                        st.plotly_chart(fig_hist, use_container_width=True)
                        
                else:
                    st.warning("⚠️ 선택하신 필터 조건(가격 범위, 브랜드, 쇼핑몰)에 부합하는 데이터가 없습니다. 사이드바 설정을 변경해 주세요.")
            else:
                st.info("검색된 제품들의 올바른 가격 데이터를 파싱하지 못했습니다.")
        else:
            st.info("검색 결과가 없거나 API 응답 값이 비어 있습니다. 검색어를 구체적으로 입력해 보세요.")
else:
    # 데이터 검색 전 초기 안내 화면
    st.info("💡 대시보드 상단의 검색창에 분석을 원하시는 가전 키워드를 입력하면 실시간 모니터링이 시작됩니다.")
