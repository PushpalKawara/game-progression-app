import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import datetime
import re

st.set_page_config(page_title="GAME PROGRESSION", layout="wide")
st.title("📊 GAME PROGRESSION Dashboard")

# -------------- FILE UPLOAD SECTION ------------------ #
start_file = st.file_uploader("📂 Upload Start Level File", type=["xlsx", "csv"])
complete_file = st.file_uploader("📂 Upload Complete Level File", type=["xlsx", "csv"])
version = st.text_input("📌 Game Version", value="1.0.0")
date_selected = st.date_input("📅 Select Date", value=datetime.date.today())

if start_file and complete_file:
    # Load files
    df_start = pd.read_excel(start_file) if start_file.name.endswith(".xlsx") else pd.read_csv(start_file)
    df_complete = pd.read_excel(complete_file) if complete_file.name.endswith(".xlsx") else pd.read_csv(complete_file)

    # ------------ CLEAN START FILE ------------- #
    level_col_start = [col for col in df_start.columns if 'level' in col.lower()][0]
    user_col_start = [col for col in df_start.columns if 'user' in col.lower()][0]
    df_start['LEVEL_CLEAN'] = df_start[level_col_start].astype(str).str.extract('(\d+)').astype(int)
    df_start = df_start[[user_col_start, 'LEVEL_CLEAN']]
    df_start.rename(columns={user_col_start: 'Start Users'}, inplace=True)

    # ------------ CLEAN COMPLETE FILE ------------- #
    level_col_comp = [col for col in df_complete.columns if 'level' in col.lower()][0]
    user_col_comp = [col for col in df_complete.columns if 'user' in col.lower()][0]
    df_complete['LEVEL_CLEAN'] = df_complete[level_col_comp].astype(str).str.extract('(\d+)').astype(int)
    df_complete.rename(columns={user_col_comp: 'Complete Users'}, inplace=True)

    # ------------ MERGE BOTH ------------- #
    df = pd.merge(df_start, df_complete, on='LEVEL_CLEAN', how='inner')

    # ------------ METRIC CALCULATIONS ------------- #
    df['Game Play Drop'] = ((df['Start Users'] - df['Complete Users']) / df['Start Users']) * 100
    df['Popup Drop'] = ((df['Complete Users'].shift(1) - df['Start Users']) / df['Complete Users'].shift(1)) * 100
    df['Total Level Drop'] = ((df['Start Users'].shift(1) - df['Complete Users']) / df['Start Users'].shift(1)) * 100
    max_start_users = df['Start Users'].max()
    df['Retention %'] = (df['Start Users'] / max_start_users) * 100

    metric_cols = ['Game Play Drop', 'Popup Drop', 'Total Level Drop', 'Retention %']
    df[metric_cols] = df[metric_cols].round(2)

    # Include gameplay columns if available
    optional_cols = ['PLAYTIME', 'HINT_USED_SUM', 'RETRY_COUNT_SUM', 'SKIPPED_SUM']
    for col in optional_cols:
        if col in df_complete.columns:
            df[col] = df_complete[col]

    df.sort_values(by='LEVEL_CLEAN', inplace=True)

    # ------------ RETENTION CHART ------------ #
    st.subheader("📈 Retention Chart (Levels 1–100)")
    retention_fig, ax = plt.subplots(figsize=(15, 6))
    df1_100 = df[df['LEVEL_CLEAN'] <= 100]
    ax.plot(df1_100['LEVEL_CLEAN'], df1_100['Retention %'], color='orange', linewidth=2, label='Retention %')
    ax.set_title("Retention Curve")
    ax.set_xlabel("Level")
    ax.set_ylabel("Retention %")
    ax.set_xticks(np.arange(1, 101, 5))
    ax.grid(True)
    ax.legend()
    st.pyplot(retention_fig)

    # ------------ DROP CHART ------------ #
    st.subheader("📉 Total Level Drop Chart")
    drop_fig, ax2 = plt.subplots(figsize=(15, 6))
    ax2.bar(df1_100['LEVEL_CLEAN'], df1_100['Total Level Drop'], color='red', label='Total Level Drop')
    ax2.set_title("Total Level Drop %")
    ax2.set_xlabel("Level")
    ax2.set_ylabel("% Drop")
    ax2.set_xticks(np.arange(1, 101, 5))
    ax2.grid(True)
    ax2.legend()
    st.pyplot(drop_fig)

    # ------------ GAMEPLAY & POPUP DROP CHART ------------ #
    st.subheader("📉 Game Play & Popup Drop Chart")
    drop_comb_fig, ax3 = plt.subplots(figsize=(15, 6))
    ax3.plot(df1_100['LEVEL_CLEAN'], df1_100['Game Play Drop'], color='purple', label='Game Play Drop')
    ax3.plot(df1_100['LEVEL_CLEAN'], df1_100['Popup Drop'], color='blue', label='Popup Drop')
    ax3.set_title("Game Play & Popup Drop")
    ax3.set_xlabel("Level")
    ax3.set_ylabel("Drop %")
    ax3.grid(True)
    ax3.legend()
    st.pyplot(drop_comb_fig)

    # ------------ DOWNLOADABLE EXCEL FUNCTION ------------ #
    def generate_excel(df, retention_fig, drop_fig, drop_comb_fig):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Summary', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Summary']

            # Insert Retention Chart
            retention_img = BytesIO()
            retention_fig.savefig(retention_img, format='png')
            retention_img.seek(0)
            worksheet.insert_image('M2', 'retention_chart.png', {'image_data': retention_img})

            # Insert Drop Chart
            drop_img = BytesIO()
            drop_fig.savefig(drop_img, format='png')
            drop_img.seek(0)
            worksheet.insert_image('M37', 'drop_chart.png', {'image_data': drop_img})

            # Insert Gameplay & Popup Drop Chart
            combo_img = BytesIO()
            drop_comb_fig.savefig(combo_img, format='png')
            combo_img.seek(0)
            worksheet.insert_image('M75', 'combo_drop_chart.png', {'image_data': combo_img})

        output.seek(0)
        return output

    # Final dataframe with renamed column
    df_export = df[['LEVEL_CLEAN', 'Start Users', 'Complete Users', 'Game Play Drop', 'Popup Drop', 'Total Level Drop',
                    'Retention %', 'PLAYTIME', 'HINT_USED_SUM', 'RETRY_COUNT_SUM', 'SKIPPED_SUM']].rename(
        columns={'LEVEL_CLEAN': 'Level'})

    st.subheader("⬇️ Download Excel Report")
    st.dataframe(df_export)

    excel_data = generate_excel(df_export, retention_fig, drop_fig, drop_comb_fig)

    st.download_button(
        label="📥 Download Excel Report",
        data=excel_data,
        file_name=f"GAME_PROGRESSION_Report_{version}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
