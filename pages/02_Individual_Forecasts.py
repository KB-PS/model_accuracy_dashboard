import streamlit as st
from src.settings import ACCURACY_MONITORING_TAB, colors
from src.graphs import preprocess_data, create_series_plot_new
from src.graphs import filter_by_date
from src.helpers import read_df, calculate_categories
from src.helpers import MAPE
from src.helpers import update_default_model
from src.helpers import create_or_update_table
import pandas as pd
from streamlit_extras.switch_page_button import switch_page
import datetime

if 'authentication_status' not in st.session_state:
    switch_page("login")

if st.session_state["authentication_status"]:
    
    #df_meals = read_df(ACCURACY_MONITORING_MEALS_TAB, date_col=["approximate_timestamp"])
    df_accuracy = read_df(ACCURACY_MONITORING_TAB, date_col=["ds"])
    #df_actuals = read_df(ACTUALS_NONAGG_TAB, date_col=["ds"])
    cat1, cat2, cat3 = calculate_categories(df_accuracy)
    default_model = st.session_state["default_model"]

    with st.sidebar:
        category_type = st.selectbox("Category Type", cat1)
        outlet_type = st.selectbox("Outlet Type", cat2)
        outlet_number = st.selectbox("Outlet Number", cat3)
        category_selected = '~'.join([category_type, outlet_type, outlet_number])
    
    accu_preprocessed = preprocess_data(df_accuracy, category_selected, time_col='ds')
        
    with st.sidebar:
        sc1, sc2 = st.columns(2)
        with sc1:
            if "start_date" in st.session_state:
                value = st.session_state["start_date"]
            else:
                value = df_accuracy.ds.min().date()

            start_date = st.date_input("Start Date", 
                                        value=value,
                                        min_value=accu_preprocessed.dt.min().date(), 
                                        max_value=accu_preprocessed.dt.max().date()
                                        )
            st.session_state["start_date"] = start_date
        with sc2:
            if "end_date" in st.session_state:
                value = st.session_state["end_date"]
            else:
                value = df_accuracy.ds.max().date()

            end_date = st.date_input("End Date", 
                                        value=value,
                                        min_value=start_date, 
                                        max_value=accu_preprocessed.dt.max().date())
            st.session_state["end_date"] = end_date
    start_date = pd.to_datetime(start_date)
    # we need to include the last date of selection

    end_date = end_date + datetime.timedelta(days=1)
    end_date = pd.to_datetime(end_date)     
    #meals_preprocessed_filtered = filter_by_date(meals_preprocessed, start_date, end_date)
    accu_preprocessed_filtered = filter_by_date(accu_preprocessed, start_date, end_date)

    # 1. aggregate by category, date and meal_category
    group_cols = ["category", "date", "meal_category"]
    agg_cols = ["metric_actual", "metric_forecast", "metric_forecast_lgbm", "metric_forecast_rf"]
    accu_preprocessed_filtered_agg = accu_preprocessed_filtered.groupby(group_cols)[agg_cols].sum().reset_index()
    
    #st.write(accu_preprocessed_filtered_agg)
    # 2. calculate MAPE
    mape_lunch_prophet = MAPE(accu_preprocessed_filtered_agg.loc[accu_preprocessed_filtered_agg.meal_category=='lunch'].metric_actual, 
                              accu_preprocessed_filtered_agg.loc[accu_preprocessed_filtered_agg.meal_category=='lunch'].metric_forecast)

    mape_lunch_lgbm = MAPE(accu_preprocessed_filtered_agg.loc[accu_preprocessed_filtered_agg.meal_category=='lunch'].metric_actual, 
                              accu_preprocessed_filtered_agg.loc[accu_preprocessed_filtered_agg.meal_category=='lunch'].metric_forecast_lgbm)

    mape_lunch_rf = MAPE(accu_preprocessed_filtered_agg.loc[accu_preprocessed_filtered_agg.meal_category=='lunch'].metric_actual, 
                              accu_preprocessed_filtered_agg.loc[accu_preprocessed_filtered_agg.meal_category=='lunch'].metric_forecast_rf)

    mape_dinner_prophet = MAPE(accu_preprocessed_filtered_agg.loc[accu_preprocessed_filtered_agg.meal_category=='dinner'].metric_actual, 
                              accu_preprocessed_filtered_agg.loc[accu_preprocessed_filtered_agg.meal_category=='dinner'].metric_forecast)

    mape_dinner_lgbm = MAPE(accu_preprocessed_filtered_agg.loc[accu_preprocessed_filtered_agg.meal_category=='dinner'].metric_actual, 
                              accu_preprocessed_filtered_agg.loc[accu_preprocessed_filtered_agg.meal_category=='dinner'].metric_forecast_lgbm)

    mape_dinner_rf = MAPE(accu_preprocessed_filtered_agg.loc[accu_preprocessed_filtered_agg.meal_category=='dinner'].metric_actual, 
                              accu_preprocessed_filtered_agg.loc[accu_preprocessed_filtered_agg.meal_category=='dinner'].metric_forecast_rf)
 
    selected_model = default_model.loc[default_model.category==category_selected, "default_model"].values[0]
    
    if accu_preprocessed_filtered.empty:
        st.warning("No data for available for the selection.")
        st.stop()

    with st.container():
        st.markdown("## Mean Average Percentage Error (MAPE)")
        with st.expander("See calculation explanation"):
            st.markdown('''
                           - For each date do a sum of sales per lunch hours and dinner hours for both actuals and forecasts  
                           - Then for each part of day calculate 100 * ABS(actuals - forecast) / forecast  
                           - Finally calculate mean over the period defined in the sidebar  
                        ''')
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Lunch")

            col11, col12, col13 = st.columns(3)
            with col11:
                st.metric("Prophet", f"{mape_lunch_prophet:.2f} %", f"{15 - mape_lunch_prophet:.2f} %")
            with col12:
                st.metric("LightGBM", f"{mape_lunch_lgbm:.2f} %", f"{15 - mape_lunch_lgbm:.2f} %")
            with col13:
                st.metric("Random Forest", f"{mape_lunch_rf:.2f} %", f"{15 - mape_lunch_rf:.2f} %")
            
        with col2:
            st.markdown("### Dinner")
            
            col21, col22, col23 = st.columns(3)
            with col21:
                st.metric("Prophet", f"{mape_dinner_prophet:.2f} %", f"{15 - mape_dinner_prophet:.2f} %")
            with col22:
                st.metric("LightGBM", f"{mape_dinner_lgbm:.2f} %", f"{15 - mape_dinner_lgbm:.2f} %")
            with col23:
                st.metric("Random Forest", f"{mape_dinner_rf:.2f} %", f"{15 - mape_dinner_rf:.2f} %")
        
        st.markdown(f"#### :{colors[selected_model]}[Default model: {selected_model}]")
    col1, col2 = st.columns(2)
    
    fig0 = create_series_plot_new(accu_preprocessed_filtered)
    st.plotly_chart(fig0, use_container_width=True, theme="streamlit")
    
    with st.sidebar:
        with st.form("my_form"):
            selected = st.selectbox("Select default model", colors.keys(), index=list(colors.keys()).index(selected_model))
            
            # Every form must have a submit button.
            submitted = st.form_submit_button("Submit")
            if submitted:
                file = '.default_model.csv'
                update_default_model(selected, category_selected, file=file)
                res = create_or_update_table("default_model")
                if res[0]:
                    default_model.loc[default_model.category==category_selected, "default_model"] = selected
                st.write(res[1])
                
    
    
    
    
    