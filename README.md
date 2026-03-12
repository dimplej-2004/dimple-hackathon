# SmartSettle – Payment Routing & Settlement Optimizer

## Overview

SmartSettle is a FinTech simulation system that optimizes how digital payment transactions are routed across multiple settlement channels. The system assigns each incoming transaction to the most suitable channel while minimizing total system cost and avoiding delays.

The project includes an **interactive Streamlit dashboard** that allows users to upload transaction data, run the routing algorithm, and visualize scheduling decisions and system performance.

---

# Problem Statement

Modern payment systems offer multiple settlement channels with different processing speeds, costs, and capacities.

Routing all payments through the fastest channel is expensive, while routing everything through the cheapest channel may introduce delays.

SmartSettle solves this problem by designing a scheduling algorithm that balances:

• Channel fees
• Transaction delay penalties
• System capacity constraints
• Transaction deadlines

The goal is to **minimize total system cost while maintaining transaction reliability**.

---

# Key Features

## Interactive Dashboard

A live dashboard built with **Streamlit** that visualizes transaction routing decisions.

The dashboard displays:

• Uploaded transaction dataset
• Channel assignment results
• Total system cost
• Failed transactions
• Channel usage over time
• Historical failure graph

---

## Smart Routing Algorithm

The system implements a **greedy scheduling algorithm** that:

• Assigns transactions to FAST, STANDARD, or BULK channels
• Respects channel capacity limits
• Ensures start time ≥ arrival time
• Ensures transactions start before deadline
• Marks transactions as failed if scheduling is impossible

---

## Settlement Channels

| Channel  | Fee   | Latency | Capacity      |
| -------- | ----- | ------- | ------------- |
| FAST     | ₹5    | 1 min   | 2 concurrent  |
| STANDARD | ₹1    | 3 min   | 4 concurrent  |
| BULK     | ₹0.20 | 10 min  | 10 concurrent |

---

# Cost Model

For successful transactions:

channel_fee + delay_penalty

delay_penalty = 0.001 × amount × delay

For failed transactions:

failure_penalty = 0.5 × amount

Total System Cost =
Sum of all channel fees + delay penalties + failure penalties

The optimization algorithm attempts to **minimize this total cost**.

---

# Dashboard Visualizations

The Streamlit dashboard provides the following insights:

### Uploaded Transactions

Displays the original **transactions.csv** file uploaded by the user.

### Routing Results

Shows channel assignments and scheduling results for each transaction.

### System Metrics

Displays key performance indicators:

• Total Transactions
• Successful Transactions
• Failed Transactions
• Total System Cost

### Channel Usage Over Time

A visualization showing how many transactions are processed simultaneously on each settlement channel.

### Failed Transaction History

A time-based graph showing when transactions failed due to capacity or deadline constraints.

This helps identify **system congestion and bottlenecks**.

### Cost Breakdown

A chart showing contributions from:

• Channel Fees
• Delay Penalties
• Failure Penalties

---

# Input Format

The system expects a CSV file named **transactions.csv** with the following structure:

tx_id,amount,arrival_time,max_delay,priority

Example:

T1,10000,0,10,5
T2,500,1,30,2
T3,2000,2,5,4

---

# Project Structure

```
smartsettle/
│
├── app.py
├── transactions.csv
├── README.md
```

---

# Installation

Install required Python libraries:

pip install streamlit pandas plotly

---

# Running the Application

Run the Streamlit dashboard using:

streamlit run app.py

The dashboard will open in your browser.

---

# Technology Stack

Frontend Dashboard
Streamlit

Backend Processing
Python

Data Handling
Pandas

Visualization
Plotly

---

# Future Improvements

Possible enhancements for future versions:

• Machine learning based routing decisions
• Dynamic fee optimization
• Real-time payment stream simulation
• Channel outage simulation
• Predictive congestion detection

---

# Use Cases

SmartSettle can simulate optimization strategies for:

• Digital payment networks
• Banking settlement systems
• FinTech transaction routing
• High-volume payment infrastructures

---

# Conclusion

SmartSettle demonstrates how intelligent routing strategies can reduce costs and improve efficiency in digital payment systems.

By combining algorithmic scheduling with interactive visualization, the system provides a powerful tool for analyzing payment network performance.

---
