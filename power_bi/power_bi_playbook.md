# Corporate-Grade Power BI Enterprise Playbook

This playbook establishes the technical guidelines, complex DAX formulas, and high-density visual specifications required to build a true **Enterprise Analytics Portal** from scratch. 

We completely reject "school-project" simplicity (which relies on single cards and basic bar charts) in favor of **dense data matrices, multi-tiered hierarchies, drill-down capabilities, advanced DAX, and professional HSL-based conditional formatting**.

---

## 🎨 1. Enterprise Visual Design & Grid System

To look corporate, the dashboard uses a **Unified Dark Slate Glassmorphic Theme** with high information density, clear visual hierarchies, and distinct functional sections.

### Color Tokens (Save as `CorporateTheme.json` and import into Power BI):
```json
{
  "name": "Apex Enterprise Slate",
  "dataColors": ["#00F2FE", "#10B981", "#8B5CF6", "#F59E0B", "#EF4444", "#3B82F6", "#EC4899"],
  "background": "#080C14",
  "foreground": "#111827",
  "tableAccent": "#00F2FE"
}
```

### Visual Layout Grid (High Density):
```
+------------------------------------------------------------------------------------------------+
|  [Logo] APEXANALYTICS PORTAL   |   PAGE 1: B2C E-COMMERCE   [PAGE 2: B2B AGENCY]   [PAGE 3: ATTRIBUTION]  |
+------------------------------------------------------------------------------------------------+
|  SLICER PANE (COLLAPSIBLE / SLIDE-OUT PANEL)                                                   |
|  [Region Dropdown]   [Year Slicer]   [Industry Selector]   [Account Manager Multi-Select]     |
+------------------------------------------------------------------------------------------------+
|  +-------------------+ +-------------------+ +-------------------+ +-------------------------+ |
|  | TOTAL BILLING     | | MANAGED AD SPEND  | | OVERALL ROAS      | | AM TARGET ATTAINMENT    | |
|  | $33.4M (YoY +12%) | | $54.2M            | | 12.11x            | | [████████░░░] 82.5%  🟢 | |
|  +-------------------+ +-------------------+ +-------------------+ +-------------------------+ |
|                                                                                                |
|  +--------------------------------------------------+ +--------------------------------------+ |
|  | DENSE ACCOUNT MANAGER PORTFOLIO MATRIX            | | CHANNELS EFFICIENCY GAUGES           | |
|  | AM / Region / Client  | Billing | Spend | ROAS   | | TikTok  [████████████] 23.1x  🟢     | |
|  | ▼ Michael Chang (APAC)                           | | YouTube [██████████░░] 23.2x  🟢     | |
|  |   ├─ Acro Corp        | $2.4M   | $3.1M | 14.2x  | | Meta    [██████░░░░░░] 13.0x  🟡     | |
|  |   └─ Beta Logistics   | $1.1M   | $1.5M | 11.1x  | | Google  [██░░░░░░░░░░] 5.9x   🔴     | |
|  +--------------------------------------------------+ +--------------------------------------+ |
|                                                                                                |
|  +-------------------------------------------------------------------------------------------+ |
|  | MONTH-OVER-MONTH CLIENT BILLING COHORT RETENTION HEATMAP (MATRIX VIEW)                     | |
|  | Cohort Month | Active Clients | M0      | M1      | M2      | M3      | M4      | M5        | |
|  | 2024-02      | 8              | [100%]  | [101%]  | [101%]  | [99%]   | [100%]  | [98%]     | |
|  | 2024-03      | 12             | [100%]  | [98%]   | [97%]   | [97%]   | [95%]   | [92%]     | |
|  +-------------------------------------------------------------------------------------------+ |
+------------------------------------------------------------------------------------------------+
```

---

## 🔢 2. Advanced Enterprise DAX Measure Suite

To build complex matrices and dynamic indicators, create a dedicated table named `_Measures` and implement these production-grade DAX formulas:

### A. B2C E-Commerce Core Metrics
* **Total B2C Sales Revenue**:
  ```dax
  B2C Total Revenue = SUM(fact_sales[line_subtotal])
  ```
* **B2C Units Sold**:
  ```dax
  B2C Units Sold = SUM(fact_sales[quantity])
  ```
* **B2C Average Order Value (AOV)**:
  ```dax
  B2C AOV = DIVIDE([B2C Total Revenue], DISTINCTCOUNT(fact_sales[order_id]), 0)
  ```
* **B2C E-Commerce Conversion Rate**:
  ```dax
  B2C Conversion Rate = DIVIDE(DISTINCTCOUNT(fact_sales[order_id]), COUNT(fact_web_traffic[session_id]), 0)
  ```
* **YoY Sales Growth %**:
  ```dax
  B2C YoY Growth % = 
  VAR CurrentSales = [B2C Total Revenue]
  VAR PriorYearSales = CALCULATE([B2C Total Revenue], SAMEPERIODLASTYEAR(dim_date[date]))
  RETURN DIVIDE(CurrentSales - PriorYearSales, PriorYearSales, 0)
  ```
* **Customer Lifetime Value (CLV)**:
  ```dax
  B2C Customer CLV = 
  DIVIDE([B2C Total Revenue], DISTINCTCOUNT(fact_sales[customer_id]), 0)
  ```
* **Active B2C Customers**:
  ```dax
  B2C Active Customers = DISTINCTCOUNT(fact_sales[customer_id])
  ```
* **Cohort Starting Customers**:
  ```dax
  B2C Cohort Starting Customers = 
  CALCULATE(
      [B2C Active Customers],
      ALLEXCEPT(fact_sales, dim_date[year], dim_date[month_name]),
      fact_sales[month_index] = 0
  )
  ```
* **Cohort Retention %**:
  ```dax
  B2C Cohort Retention % = 
  DIVIDE(
      [B2C Active Customers],
      [B2C Cohort Starting Customers],
      0
  )
  ```

### B. B2B Agency Performance Metrics
* **Total Ad Spend Managed**:
  ```dax
  B2B Managed Ad Spend = SUM(fact_ad_performance[ad_spend])
  ```
* **B2B Client Revenue Generated**:
  ```dax
  B2B Client Revenue Generated = SUM(fact_ad_performance[client_conversion_revenue])
  ```
* **B2B Overall ROAS**:
  ```dax
  B2B Managed ROAS = 
  DIVIDE(
      [B2B Client Revenue Generated], 
      [B2B Managed Ad Spend], 
      0
  )
  ```
* **B2B Cost Per Acquisition (CPA)**:
  ```dax
  B2B CPA = DIVIDE([B2B Managed Ad Spend], SUM(fact_ad_performance[conversions]), 0)
  ```
* **Monthly Retainer & Managed Ad Billing**:
  ```dax
  B2B Total Billing = SUM(fact_client_billing[total_billing_amount])
  ```
* **Account Manager Target Revenue Attainment %**:
  ```dax
  AM Target Attainment % = 
  DIVIDE(
      [B2B Total Billing], 
      SUM(dim_account_managers[target_monthly_revenue]), 
      0
  )
  ```
* **Dynamic Target Achievement Alert**:
  ```dax
  Target Status Badge = 
  VAR Attainment = [AM Target Attainment %]
  RETURN 
      IF(Attainment >= 1.0, "🏆 Target Exceeded",
      IF(Attainment >= 0.8, "🟢 Target Met",
      IF(Attainment >= 0.6, "🟡 At Risk", "🔴 Action Required")))
  ```

---

## 📈 3. Deep-Dive Corporate Visual Setup (Step-by-Step)

### Page 1: B2C E-Commerce Operational Matrix (The "Pivot" View)
Instead of a simple bar chart, Page 1 will center around a **high-density performance matrix** that lets executives slice sales and sessions dynamically:

1. **Category vs. Country Sales Matrix**:
   * **Visual**: *Matrix Visual*.
   * **Rows**: `dim_products[category]` ➡️ `dim_products[product_name]` *(Enables Drill-Down!)*.
   * **Columns**: `dim_customers[country]`.
   * **Values**: `[B2C Total Revenue]`, `[B2C Customer CLV]`.
   * **Conditional Formatting (Heatmap)**: 
     * Right-click `B2C Total Revenue` in the visual list ➡️ *Conditional Formatting* ➡️ *Background Color*.
     * Format style: *Gradient*. Select `#0A0F1D` for minimum, `#1E3A8A` for mid, and `#3B82F6` (Electric Blue) for maximum to create a beautiful corporate heat map.

2. **Customer Purchase Frequency RFM Heat Grid**:
   * **Visual**: *Matrix Visual*.
   * **Rows**: `fact_sales[r_score]` (Recency 1 to 5).
   * **Columns**: `fact_sales[f_score]` (Frequency 1 to 5).
   * **Values**: `[B2C Total Revenue]`.
   * **Conditional Formatting**: Diverging gradient from Coral/Red (low frequency) to Dark Blue/Teal (high frequency). 
   * **Interactivity**: Serves as a dynamic filter. Clicking any grid cell automatically filters the raw detail Table view at the bottom of the page.

---

### Page 2: B2B Agency Portfolio & Client Retention (The "Executive Ledger")
This page acts as the operational nerve center of the digital marketing agency:

1. **Account Manager Portfolio Drill-Down Grid**:
   * **Visual**: *Matrix Visual*.
   * **Rows Hierarchy**: `dim_account_managers[region]` ➡️ `dim_account_managers[name]` ➡️ `dim_clients[client_name]`.
   * **Values**: `[B2B Total Billing]`, `[B2B Managed Ad Spend]`, `[B2B Managed ROAS]`, `[Target Status Badge]`.
   * **Features**:
     * Expand/Collapse: The user can click `+` next to "APAC" to see all APAC managers, and click `+` next to "Michael Chang" to see his individual corporate clients and how much billing they generate.
     * KPI Badges: The `Target Status Badge` is color-coded using conditional formatting rules (Text color) so that `🔴 Action Required` instantly glows bright red.

2. **MoM Client Billing Cohort Matrix**:
   * **Visual**: *Matrix Visual*.
   * **Rows**: `client_billing_cohorts[cohort_month]` (YYYY-MM).
   * **Columns**: `client_billing_cohorts[month_index]` (0, 1, 2, 3...).
   * **Values**: `SUM(client_billing_cohorts[revenue_retention_pct])` / 100.
   * **Formatting**: Set values to Percentage (`0.0%`).
   * **Heatmap Gradient**: Format elements using background gradients scaling from `#111827` (Dark slate gray for 0%) to `#10B981` (Emerald Green for 100%+). This instantly visualizes client lifecycle longevity.

---

### Page 3: Marketing Multi-Touch Attribution & Channel ROI (The "Attribution Center")
This page tracks which marketing channels are converting traffic and generating B2B/B2C revenue:

1. **Traffic Channel Cross-Tabulation Grid**:
   * **Visual**: *Matrix Visual*.
   * **Rows**: `view_marketing_attribution[traffic_source]`.
   * **Columns**: `dim_date[year]`.
   * **Values**: `SUM(view_marketing_attribution[total_sessions])`, `AVERAGE(view_marketing_attribution[session_conversion_rate_pct])`, `SUM(view_marketing_attribution[gross_revenue])`, `AVERAGE(view_marketing_attribution[bounce_rate_pct])`.
   * **Data Bars**: Add positive teal data bars to `gross_revenue` to show channel scale.

2. **Channel Efficiency Correlation Scatter**:
   * **Visual**: *Scatter Chart*.
   * **X-Axis**: `Average session_conversion_rate_pct`.
   * **Y-Axis**: `Average bounce_rate_pct`.
   * **Legend**: `traffic_source`.
   * **Size**: `SUM(gross_revenue)`.
   * **Purpose**: Executives can immediately identify channels that convert highly (bottom right quadrant) vs. channels that represent dead spend (top left quadrant).

---

## 🎛️ 4. Collapsible Slicer & Navigation Panel
To maximize canvas space and look incredibly sleek, we build a **Collapsible Slicer Panel** utilizing Power BI Bookmarks and Selection panes:

1. **Create the Slicer Panel**:
   * Draw a vertical rectangle shape on the left side of the canvas (Color: `#111827`, Border: none, Transparency: 5%).
   * Insert slicers into this rectangle:
     * **Region Slicer**: `dim_account_managers[region]` (Format: Tile or Dropdown).
     * **Industry Slicer**: `dim_clients[industry]` (Format: Dropdown).
     * **Date Slider**: `dim_date[date]` (Format: Between).
     * **Account Manager**: `dim_account_managers[name]` (Format: Dropdown with search enabled).
2. **Setup Interactive Show/Hide Buttons**:
   * Add an icon button (e.g., "Filter" icon) at the top of the page.
   * Create two Bookmarks in the Bookmark Pane:
     * **Bookmark A**: `Slicer_Open` (Rectangle shape and slicers are set to **Visible** in Selection Pane).
     * **Bookmark B**: `Slicer_Closed` (Rectangle shape and slicers are set to **Hidden** in Selection Pane).
   * Assign the `Slicer_Open` action to your Filter button, and assign `Slicer_Closed` to a "Close" arrow inside the panel.
   * **Result**: The slicer panel smoothly glides out when clicked, allowing deep, dynamic slicing without cluttering the beautiful dashboard grid!
