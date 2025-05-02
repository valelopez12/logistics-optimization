import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from optimizer import run_logistics_optimization
import pandas as pd

def to_excel_download_link(df, filename):
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    b64 = base64.b64encode(buffer.read()).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">Download {filename}</a>'
    return href


def main():
    st.title("Logistics Optimization Dashboard")

    st.sidebar.header("Optimization Settings")
    n_clusters = st.sidebar.slider("Number of Regions (Clusters)", min_value=2, max_value=15, value=5)
    sample_size = st.sidebar.slider("Sample Size (Orders)", 10, 100, 50, step=10)
    max_retries = st.sidebar.slider("Max Retries per Cluster", 0, 5, 2)

    file = st.file_uploader("Upload Excel file", type=["xlsx"])

    if file:
        if st.button("Run Optimization"):
            with st.spinner("Optimizing routes and trucks..."):
                assignments_df, util_df, df_clean = run_logistics_optimization(
                    file_path=file,
                    n_clusters=n_clusters,
                    alpha=0.7,
                    beta=0.3,
                    sample_size=sample_size,
                    max_retries=max_retries
                )

            st.success("Optimization complete.")

            # --- KPIs ---
            total_trucks = util_df['truck'].nunique()
            avg_util = util_df['utilization_pct'].mean()
            total_pallets = assignments_df['pallet_qty'].sum()
            total_distance = util_df['total_distance_km'].sum()

            st.subheader("Key Performance Indicators")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Trucks Used", total_trucks)
            col2.metric("Avg. Utilization %", f"{avg_util:.2f}%")
            col3.metric("Total Pallets", total_pallets)
            col4.metric("Total Distance (km)", f"{total_distance:.0f}")

            # Create summary report
            df_summary = df_clean.copy()
            df_summary['order_id'] = df_summary['order_id'].astype(str)

            summary = pd.merge(assignments_df, df_summary, on='order_id', how='left')

            summary = summary[[
                'order_id',
                'company',
                'pallet_qty_x',
                'load_address',
                'load_coords',
                'delivery_address',
                'delivery_coords',
                'distance_km',
                'assigned_truck',
                'cluster'
            ]]

            summary.columns = [
                'Order ID',
                'Company',
                'Pallet Qty',
                'Load Address',
                'Load Coordinates',
                'Delivery Address',
                'Delivery Coordinates',
                'Distance (km)',
                'Assigned Truck',
                'Region'
            ]

            # Download buttons
            st.markdown(to_excel_download_link(assignments_df, "Truck_Assignments.xlsx"), unsafe_allow_html=True)
            st.markdown(to_excel_download_link(util_df, "Truck_Utilization.xlsx"), unsafe_allow_html=True)
            st.markdown(to_excel_download_link(summary, "Summary_Report.xlsx"), unsafe_allow_html=True)

            # Display tables
            st.subheader("Summary Report")
            st.dataframe(summary)

            st.subheader("Truck Assignments")
            st.dataframe(assignments_df)

            st.subheader("Truck Utilization")
            st.dataframe(util_df)

            # Visualization: Utilization
            st.subheader("Truck Utilization (%)")
            fig1, ax1 = plt.subplots(figsize=(12, 5))
            util_sorted = util_df.sort_values("utilization_pct")
            ax1.bar(util_sorted['truck'], util_sorted['utilization_pct'])
            ax1.set_ylabel("Utilization %")
            ax1.set_xticklabels(util_sorted['truck'], rotation=45, ha='right')
            st.pyplot(fig1)

            # Visualization: Pallet Volume
            st.subheader("Pallet Volume by Region")
            volume = assignments_df.groupby('cluster')['pallet_qty'].sum().sort_values()
            fig2, ax2 = plt.subplots()
            volume.plot(kind='barh', ax=ax2)
            ax2.set_xlabel("Pallets")
            st.pyplot(fig2)

            # Visualization: Distance Distribution
            st.subheader("Delivery Distance by Region")
            fig3, ax3 = plt.subplots()
            sns.boxplot(data=df_clean, x='cluster_name', y='distance_km', ax=ax3)
            ax3.set_ylabel("Distance (km)")
            ax3.set_xticklabels(ax3.get_xticklabels(), rotation=45)
            st.pyplot(fig3)

        else:
            st.info("Adjust parameters and click Run Optimization")

if __name__ == "__main__":
    main()
