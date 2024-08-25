import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from datetime import date, timedelta

# Set the page title and icon
st.set_page_config(
    page_title="ETF Investment Growth Analyzer",  # Title that appears on the browser tab
    page_icon="📈",  # Optional: An emoji or path to an icon
    layout="wide"  # Optional: Use 'wide' for a wider layout or 'centered' for a centered layout
)

# Title and Introductory Message
st.title("ETF Investment Growth Analyzer")
st.markdown(
    """
    **Disclaimer:** Stock performance is inherently unpredictable, but analyzing past performance can provide insights 
    that may guide future investment decisions. This ETF analysis tool aims to assist you in making more informed 
    investing choices by evaluating historical performance metrics.
    """
)

# List of high-volume ETFs
high_volume_etfs = [
    "SPY", "IVV", "VOO", "QQQ", "VTI", "EEM", "IWM", "XLK", "XLF", "TLT", "Enter your own"
]

# Dropdown menu for selecting an ETF or entering a custom one
selected_etf = st.selectbox("Select an ETF", high_volume_etfs)

# Handle custom ETF input if "Enter your own" is selected
if selected_etf == "Enter your own":
    etf_symbol = st.text_input("Enter ETF Symbol", "").upper()
else:
    etf_symbol = selected_etf

# Set the minimum date to 1950-01-01 and allow the user to select dates
min_date = pd.Timestamp('1950-01-01')
start_date = st.date_input("Start Date", value=date.today() - timedelta(days=365), min_value=min_date)
end_date = st.date_input("End Date", value=date.today())

# Convert start_date and end_date to timezone-aware Timestamps
start_date = pd.Timestamp(start_date).tz_localize('America/New_York')
end_date = pd.Timestamp(end_date).tz_localize('America/New_York')

# User input for initial investment
initial_investment = st.number_input("Initial Investment Amount ($)", value=1000)

# Risk-free rate (for Sharpe Ratio calculation)
risk_free_rate = 0.02  # Assuming 2% annual risk-free rate (e.g., from government bonds)

# Validate and analyze when the user clicks the button
if st.button("Analyze Growth"):
    if start_date >= end_date:
        st.error("End date must be after the start date.")
    elif not etf_symbol:
        st.error("Please enter an ETF symbol.")
    else:
        # Validate the ETF symbol by trying to download the data
        data = yf.download(etf_symbol, start=start_date, end=end_date)
        
        if data.empty:
            st.error(f"'{etf_symbol}' is not a valid ETF symbol or has no data for the selected date range.")
        else:
            # Calculate daily returns
            data['Daily Return'] = data['Adj Close'].pct_change().dropna()

            # Calculate cumulative returns and investment value over time
            data['Cumulative Return'] = data['Adj Close'].pct_change().fillna(0).add(1).cumprod()
            data['Investment Value'] = initial_investment * data['Cumulative Return']

            # Annualized Return (CAGR)
            total_return = data['Cumulative Return'].iloc[-1] - 1
            years = (end_date - start_date).days / 365.25
            cagr = (1 + total_return)**(1/years) - 1

            # Annualized Volatility
            daily_volatility = data['Daily Return'].std()
            annualized_volatility = daily_volatility * (252 ** 0.5)
            
            # Annualized Sharpe Ratio
            daily_excess_return = data['Daily Return'] - (risk_free_rate / 252)
            daily_sharpe_ratio = daily_excess_return.mean() / daily_volatility
            annualized_sharpe_ratio = daily_sharpe_ratio * (252 ** 0.5)
            
            # Beta calculation: comparing to S&P 500 as the market benchmark
            market_data = yf.download('^GSPC', start=start_date, end=end_date)
            if not market_data.empty:
                market_return = market_data['Adj Close'].pct_change().dropna()
                covariance = data['Daily Return'].cov(market_return)
                market_variance = market_return.var()
                beta = covariance / market_variance if market_variance != 0 else None
            else:
                beta = None

            # Dividend yield (sum of dividends over the period / initial price)
            dividends = yf.Ticker(etf_symbol).dividends
            if not dividends.empty:
                # Ensure dividends.index is timezone-aware and matches start_date and end_date
                dividends = dividends.tz_convert('America/New_York')
                dividends = dividends[(dividends.index >= start_date) & (dividends.index <= end_date)]
                dividend_yield = dividends.sum() / data['Adj Close'].iloc[0]
            else:
                dividend_yield = None

            # Generate a table showing the value of the investment for each year
            data['Year'] = data.index.year
            annual_data = data.groupby('Year').last()  # Get the last available data point for each year
            annual_table = annual_data[['Investment Value']].reset_index()

            st.subheader(f"Growth of ${initial_investment} invested in {etf_symbol}")
            st.write(annual_table)  # Show the table with year-end values

            st.write(f"**Annualized Return (CAGR):** {cagr:.2%}")
            st.write(f"**Volatility (Annualized):** {annualized_volatility:.2%}")
            st.write(f"**Sharpe Ratio (Annualized):** {annualized_sharpe_ratio:.2f}")
            st.write(f"**Beta (vs S&P 500):** {beta:.2f}" if beta is not None else "Beta: N/A")
            st.write(f"**Dividend Yield:** {dividend_yield:.2%}" if dividend_yield is not None else "Dividend Yield: N/A")

            # Plot the investment growth using Plotly
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=data.index, 
                y=data['Investment Value'],
                mode='lines',
                name=f"Investment Value in {etf_symbol}",
                hovertemplate='%{y:.2f}'  # Shows the dollar amount on hover
            ))
            fig.update_layout(
                title=f"{etf_symbol} Growth Model from {start_date.date()} to {end_date.date()}",
                xaxis_title="Date",
                yaxis_title="Value ($)",
                hovermode="x"
            )
            st.plotly_chart(fig)

# Footer with the creator's name
st.markdown(
    """
    ---
    **Created by Gurbaaz Sindhar**
    """
)

