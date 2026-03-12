"""Simple Streamlit dashboard for SmartSettle.

Run with:
    pip install streamlit
    streamlit run dashboard.py

This provides a web interface to upload a transactions CSV, run the
scheduler, and download the resulting JSON.  It uses the existing
utilities and scheduler from the project.
"""

import json
import streamlit as st
from io import StringIO
from typing import List, Dict, Any

import pandas as pd
import altair as alt

from utils import load_transactions, build_channels, save_results
from scheduler import Scheduler
from cost_calculator import (
    total_system_cost,
    compute_delay_penalty,
    compute_failure_cost,
)

# make page look more polished
st.set_page_config(
    page_title="SmartSettle Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.title("SmartSettle Payment Routing Optimizer 🚀")

# simple navigation buttons on top
if 'page' not in st.session_state:
    st.session_state['page'] = 'Home'

col1, col2, col3, col4 = st.columns(4)
if col1.button('Home'):
    st.session_state['page'] = 'Home'
if col2.button('Upload'):
    st.session_state['page'] = 'Upload'
if col3.button('Scheduler'):
    st.session_state['page'] = 'Scheduler'
if col4.button('Results'):
    st.session_state['page'] = 'Results'

# custom CSS for nicer look
st.markdown(
    """
    <style>
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        height:3em;
        width:100%;
        font-size:16px;
    }
    .stFileUploader>div>div {
        background-color: #fafafa;
        border: 2px dashed #4CAF50;
        border-radius: 8px;
    }
    .stFileUploader>div>label {
        color: #4CAF50;
        font-weight: bold;
    }
    .stMetric > div {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 10px;
    }
    .stDownloadButton>button {
        background-color: #1f77b4;
        color: white;
        font-size: 16px;
    }
    .big-header {
        font-size:1.5rem;
        font-weight:600;
    }
    /* box around sections */
    .stContainer {
        border:1px solid #ddd;
        border-radius:8px;
        padding:10px;
        margin-bottom:15px;
        background-color:#fff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    **Welcome!** Use this dashboard to upload a batch of transactions,
    run the scheduler, and inspect the results interactively.

    The output includes a detailed assignments table, cost breakdown, and
    the ability to export your results as JSON.
    """
)

st.markdown("---")

# provide sidebar instructions
with st.sidebar:
    st.header("Getting started")
    st.write("1. Upload a transactions CSV file.")
    st.write("2. (Optional) inspect the uploaded data as JSON.")
    st.write("3. Click **Run scheduler** to compute assignments.")
    st.write("4. Explore the charts and download results.")
    st.write("\n🎯 The dashboard colours and buttons are customised for clarity.")

uploaded = st.file_uploader("Transactions CSV", type=["csv"])

# place holders for metrics to be filled after scheduling
total_cost_placeholder = st.empty()
channel_cost_placeholder = st.empty()
delay_cost_placeholder = st.empty()
failure_cost_placeholder = st.empty()
# initialize with N/A
total_cost_placeholder.metric("Total Cost", "N/A")
channel_cost_placeholder.metric("Channel Fees", "N/A")
delay_cost_placeholder.metric("Delay Penalties", "N/A")
failure_cost_placeholder.metric("Failure Costs", "N/A")

if uploaded is not None:
    # read transactions into memory
    try:
        data = StringIO(uploaded.getvalue().decode("utf-8"))
        txs = load_transactions(data)
    except Exception as e:
        st.error(f"Failed to parse CSV: {e}")
        txs = []

    if txs:
        # preview the uploaded transactions as JSON and allow download
        with st.expander("Preview uploaded transactions (JSON) ", expanded=False):
            st.json(txs)
            json_bytes = json.dumps(txs, indent=2).encode('utf-8')
            st.download_button("Download TXs as JSON", json_bytes, file_name="transactions.json")

        # large green button created by CSS above
        if st.button("Run scheduler"):
            st.info("Scheduling in progress…")
            channels = build_channels()
            scheduler = Scheduler(channels)
            assignments, _ = scheduler.schedule(txs)
            cost = total_system_cost(txs, assignments)
            st.success("Scheduling completed!")

            # make lookup for cost breakdown
            tx_map = {tx['tx_id']: tx for tx in txs}
            details = []
            total_channel = 0.0
            total_delay = 0.0
            total_failure = 0.0

            progress = st.progress(0)
            for idx, a in enumerate(assignments, start=1):
                tx = tx_map.get(a['tx_id'], {})
                channel_fee = a.get('channel_fee', 0) or 0
                if a['channel_id'] is None or a['start_time'] is None:
                    failure = compute_failure_cost(tx)
                    delay_pen = 0.0
                    channel_fee = 0.0
                else:
                    delay = a['start_time'] - tx.get('arrival_time', 0)
                    delay_pen = compute_delay_penalty(tx.get('amount', 0), delay)
                    failure = 0.0
                total_channel += channel_fee
                total_delay += delay_pen
                total_failure += failure
                details.append({
                    'tx_id': a['tx_id'],
                    'channel': a['channel_id'],
                    'start_time': a['start_time'],
                    'channel_fee': channel_fee,
                    'delay_penalty': delay_pen,
                    'failure_cost': failure,
                })
                # update intermediate metrics for real-time feel
                channel_cost_placeholder.metric("Channel Fees", f"₹{total_channel:,.2f}")
                delay_cost_placeholder.metric("Delay Penalties", f"${total_delay:,.2f}")
                failure_cost_placeholder.metric("Failure Costs", f"${total_failure:,.2f}")
                progress.progress(idx / len(assignments))

            # final total cost
            total_cost_placeholder.metric("Total Cost", f"₹{cost:,.2f}")


            # build output JSON for preview/download
            output = {
                'assignments': assignments,
                'total_system_cost_estimate': cost,
                'breakdown': {
                    'channel': total_channel,
                    'delay': total_delay,
                    'failure': total_failure,
                }
            }

            # save results so they survive reruns and allow later UI
            st.session_state['results'] = {
                'txs': txs,
                'assignments': assignments,
                'details': details,
                'cost': cost,
                'total_channel': total_channel,
                'total_delay': total_delay,
                'total_failure': total_failure,
                'output': output,
            }
            # show graphs right away
            st.session_state['show_graphs'] = True

            df_details = pd.DataFrame(details)

            # transaction dataframe needed for charts
            df_txs = pd.DataFrame(txs)
            df_txs['delay'] = df_txs['max_delay']  # placeholder if needed

        # once results are available we show the extra buttons below
        if 'results' in st.session_state:
            res = st.session_state['results']
            st.download_button("Download result JSON", json.dumps(res['output'], indent=2), file_name="submission.json")
            # toggle show/hide graphs
            toggle_label = "Hide visualizations" if st.session_state.get('show_graphs') else "Show visualizations"
            if st.button(toggle_label):
                st.session_state['show_graphs'] = not st.session_state.get('show_graphs', False)
            # ensure they are visible on first run
            if 'show_graphs' not in st.session_state:
                st.session_state['show_graphs'] = True

        # render graphs if requested
        if st.session_state.get('show_graphs'):
            res = st.session_state['results']
            df_details = pd.DataFrame(res['details'])
            df_txs = pd.DataFrame(res['txs'])
            df_txs['delay'] = df_txs['max_delay']
            total_channel = res['total_channel']
            total_delay = res['total_delay']
            total_failure = res['total_failure']
            cost = res['cost']


            # create tabs container for visualizations
            tabs = st.tabs(["Summary", "Transactions", "Usage", "Distributions", "Capacity", "Cost"])

            # summary tab: metrics and JSON
            with tabs[0]:
                st.subheader("Cost Summary 📊")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Cost", f"₹{cost:,.2f}")
                col2.metric("Channel Fees", f"₹{total_channel:,.2f}")
                col3.metric("Delay Penalties", f"${total_delay:,.2f}")
                col4.metric("Failure Costs", f"${total_failure:,.2f}")

                with st.expander("View output JSON", expanded=False):
                    st.json(output)

                # simple bar breakdown
                breakdown = pd.DataFrame({
                    'category': ["Channel", "Delay", "Failure"],
                    'amount': [total_channel, total_delay, total_failure]
                })
                st.bar_chart(breakdown.set_index('category'))

            # transactions tab
            with tabs[1]:
                st.subheader("Assignment Details")
                st.dataframe(df_details.style.format({
                    'channel_fee': '₹{:,.2f}',
                    'delay_penalty': '₹{:,.2f}',
                    'failure_cost': '₹{:,.2f}',
                }))

                st.markdown("**Amount distribution**")
                st.altair_chart(
                    alt.Chart(df_txs).mark_bar(color='#4CAF50').encode(
                        x=alt.X('amount:Q', bin=True),
                        y='count()',
                    ),
                    use_container_width=True,
                )

                st.markdown("**Arrival vs Amount (scatter)**")
                st.altair_chart(
                    alt.Chart(df_txs).mark_circle(size=60, color='#1f77b4').encode(
                        x='arrival_time:Q',
                        y='amount:Q',
                        tooltip=['tx_id', 'amount', 'arrival_time']
                    ).interactive(),
                    use_container_width=True,
                )

            # usage tab
            with tabs[2]:
                st.subheader("Channel usage over time")
                if not df_details.empty:
                    usage = df_details.dropna(subset=['start_time']).groupby(['start_time', 'channel']).size().unstack(fill_value=0)
                    st.line_chart(usage)

            # distributions tab
            with tabs[3]:
                st.subheader("Priority & Delay Distributions")
                if not df_txs.empty:
                    st.altair_chart(
                        alt.Chart(df_txs).mark_bar(color='#ff7f0e').encode(
                            x='priority:O',
                            y='count()'
                        ),
                        use_container_width=True,
                    )

                st.markdown("**Delay distribution (assigned)**")
                if not df_details.empty:
                    df_assigned = df_details.dropna(subset=['start_time']).copy()
                    df_assigned['actual_delay'] = df_assigned.apply(
                        lambda r: r.start_time - tx_map.get(r.tx_id, {}).get('arrival_time', 0),
                        axis=1,
                    )
                    if not df_assigned['actual_delay'].empty:
                        st.altair_chart(
                            alt.Chart(df_assigned).mark_bar(color='#d62728').encode(
                                x=alt.X('actual_delay:Q', bin=True),
                                y='count()',
                            ),
                            use_container_width=True,
                        )

            # capacity tab (bar chart of usage vs capacity)
            with tabs[4]:
                st.subheader("Channel capacity comparison")
                if not df_details.empty:
                    usage = df_details.dropna(subset=['start_time']).groupby('channel').size().reset_index(name='used')
                    chs = build_channels()
                    cap_map = {c.channel_id: c.capacity for c in chs}
                    usage['capacity'] = usage['channel'].map(cap_map)
                    usage_melt = usage.melt(id_vars='channel', value_vars=['used','capacity'], var_name='type', value_name='count')
                    chart = alt.Chart(usage_melt).mark_bar().encode(
                        x='channel:O',
                        y='count:Q',
                        color='type:N',
                        tooltip=['channel','type','count']
                    )
                    st.altair_chart(chart, use_container_width=True)

            # cost tab (bar) instead of pie
            with tabs[5]:
                st.subheader("Cost breakdown")
                breakdown_df = pd.DataFrame({
                    'category': ['Channel', 'Delay', 'Failure'],
                    'amount': [total_channel, total_delay, total_failure]
                })
                chart = alt.Chart(breakdown_df).mark_bar(color='#17becf').encode(
                    x='category:N',
                    y='amount:Q',
                    tooltip=['category','amount']
                )
                st.altair_chart(chart, use_container_width=True)

            st.markdown("---")

            # allow user to download JSON
            output = {
                'assignments': assignments,
                'total_system_cost_estimate': cost,
                'breakdown': {
                    'channel': total_channel,
                    'delay': total_delay,
                    'failure': total_failure,
                }
            }
            b = json.dumps(output, indent=2)
            st.download_button("Download JSON", b, file_name="submission.json")
