# Logistics Optimization Dashboard

A Python-based logistics optimization tool and interactive dashboard.
The optimizer reads shipment orders from an Excel file, geocodes pickup and delivery locations, computes distances, clusters deliveries into regions and solves a truck‐loading and routing assignment problem using Gurobi. The Streamlit dashboard allows you to upload data, adjust parameters, run the optimization and view or download results.

## Table of Contents

1. Features
2. Prerequisites
3. Installation
4. Configuration
5. Usage
6. File Structure
7. License

## Features

* **Data Cleaning & Sampling**
  Deduplicates orders, filters columns, handles missing data and samples a subset of orders.

* **Geocoding & Distance Calculation**
  Uses Nominatim (OpenStreetMap) to convert addresses to latitude/longitude.
  Computes geodesic distance between load and delivery points.

* **Clustering**
  Groups deliveries into cluster via K-Means representing the different regions in Europe.

* **Optimization Model**
  Mixed-integer programming (Pyomo + Gurobi) to assign orders to trucks under capacity constraints.
  Balances fixed truck allocation (α) vs. distance (β).

* **Interactive Dashboard**
  Streamlit interface for parameter adjustment, file upload, and visualization.
  Downloadable Excel reports for assignments, utilization, and summary.
  KPI: trucks used, truck utilization (%), pallet qty and distance travelled. 
  Plots: utilization bar chart, pallet volume by region and distance distribution.

## Prerequisites

* Python 3.8 or higher
* Gurobi with an Academic WLS license (environment variables set) 
* Internet access (for geocoding via Nominatim)

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/logistics-optimizer.git
   cd logistics-optimizer
   ```

2. **Set Gurobi credentials**
   Export your Gurobi access ID, secret, and license ID as environment variables:

   ```bash
   export GRB_WLSACCESSID="your-access-id"
   export GRB_WLSSECRET="your-secret"
   export GRB_LICENSEID="your-license-id"
   ```

3. **Verify Gurobi installation and license**

   ```bash
   gurobi_cl --help
   ```

## Configuration

Adjust these parameters in the Streamlit sidebar:

* **n\_clusters** (int): Number of delivery regions (K in K-Means).
* **sample\_size** (int): Number of random orders to sample.
* **max\_retries** (int): Extra trucks allowed if initial solution infeasible.

## Usage

1. **Launch the dashboard**

   ```bash
   streamlit run app.py
   ```

2. **Upload your Excel file**

   * Supported format: `.xlsx`
   * Required columns (case-insensitive, spaces/punctuation normalized):

     ```
     Company, Order ID, Status, Trip Reference,
     Load Point City, Load Point Postal Code, Load Point Country,
     Delivery Point City, Delivery Point Postal Code, Delivery Point Country,
     Pallet Qty, Pallet Type, Shipment Type,
     Order Creation Date, Expected Load Date, Expected Delivery Date,
     Actual Load Date, Actual Delivery Date, Temperature
     ```
 
3. **Set parameters using the sidebar sliders**

   * Number of Regions (2–15)
   * Sample Size (10–100)
   * Max Retries (0–5)

4. **Run Optimization**

   * Click **Run Optimization** and wait for completion.

5. **View & Download Results**

   * Download Excel reports:

     * Truck Assignments
     * Truck Utilization
     * Summary Report
   * Key Performance Indicators
   * Interactive dataframes and plots displayed in the app.

## File Structure

```
├── app.py                   # Streamlit dashboard script
├── optimizer.py             # Contains run_logistics_optimization()
└── README.md                # Project documentation
```

* **optimizer.py**
  Defines `run_logistics_optimization(file_path, n_clusters, alpha, beta, sample_size, max_retries)`, returns `(assignments_df, util_df, df_clean)`.

* **app.py**
  Implements Streamlit UI: sliders, file uploader, download links, tables and charts.

## License

This project is licensed under the **Gurobi Academic WLS** license. In case this license is not available replace with an open source solver like "GLPK". These are much slower than Gurobi and may requiere smaller sample sizes to fully optimize the logistics process. 
