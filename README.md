# Datahut Data Science Internship Assignment

## Web Scraping & Pricing Analysis — adidas India Men's Footwear

An end-to-end data science project that collects product data from the adidas India Men's Footwear catalogue, cleans and validates the dataset, and analyses pricing and discount patterns.

The project covers three stages:

1. Web scraping and pagination
2. Data cleaning and validation
3. Pricing and discount analysis

---

## Repository Structure

```text
Datahut-Science-Assignment/
│
├── scraper.py
├── clean.ipynb
├── analysis.ipynb
│
├── products_raw.csv
├── products_clean.csv
├── pricing_outliers.csv
├── validation_report.txt
│
├── charts/
│   ├── chart1_discount_tiers.png
│   ├── chart2_subbrand_comparison.png
│   └── chart3_price_tier_discount.png
│
├── requirements.txt
└── README.md
```

---

## Setup

### Requirements

* Python 3.10+
* Google Chrome
* Chrome DevTools Protocol enabled for the scraping step

Install the required Python libraries:

```bash
pip install -r requirements.txt
```

The main libraries used are:

* `playwright` — browser connection and page navigation
* `pandas` — data cleaning and analysis
* `numpy` — numerical operations
* `scipy` — statistical analysis
* `matplotlib` — data visualization

---

# Problem 1 — Web Scraping

## Approach

Initial testing showed that direct automated requests to the adidas India website were blocked with HTTP 403 responses. Standard automated browser sessions were also unreliable.

To handle this, the scraper connects to an existing Chrome browser session through the Chrome DevTools Protocol (CDP).

The scraper then:

1. Connects to the open adidas India browser tab.
2. Captures the HTML document response through a Playwright response listener.
3. Extracts the structured `__NEXT_DATA__` JSON embedded in the page HTML.
4. Reads product data and pagination information from this structured data.
5. Dynamically discovers the total product count and page size.
6. Continues through the catalogue using `?start=N` pagination offsets.
7. Adds a 2.5-second delay between page loads.
8. Logs navigation and parsing failures.
9. Saves the collected data to `products_raw.csv`.

The scraper does not hard-code the expected catalogue size.

## Price Handling

The product data contains a `priceData.prices` array.

The scraper handles the two observed cases separately:

* **Discounted product:** sale price and original price are stored separately.
* **Full-price product:** the single available price is used for both sale price and MRP.

This prevents full-price and discounted products from being mixed or interpreted incorrectly.

## How to Run

Start Chrome with remote debugging enabled:

```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\chrome_debug"
```

Open the following page in that Chrome window:

```text
https://www.adidas.co.in/men-shoes
```

After the page loads, run:

```bash
python scraper.py
```

The output is saved as:

```text
products_raw.csv
```

---

# Problem 2 — Data Cleaning and Validation

The raw scraped data is cleaned and validated in `clean.ipynb`.

## Cleaning Steps

The notebook:

1. Loads and inspects the raw dataset.
2. Checks duplicate product IDs and URLs.
3. Removes duplicate products based on product URL if present.
4. Converts price columns to numeric values.
5. Creates:

   * `discount_amount = mrp - sale_price`
   * `discount_pct = discount_amount / mrp × 100`
6. Checks for impossible cases where sale price is greater than MRP.
7. Checks for missing names, prices, and URLs.
8. Counts discounted and full-price products.
9. Saves the cleaned dataset and validation report.

## Data Quality Results

| Metric                      |        Result |
| --------------------------- | ------------: |
| Raw products                |         1,671 |
| Duplicate product IDs       |             0 |
| Duplicate product URLs      |             0 |
| Clean products              |         1,671 |
| Missing critical fields     |             0 |
| Sale price greater than MRP |             0 |
| Discounted products         | 1,400 (83.8%) |
| Full-price products         |   271 (16.2%) |

The cleaned dataset is saved as `products_clean.csv`.

---

# Problem 3 — Pricing and Discount Analysis

The analysis in `analysis.ipynb` examines discount structure, sub-brand behaviour, price tiers, and unusual pricing patterns.

## Key Findings

### 1. Discounts follow clear fixed tiers

Discounts are strongly concentrated at a few levels.

| Discount | Products |
| -------- | -------: |
| 30%      |      283 |
| 35%      |        4 |
| 40%      |      146 |
| 50%      |      962 |
| 60%      |        5 |

The **50% discount tier dominates**, accounting for most discounted products.

This suggests that adidas uses standard discount levels across the catalogue rather than setting a different discount percentage for every product.

---

### 2. Originals follows a different discount pattern

| Sub-brand   | Products | On Sale | Median Discount |
| ----------- | -------: | ------: | --------------: |
| Originals   |      200 |   62.5% |             30% |
| Performance |      858 |   87.6% |             50% |
| Sportswear  |      536 |   84.1% |             50% |
| TERREX      |       77 |   93.5% |             50% |

Originals is discounted less frequently and at a lower typical depth than the other sub-brands.

This suggests that Originals follows a more conservative discounting pattern, while Performance, Sportswear, and TERREX use deeper and more frequent discounts.

---

### 3. Premium products show more conservative discounting

Products were divided into four price tiers using MRP quartiles.

The Premium tier has a lower share of products on sale and a lower median discount than the other tiers.

The Pearson correlation between MRP and discount percentage is:

```text
r = -0.242
```

This shows a **weak negative relationship**.

Higher-priced products tend to receive slightly smaller percentage discounts, but the relationship is weak. Therefore, MRP alone is not a strong predictor of discount depth.

The correlation is statistically significant, but its practical strength remains weak.

---

### 4. No pricing outliers were detected

Pricing outliers were checked using the IQR method within each sub-brand.

The peer groups were defined by sub-brand because different product lines may follow different pricing and discount patterns.

For each group:

```text
Lower Fence = Q1 - 1.5 × IQR
Upper Fence = Q3 + 1.5 × IQR
```

No products in the current dataset fell outside these sub-brand-specific discount fences.

Therefore, `pricing_outliers.csv` contains no flagged products. This is a valid result of the selected statistical method rather than a processing error.

---

## Visualizations

Three charts were created to support the main findings:

| Chart                            | Purpose                                                           |
| -------------------------------- | ----------------------------------------------------------------- |
| `chart1_discount_tiers.png`      | Shows the distribution of products across discount levels         |
| `chart2_subbrand_comparison.png` | Compares sale participation and median discount across sub-brands |
| `chart3_price_tier_discount.png` | Compares discount behaviour across MRP price tiers                |

The charts are saved in the `charts/` directory.

---

## Challenges and Decisions

| Challenge                                                 | Approach                                                         |
| --------------------------------------------------------- | ---------------------------------------------------------------- |
| Automated HTTP requests returned HTTP 403                 | Used an existing Chrome session through CDP                      |
| Standard automated browser access was unreliable          | Connected Playwright to the CDP-enabled Chrome session           |
| Product data needed to be extracted reliably              | Parsed structured `__NEXT_DATA__` JSON embedded in the HTML      |
| Catalogue size could change                               | Discovered total count and page size dynamically                 |
| Multiple price states                                     | Handled full-price and discounted products separately            |
| Duplicate risk during pagination                          | Checked product ID and URL uniqueness during cleaning            |
| Comparing pricing outliers across different product lines | Applied IQR fences separately within each sub-brand              |
| Weak statistical relationship                             | Reported the correlation strength without overstating the result |

---

## Assumptions and Limitations

* The analysis represents a **single snapshot** of the adidas India Men's Footwear catalogue.
* Discount patterns may change during seasonal promotions, clearance periods, or other sale events.
* The analysis covers one product category and one regional website.
* Product availability and prices may change after the data collection date.
* The dataset does not include sales volume, inventory levels, product age, cost, or profit-margin data.
* The analysis identifies pricing patterns and statistical relationships but does not prove the business reasons behind them.
* The outlier results depend on the chosen peer group and IQR-based method.

---

## Final Summary

The analysis shows that discounting in the adidas India Men's Footwear catalogue is highly structured, with **50% off as the dominant promotional tier**.

Discount behaviour also differs across product lines. **Originals is discounted less frequently and less deeply**, while Performance, Sportswear, and TERREX show more aggressive discounting.

Premium-priced products show some signs of more conservative discounting, but the overall relationship between MRP and discount percentage is weak.

The project demonstrates a complete workflow from web data collection to validation, statistical analysis, visualization, and business interpretation.
