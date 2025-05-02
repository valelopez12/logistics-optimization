import os
import time
import numpy as np
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from sklearn.cluster import KMeans
from pyomo.environ import *
from pyomo.opt import SolverFactory, TerminationCondition

def run_logistics_optimization(file_path, n_clusters=10, alpha=0.7, beta=0.3, sample_size=50, max_retries=2):
    df = pd.read_excel(file_path)

    # Gurobi credentials
    os.environ['GRB_WLSACCESSID'] = 'insert access ID'
    os.environ['GRB_WLSSECRET'] = 'insert Key'
    os.environ['GRB_LICENSEID'] = 'insert License ID'

    df = df.drop_duplicates(subset='Order ID', keep='last')
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('[^a-zA-Z0-9_]', '', regex=True)
    df = df.loc[:, df.isnull().mean() <= 0.5]

    rel_columns = [
        'company', 'order_id', 'status', 'trip_reference',
        'load_point_city', 'load_point_postal_code', 'load_point_country',
        'delivery_point_city', 'delivery_point_postal_code', 'delivery_point_country',
        'pallet_qty', 'pallet_type', 'shipment_type',
        'order_creation_date', 'expected_load_date', 'expected_delivery_date',
        'actual_load_date', 'actual_delivery_date', 'temperature'
    ]
    df = df[rel_columns]

    for col in ['order_creation_date', 'expected_load_date', 'expected_delivery_date', 'actual_load_date', 'actual_delivery_date']:
        df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)

    df = df[df['actual_load_date'].isna() & df['actual_delivery_date'].isna()].copy()
    df = df.sample(sample_size, random_state=42).copy()

    geolocator = Nominatim(user_agent="logistics_optimizer")
    address_cache = {}

    def get_coordinates_cached(address):
        if address in address_cache:
            return address_cache[address]
        try:
            location = geolocator.geocode(address, timeout=10)
            if location:
                coords = (location.latitude, location.longitude)
                address_cache[address] = coords
                time.sleep(1)
                return coords
        except:
            pass
        address_cache[address] = None
        return None

    df['load_address'] = df['load_point_city'] + ', ' + df['load_point_postal_code'].astype(str) + ', ' + df['load_point_country']
    df['delivery_address'] = df['delivery_point_city'] + ', ' + df['delivery_point_postal_code'].astype(str) + ', ' + df['delivery_point_country']
    df['load_coords'] = df['load_address'].apply(get_coordinates_cached)
    df['delivery_coords'] = df['delivery_address'].apply(get_coordinates_cached)

    def compute_distance_km(row):
        if row['load_coords'] and row['delivery_coords']:
            return geodesic(row['load_coords'], row['delivery_coords']).km
        return None

    df['distance_km'] = df.apply(compute_distance_km, axis=1)

    coords = df['delivery_coords'].dropna().tolist()
    coords_array = np.array(coords)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(coords_array)
    df.loc[df['delivery_coords'].notna(), 'cluster_id'] = labels
    df = df[df['cluster_id'].notna()].copy()
    df['cluster_id'] = df['cluster_id'].astype(int)
    cluster_id_to_region = {cid: f"Region {i+1}" for i, cid in enumerate(sorted(df['cluster_id'].unique()))}
    df['cluster_name'] = df['cluster_id'].map(cluster_id_to_region)

    TRUCK_CAPACITY = int(df[df['shipment_type'] == 'FTL']['pallet_qty'].max())
    df = df[df['pallet_qty'] <= TRUCK_CAPACITY].copy()
    df = df.reset_index(drop=True)
    df['order_id'] = df['order_id'].astype(str)
    df.set_index('order_id', inplace=True)

    all_assignments = []
    all_utilization = []

    for cluster_id, cluster_name in df.groupby('cluster_id')['cluster_name'].first().items():
        df_cluster = df[df['cluster_id'] == cluster_id].copy()
        distance_dict = df_cluster['distance_km'].to_dict()

        if len(df_cluster) == 0:
            continue

        orders = df_cluster.index.tolist()
        total_pallets = df_cluster['pallet_qty'].sum()
        initial_trucks = int(np.ceil(total_pallets / TRUCK_CAPACITY))
        success = False

        for extra in range(max_retries + 1):
            num_trucks = initial_trucks + extra
            trucks = list(range(1, num_trucks + 1))

            try:
                model = ConcreteModel()
                model.O = Set(initialize=orders)
                model.T = Set(initialize=trucks)
                model.p = Param(model.O, initialize=df_cluster['pallet_qty'].to_dict())
                model.c = Param(initialize=TRUCK_CAPACITY)
                model.x = Var(model.O, model.T, domain=Binary)
                model.y = Var(model.T, domain=Binary)

                def obj_rule(m):
                    truck_cost = alpha * sum(m.y[t] for t in m.T)
                    distance_cost = beta * sum(distance_dict[o] * m.x[o, t] for o in m.O for t in m.T)
                    return truck_cost + distance_cost

                model.obj = Objective(rule=obj_rule, sense=minimize)

                def one_truck_per_order(m, o):
                    return sum(m.x[o, t] for t in m.T) == 1
                model.one_truck = Constraint(model.O, rule=one_truck_per_order)

                def capacity(m, t):
                    return sum(m.p[o] * m.x[o, t] for o in m.O) <= m.c * m.y[t]
                model.capacity = Constraint(model.T, rule=capacity)

                solver = SolverFactory('gurobi')
                results = solver.solve(model, tee=False)

                if results.solver.termination_condition != TerminationCondition.optimal:
                    continue

                success = True
                for t in model.T:
                    if value(model.y[t]) == 1:
                        assigned_orders = [o for o in model.O if value(model.x[o, t]) == 1]
                        total = sum(df_cluster.loc[o, 'pallet_qty'] for o in assigned_orders)
                        total_km = sum(df_cluster.loc[o, 'distance_km'] for o in assigned_orders)

                        truck_name = f"Region {cluster_id + 1} - Truck {t}"
                        all_utilization.append({
                            'cluster': cluster_name,
                            'truck': truck_name,
                            'pallets_loaded': total,
                            'capacity': TRUCK_CAPACITY,
                            'utilization_pct': round(total / TRUCK_CAPACITY * 100, 2),
                            'total_distance_km': round(total_km, 2)
                        })

                        for o in assigned_orders:
                            all_assignments.append({
                                'order_id': o,
                                'cluster': cluster_name,
                                'assigned_truck': truck_name,
                                'pallet_qty': df_cluster.loc[o, 'pallet_qty']
                            })
                break

            except:
                continue

    assignments_df = pd.DataFrame(all_assignments)
    util_df = pd.DataFrame(all_utilization)
    df.reset_index(inplace=True)
    return assignments_df, util_df, df
