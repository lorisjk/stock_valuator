<!--
 enter update date here
-->
**Latest update:**
Fixed split adjustions by back looking double checking against yfinance data to approximate split count.
Before we simply compared a outlier against th most recent data point, which led to false approximations and wrong multiples. Now fixed, for more info see: [Repo](https://github.com/lorisjk/stock_valuator.git)