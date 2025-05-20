import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import datetime
import re

# Dummy username & password
USERNAME = "Pushpal@2025"
PASSWORD = "Pushpal@202512345"

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    with st.form("login"):
        st.subheader("🔐 Login Required")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login = st.form_submit_button("Login")

        if login:
            if username == USERNAME and password == PASSWORD:
                st.session_state.logged_in = True
                st.success("Logged in successfully!")
            else:
                st.error("Incorrect credentials")
    st.stop()

st.set_page_config(page_title="GAME PROGRESSION", layout="wide")
st.title("📊 GAME PROGRESSION Dashboard")

# -------------------- FUNCTION TO EXPORT EXCEL -------------------- #
def generate_excel(df_export, retention_fig, drop_fig, drop_comb_fig):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Step 1: Remove duplicate levels from df_export
        df_export = df_export.drop_duplicates(subset='Level', keep='first').reset_index(drop=True)

        # Write dataframe to Excel
        df_export.to_excel(writer, sheet_name='Summary', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Summary']

        # Header format
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D9E1F2',
            'border': 1
        })

        # Cell format
        cell_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter'
        })

        # Red text and yellow fill format for drop and combo drop ≥ 3
        highlight_format = workbook.add_format({
            'font_color': 'red',
            'bg_color': 'yellow',
            'align': 'center',
            'valign': 'vcenter'
        })

        # Apply formats to the worksheet
        for col_num, value in enumerate(df_export.columns):
            worksheet.write(0, col_num, value, header_format)

        # Apply cell format with conditional formatting
        for row_num in range(1, len(df_export) + 1):
            for col_num in range(len(df_export.columns)):
                value = df_export.iloc[row_num - 1, col_num]
                col_name = df_export.columns[col_num]

                # Convert all numpy types to native Python types
                if isinstance(value, (np.generic, np.bool_)):
                    value = value.item()

                # Handle NaNs safely
                if pd.isna(value):
                    value = ""

                try:
                    if col_name in ['Game Play Drop', 'Popup Drop', 'Total Level Drop'] and isinstance(value, (int, float)) and value >= 3:
                        worksheet.write(row_num, col_num, value, highlight_format)
                    else:
                        worksheet.write(row_num, col_num, value, cell_format)
                except Exception as e:
                    st.warning(f"⚠️ Could not write value at row {row_num} col {col_num}: {e}")

        # Freeze top row
        worksheet.freeze_panes(1, 0)

        # Set column widths dynamically
        for i, col in enumerate(df_export.columns):
            column_len = max(df_export[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, column_len)

        # Insert Retention Chart
        retention_img = BytesIO()
        retention_fig.savefig(retention_img, format='png', dpi=300, bbox_inches='tight')
        retention_img.seek(0)
        worksheet.insert_image('M2', 'retention_chart.png', {'image_data': retention_img})

        # Insert total Drop Chart
        drop_img = BytesIO()
        drop_fig.savefig(drop_img, format='png', dpi=300, bbox_inches='tight')
        drop_img.seek(0)
        worksheet.insert_image('M37', 'drop_chart.png', {'image_data': drop_img})

        # Insert Combo Drop Chart
        drop_comb_img = BytesIO()
        drop_comb_fig.savefig(drop_comb_img, format='png', dpi=300, bbox_inches='tight')
        drop_comb_img.seek(0)
        worksheet.insert_image('M67', 'drop_comb_chart.png', {'image_data': drop_comb_img})

    output.seek(0)
    return output

# -------------------- MAIN FUNCTION -------------------- #
def main():
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
        df_start.columns = df_start.columns.str.strip().str.upper()
        level_columns = ['LEVEL', 'LEVELPLAYED', 'TOTALLEVELPLAYED', 'TOTALLEVELSPLAYED']
        level_col_start = next((col for col in df_start.columns if col in level_columns), None)
        user_col_start = next((col for col in df_start.columns if 'USER' in col), None)

        if level_col_start and user_col_start:
            df_start = df_start[[level_col_start, user_col_start]]

            def clean_level(x):
                try:
                    return int(re.search(r"(\d+)", str(x)).group(1))
                except:
                    return None

            df_start['LEVEL_CLEAN'] = df_start[level_col_start].apply(clean_level)
            df_start.dropna(inplace=True)
            df_start['LEVEL_CLEAN'] = df_start['LEVEL_CLEAN'].astype(int)
            df_start.sort_values('LEVEL_CLEAN', inplace=True)
            df_start.rename(columns={user_col_start: 'Start Users'}, inplace=True)
        else:
            st.error("❌ Required columns not found in start file.")
            return

        # ------------ CLEAN COMPLETE FILE ------------- #
        df_complete.columns = df_complete.columns.str.strip().str.upper()
        level_col_complete = next((col for col in df_complete.columns if col in level_columns), None)
        user_col_complete = next((col for col in df_complete.columns if 'USER' in col), None)

        # Get all additional columns we want to include
        additional_columns = ['PLAY_TIME_AVG','PLAYTIME_AVG', 'HINT_USED_SUM', 'RETRY_COUNT_SUM', 'SKIPPED_SUM', 'ATTEMPT_SUM','PREFAB_NAME']
        available_additional_cols = [col for col in additional_columns if col in df_complete.columns]
        df_complete[available_additional_cols] = df_complete[available_additional_cols].round(2)

        if level_col_complete and user_col_complete:
            # Include all additional columns we found
            cols_to_keep = [level_col_complete, user_col_complete] + available_additional_cols
            df_complete = df_complete[cols_to_keep]

            df_complete['LEVEL_CLEAN'] = df_complete[level_col_complete].apply(clean_level)
            df_complete.dropna(inplace=True)
            df_complete['LEVEL_CLEAN'] = df_complete['LEVEL_CLEAN'].astype(int)
            df_complete.sort_values('LEVEL_CLEAN', inplace=True)
            df_complete.rename(columns={user_col_complete: 'Complete Users'}, inplace=True)
        else:
            st.error("❌ Required columns not found in complete file.")
            return

        # ------------ MERGE AND CALCULATE METRICS ------------- #

        df = pd.merge(df_start, df_complete, on='LEVEL_CLEAN', how='outer').sort_values('LEVEL_CLEAN')

        # Find the higher of Level 1 or Level 2 Start Users for Retention base
        base_users = df[df['LEVEL_CLEAN'].isin([1, 2])]['Start Users'].max()

        # Calculate metrics
        df['Game Play Drop'] = (((df['Start Users'] - df['Complete Users']) / df['Start Users']) * 100)
        df['Popup Drop'] =( ((df['Complete Users'] - df['Start Users'].shift(-1)) / df['Complete Users']) * 100)
        df['Total Level Drop'] = (df['Game Play Drop'] + df['Popup Drop'])

         # Retention based on fixed highest value of Level 1 or 2 Start Users
       df['Retention %'] = ( (df['Start Users'] / base_users) * 100 )

       # Conditionally calculate 'Attempt' if 'RETRY_COUNT_SUM' exists
       if 'RETRY_COUNT_SUM' in df.columns:
          df['Attempt'] = df['RETRY_COUNT_SUM'] / df['Complete Users']

       # Round metrics
       metric_cols = ['Game Play Drop', 'Popup Drop', 'Total Level Drop', 'Retention %']
       if 'Attempt' in df.columns:
           metric_cols.append('Attempt')

      df[metric_cols] = df[metric_cols].round(2)


        

        # ------------ CHARTS ------------ #
        df_100 = df[df['LEVEL_CLEAN'] <= 100]

        # Custom x tick labels
        xtick_labels = []
        for val in np.arange(1, 101, 1):
            if val % 5 == 0:
                xtick_labels.append(f"$\\bf{{{val}}}$")  # Bold using LaTeX
            else:
                xtick_labels.append(str(val))

        # ------------ RETENTION CHART ------------ #
        st.subheader("📈 Retention Chart (Levels 1-100)")
        retention_fig, ax = plt.subplots(figsize=(15, 7))
        df_100 = df[df['LEVEL_CLEAN'] <= 100]

        ax.plot(df_100['LEVEL_CLEAN'], df_100['Retention %'],
                linestyle='-', color='#F57C00', linewidth=2, label='RETENTION')

        ax.set_xlim(1, 100)
        ax.set_ylim(0, 110)
        ax.set_xticks(np.arange(1, 101, 1))
        ax.set_yticks(np.arange(0, 110, 5))

        # Set labels with padding
        ax.set_xlabel("Level", labelpad=15)
        ax.set_ylabel("% Of Users", labelpad=15)

        ax.set_title(f"Retention Chart (Levels 1-100) | Version {version} | Date: {date_selected.strftime('%d-%m-%Y')}",
                     fontsize=12, fontweight='bold')

        # Custom x tick labels
        xtick_labels = []
        for val in np.arange(1, 101, 1):
            if val % 5 == 0:
                xtick_labels.append(f"$\\bf{{{val}}}$")  # Bold using LaTeX
            else:
                xtick_labels.append(str(val))
        ax.set_xticklabels(xtick_labels, fontsize=6)

        ax.tick_params(axis='x', labelsize=6)
        ax.grid(True, linestyle='--', linewidth=0.5)

        # Annotate data points below x-axis
        for x, y in zip(df_100['LEVEL_CLEAN'], df_100['Retention %']):
            if not np.isnan(y):
                ax.text(x, -5, f"{int(y)}", ha='center', va='top', fontsize=7)

        ax.legend(loc='lower left', fontsize=8)
        plt.tight_layout(rect=[0, 0.03, 1, 0.97])
        st.pyplot(retention_fig)

        # ------------ TOTAL DROP CHART ------------ #
        st.subheader("📉 Total Drop Chart (Levels 1-100)")
        drop_fig, ax2 = plt.subplots(figsize=(15, 6))
        bars = ax2.bar(df_100['LEVEL_CLEAN'], df_100['Total Level Drop'], color='#EF5350', label='DROP RATE')

        ax2.set_xlim(1, 100)
        ax2.set_ylim(0, max(df_100['Total Level Drop'].max(), 10) + 10)
        ax2.set_xticks(np.arange(1, 101, 1))
        ax2.set_yticks(np.arange(0, max(df_100['Total Level Drop'].max(), 10) + 11, 5))
        ax2.set_xlabel("Level")
        ax2.set_ylabel("% Of Users Drop")
        ax2.set_title(f"Total Level Drop Chart | Version {version} | Date: {date_selected.strftime('%d-%m-%Y')}",
                      fontsize=12, fontweight='bold')

        # Custom x tick labels
        ax2.set_xticklabels(xtick_labels, fontsize=6)
        ax2.tick_params(axis='x', labelsize=6)
        ax2.grid(True, linestyle='--', linewidth=0.5)

        # Annotate data points below x-axis
        for bar in bars:
            x = bar.get_x() + bar.get_width() / 2
            y = bar.get_height()
            ax2.text(x, -2, f"{y:.0f}", ha='center', va='top', fontsize=7)

        ax2.legend(loc='upper right', fontsize=8)
        plt.tight_layout()
        st.pyplot(drop_fig)

        # ------------ COMBO DROP CHART ------------ #
        st.subheader("📉 Combo Drop Chart (Levels 1-100)")
        drop_comb_fig, ax3 = plt.subplots(figsize=(15, 6))

        # Plot both drop types
        width = 0.4
        x = df_100['LEVEL_CLEAN']
        ax3.bar(x + width/2, df_100['Game Play Drop'], width, color='#66BB6A', label='Game Play Drop')
        ax3.bar(x - width/2, df_100['Popup Drop'], width, color='#42A5F5', label='Popup Drop')

        ax3.set_xlim(1, 100)
        max_drop = max(df_100['Game Play Drop'].max(), df_100['Popup Drop'].max())
        ax3.set_ylim(0, max(max_drop, 10) + 10)
        ax3.set_xticks(np.arange(1, 101, 1))
        ax3.set_yticks(np.arange(0, max(max_drop, 10) + 11, 5))
        ax3.set_xlabel("Level")
        ax3.set_ylabel("% Of Users Dropped")
        ax3.set_title(f"Game Play  & Popup Drop Chart | Version {version} | Date: {date_selected.strftime('%d-%m-%Y')}",
                      fontsize=12, fontweight='bold')

        # Custom x tick labels
        ax3.set_xticklabels(xtick_labels, fontsize=6)
        ax3.tick_params(axis='x', labelsize=6)
        ax3.grid(True, linestyle='--', linewidth=0.5)
        ax3.legend(loc='upper right', fontsize=8)
        plt.tight_layout()
        st.pyplot(drop_comb_fig)

        # ------------ DOWNLOAD SECTION ------------ #
        st.subheader("⬇️ Download Excel Report")

        # Prepare export dataframe - include all available additional columns
        export_columns = ['LEVEL_CLEAN', 'Start Users', 'Complete Users',
                         'Game Play Drop', 'Popup Drop', 'Total Level Drop',
                         'Retention %'] + available_additional_cols

        df_export = df[export_columns].rename(columns={'LEVEL_CLEAN': 'Level'})

        st.dataframe(df_export)

        # Generate and download Excel
        excel_data = generate_excel(df_export, retention_fig, drop_fig, drop_comb_fig)

        st.download_button(
            label="📥 Download Excel Report",
            data=excel_data,
            file_name=f"GAME_PROGRESSION_Report_{version}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()
