#!/usr/bin/env python3
"""
Comprehensive analysis of Namecheap auction data.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Set style for better-looking plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Configuration
CSV_PATH = '/Users/daaaa/Projects/Code/OpenDomains/data/auctions/namecheap_market_sales_2026_01_01.csv'
OUTPUT_DIR = '/Users/daaaa/Projects/Code/OpenDomains/data/analysis_results'

print("=" * 80)
print("NAMECHEAP AUCTION DATA ANALYSIS")
print("=" * 80)
print(f"Loading data from: {CSV_PATH}")
print()

# Load data
print("Loading data...")
df = pd.read_csv(CSV_PATH, sep=',', quotechar='"', encoding='utf-8')
print(f"Total rows loaded: {len(df):,}")
print(f"Total columns: {len(df.columns)}")
print()

# Data cleaning and type conversion
print("Cleaning and converting data types...")

# Convert numeric columns
numeric_cols = ['price', 'startPrice', 'renewPrice', 'bidCount', 'ahrefsDomainRating',
                'umbrellaRanking', 'cloudflareRanking', 'estibotValue', 'extensionsTaken',
                'keywordSearchCount', 'lastSoldPrice', 'lastSoldYear', 'semrushAScore',
                'majesticCitation', 'ahrefsBacklinks', 'semrushBacklinks', 'majesticBacklinks',
                'majesticTrustFlow', 'goValue']

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Convert date columns (using utc=True to handle timezone awareness)
df['startDate'] = pd.to_datetime(df['startDate'], errors='coerce', utc=True)
df['endDate'] = pd.to_datetime(df['endDate'], errors='coerce', utc=True)
df['registeredDate'] = pd.to_datetime(df['registeredDate'], errors='coerce', utc=True)

# Extract TLD from domain name
df['tld'] = df['name'].str.split('.').str[-1]
df['domain_length'] = df['name'].str.split('.').str[0].str.len()

# Calculate domain age in years
df['domain_age_years'] = ((pd.Timestamp.now(tz='UTC') - df['registeredDate']).dt.days / 365.25).round(2)

# Calculate price appreciation ratio
df['price_appreciation_ratio'] = np.where(df['startPrice'] > 0, df['price'] / df['startPrice'], np.nan)

# Calculate value gaps
df['estibot_price_gap'] = df['estibotValue'] - df['price']
df['estibot_price_ratio'] = np.where(df['price'] > 0, df['estibotValue'] / df['price'], np.nan)

print("Data cleaning complete.")
print()

# ============================================================================
# 1. PRICE DISTRIBUTION ANALYSIS
# ============================================================================
print("=" * 80)
print("1. PRICE DISTRIBUTION ANALYSIS")
print("=" * 80)

# Basic statistics
print("\n--- Basic Price Statistics ---")
price_stats = df['price'].describe()
print(f"Mean Price: ${price_stats['mean']:,.2f}")
print(f"Median Price: ${price_stats['50%']:,.2f}")
print(f"Min Price: ${price_stats['min']:,.2f}")
print(f"Max Price: ${price_stats['max']:,.2f}")
print(f"Std Dev: ${price_stats['std']:,.2f}")
print(f"25th Percentile: ${price_stats['25%']:,.2f}")
print(f"75th Percentile: ${price_stats['75%']:,.2f}")

# Price range distribution
print("\n--- Price Range Distribution ---")
price_bins = [0, 1000, 5000, float('inf')]
price_labels = ['Budget (<$1k)', 'Mid ($1k-$5k)', 'Premium ($5k+)']
df['price_category'] = pd.cut(df['price'], bins=price_bins, labels=price_labels, include_lowest=True)

price_distribution = df['price_category'].value_counts().sort_index()
for category, count in price_distribution.items():
    percentage = (count / len(df)) * 100
    print(f"{category}: {count:,} domains ({percentage:.2f}%)")

# Most common price points
print("\n--- Top 10 Most Common Price Points ---")
price_counts = df['price'].value_counts().head(10)
for price, count in price_counts.items():
    print(f"${price:.2f}: {count:,} domains")

# Average start price vs current price ratio
print("\n--- Start Price vs Current Price Analysis ---")
valid_ratio = df['price_appreciation_ratio'].dropna()
print(f"Average Start Price: ${df['startPrice'].mean():,.2f}")
print(f"Average Current Price: ${df['price'].mean():,.2f}")
print(f"Average Price Appreciation Ratio: {valid_ratio.mean():.2f}x")
print(f"Median Price Appreciation Ratio: {valid_ratio.median():.2f}x")

# ============================================================================
# 2. DOMAIN QUALITY METRICS CORRELATION
# ============================================================================
print("\n" + "=" * 80)
print("2. DOMAIN QUALITY METRICS CORRELATION")
print("=" * 80)

# Calculate correlations with price
print("\n--- Correlation with Price ---")
quality_cols = ['ahrefsDomainRating', 'estibotValue', 'ahrefsBacklinks',
                'semrushBacklinks', 'majesticBacklinks', 'majesticTrustFlow',
                'domain_age_years', 'keywordSearchCount']

correlations = {}
for col in quality_cols:
    if col in df.columns:
        corr = df['price'].corr(df[col])
        correlations[col] = corr
        print(f"{col}: {corr:.4f}")

# Sort by absolute correlation
sorted_correlations = sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True)

print("\n--- Strongest Correlations with Price (Absolute) ---")
for col, corr in sorted_correlations[:5]:
    print(f"{col}: {corr:.4f}")

# Create correlation matrix for key metrics
print("\nGenerating correlation matrix visualization...")
key_metrics = ['price', 'ahrefsDomainRating', 'estibotValue', 'ahrefsBacklinks',
                'semrushBacklinks', 'majesticTrustFlow', 'domain_age_years']
corr_data = df[key_metrics].corr()

# ============================================================================
# 3. BEST VALUE OPPORTUNITIES
# ============================================================================
print("\n" + "=" * 80)
print("3. BEST VALUE OPPORTUNITIES")
print("=" * 80)

# Domains where Estibot value >> current price (undervalued)
print("\n--- Top 15 Undervalued Domains (Estibot Value >> Price) ---")
undervalued = df[df['price'] > 0].copy()
undervalued['estibot_price_ratio'] = undervalued['estibotValue'] / undervalued['price']
undervalued = undervalued[undervalued['estibotValue'] > 0]
undervalued_top = undervalued.nlargest(15, 'estibot_price_ratio')[['name', 'price', 'estibotValue', 'estibot_price_ratio', 'ahrefsDomainRating', 'ahrefsBacklinks', 'domain_age_years']]
for _, row in undervalued_top.iterrows():
    print(f"{row['name']}: Price ${row['price']:,.2f}, Estibot ${row['estibotValue']:,.2f}, Ratio {row['estibot_price_ratio']:.2f}x, DR {row['ahrefsDomainRating']}, Backlinks {row['ahrefsBacklinks']:,.0f}, Age {row['domain_age_years']:.1f}y")

# High DR domains with reasonable prices
print("\n--- Top 15 High DR Domains with Reasonable Prices (<$1000) ---")
high_dr_value = df[(df['ahrefsDomainRating'] >= 30) & (df['price'] < 1000) & (df['price'] > 0)].copy()
high_dr_value = high_dr_value.nlargest(15, 'ahrefsDomainRating')[['name', 'price', 'ahrefsDomainRating', 'ahrefsBacklinks', 'estibotValue', 'domain_age_years']]
for _, row in high_dr_value.iterrows():
    print(f"{row['name']}: Price ${row['price']:,.2f}, DR {row['ahrefsDomainRating']}, Backlinks {row['ahrefsBacklinks']:,.0f}, Estibot ${row['estibotValue']:,.2f}, Age {row['domain_age_years']:.1f}y")

# Domains with strong backlink profiles but reasonable prices
print("\n--- Top 15 Domains with Strong Backlinks & Reasonable Prices (<$1000) ---")
strong_backlinks = df[(df['ahrefsBacklinks'] >= 10000) & (df['price'] < 1000) & (df['price'] > 0)].copy()
strong_backlinks = strong_backlinks.nlargest(15, 'ahrefsBacklinks')[['name', 'price', 'ahrefsBacklinks', 'ahrefsDomainRating', 'estibotValue', 'domain_age_years']]
for _, row in strong_backlinks.iterrows():
    print(f"{row['name']}: Price ${row['price']:,.2f}, Backlinks {row['ahrefsBacklinks']:,.0f}, DR {row['ahrefsDomainRating']}, Estibot ${row['estibotValue']:,.2f}, Age {row['domain_age_years']:.1f}y")

# ============================================================================
# 4. AUCTION COMPETITIVENESS ANALYSIS
# ============================================================================
print("\n" + "=" * 80)
print("4. AUCTION COMPETITIVENESS ANALYSIS")
print("=" * 80)

# Bid count distribution
print("\n--- Bid Count Distribution ---")
bid_stats = df['bidCount'].describe()
print(f"Mean Bids: {bid_stats['mean']:.2f}")
print(f"Median Bids: {bid_stats['50%']:.2f}")
print(f"Max Bids: {int(bid_stats['max'])}")

bid_bins = [-1, 0, 1, 5, 10, 20, 50, float('inf')]
bid_labels = ['0', '1', '2-5', '6-10', '11-20', '21-50', '50+']
df['bid_category'] = pd.cut(df['bidCount'], bins=bid_bins, labels=bid_labels, include_lowest=True)
bid_distribution = df['bid_category'].value_counts().sort_index()
for category, count in bid_distribution.items():
    percentage = (count / len(df)) * 100
    print(f"{category} bids: {count:,} domains ({percentage:.2f}%)")

# Most contested auctions
print("\n--- Top 15 Most Contested Auctions (Highest Bid Counts) ---")
most_contested = df.nlargest(15, 'bidCount')[['name', 'bidCount', 'price', 'startPrice', 'ahrefsDomainRating', 'estibotValue', 'domain_age_years']]
for _, row in most_contested.iterrows():
    print(f"{row['name']}: {int(row['bidCount'])} bids, Current ${row['price']:,.2f}, Start ${row['startPrice']:,.2f}, DR {row['ahrefsDomainRating']}, Estibot ${row['estibotValue']:,.2f}, Age {row['domain_age_years']:.1f}y")

# Relationship between bid count and price
print("\n--- Bid Count vs Price Relationship ---")
bid_price_corr = df['bidCount'].corr(df['price'])
print(f"Correlation: {bid_price_corr:.4f}")

# High bid count but reasonable prices
print("\n--- Top 15 Highly Contested with Reasonable Prices (<$1000) ---")
contested_value = df[(df['bidCount'] >= 10) & (df['price'] < 1000) & (df['price'] > 0)].copy()
contested_value = contested_value.nlargest(15, 'bidCount')[['name', 'bidCount', 'price', 'ahrefsDomainRating', 'estibotValue', 'ahrefsBacklinks']]
for _, row in contested_value.iterrows():
    print(f"{row['name']}: {int(row['bidCount'])} bids, Price ${row['price']:,.2f}, DR {row['ahrefsDomainRating']}, Estibot ${row['estibotValue']:,.2f}, Backlinks {row['ahrefsBacklinks']:,.0f}")

# ============================================================================
# 5. DOMAIN CHARACTERISTICS ANALYSIS
# ============================================================================
print("\n" + "=" * 80)
print("5. DOMAIN CHARACTERISTICS ANALYSIS")
print("=" * 80)

# TLD distribution
print("\n--- Top 20 TLDs by Count ---")
tld_dist = df['tld'].value_counts().head(20)
for tld, count in tld_dist.items():
    percentage = (count / len(df)) * 100
    print(f".{tld}: {count:,} domains ({percentage:.2f}%)")

# Domain length distribution
print("\n--- Domain Length Distribution ---")
length_stats = df['domain_length'].describe()
print(f"Mean Length: {length_stats['mean']:.2f} characters")
print(f"Median Length: {int(length_stats['50%'])} characters")
print(f"Min Length: {int(length_stats['min'])} characters")
print(f"Max Length: {int(length_stats['max'])} characters")

length_bins = [0, 4, 6, 9, 13, 21, float('inf')]
length_labels = ['1-3', '4-5', '6-8', '9-12', '13-20', '20+']
df['length_category'] = pd.cut(df['domain_length'], bins=length_bins, labels=length_labels, include_lowest=True)
length_dist = df['length_category'].value_counts().sort_index()
for category, count in length_dist.items():
    percentage = (count / len(df)) * 100
    print(f"{category} chars: {count:,} domains ({percentage:.2f}%)")

# Age distribution
print("\n--- Domain Age Distribution ---")
age_stats = df['domain_age_years'].describe()
print(f"Mean Age: {age_stats['mean']:.2f} years")
print(f"Median Age: {age_stats['50%']:.2f} years")
print(f"Min Age: {age_stats['min']:.2f} years")
print(f"Max Age: {age_stats['max']:.2f} years")

age_bins = [0, 1, 3, 5, 10, 20, float('inf')]
age_labels = ['<1yr', '1-3yr', '3-5yr', '5-10yr', '10-20yr', '20+yr']
df['age_category'] = pd.cut(df['domain_age_years'], bins=age_bins, labels=age_labels, include_lowest=True, right=False)
age_dist = df['age_category'].value_counts().sort_index()
for category, count in age_dist.items():
    percentage = (count / len(df)) * 100
    print(f"{category}: {count:,} domains ({percentage:.2f}%)")

# Registration date patterns
print("\n--- Top 10 Registration Years ---")
df['reg_year'] = df['registeredDate'].dt.year
year_dist = df['reg_year'].value_counts().head(10).sort_index()
for year, count in year_dist.items():
    percentage = (count / len(df[df['reg_year'].notna()])) * 100
    print(f"{year}: {count:,} domains ({percentage:.2f}%)")

# ============================================================================
# GENERATE VISUALIZATIONS
# ============================================================================
print("\n" + "=" * 80)
print("GENERATING VISUALIZATIONS")
print("=" * 80)

import os
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Price distribution
print("\nCreating price distribution histogram...")
fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# Overall price distribution
axes[0].hist(df['price'], bins=100, edgecolor='black', alpha=0.7)
axes[0].set_xlabel('Price ($)')
axes[0].set_ylabel('Count')
axes[0].set_title('Price Distribution (All Prices)')
axes[0].set_yscale('log')
axes[0].grid(True, alpha=0.3)

# Price distribution under $5000
axes[1].hist(df[df['price'] < 5000]['price'], bins=50, edgecolor='black', alpha=0.7)
axes[1].set_xlabel('Price ($)')
axes[1].set_ylabel('Count')
axes[1].set_title('Price Distribution (< $5000)')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/price_distribution.png', dpi=150, bbox_inches='tight')
print(f"Saved: {OUTPUT_DIR}/price_distribution.png")
plt.close()

# 2. Price category distribution
print("Creating price category distribution chart...")
plt.figure(figsize=(10, 6))
price_distribution.plot(kind='bar', color='skyblue', edgecolor='black')
plt.xlabel('Price Category')
plt.ylabel('Count')
plt.title('Price Category Distribution')
plt.xticks(rotation=45)
plt.grid(True, alpha=0.3, axis='y')
for i, v in enumerate(price_distribution.values):
    plt.text(i, v + len(df)*0.01, f'{v:,}', ha='center', fontsize=9)
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/price_category_distribution.png', dpi=150, bbox_inches='tight')
print(f"Saved: {OUTPUT_DIR}/price_category_distribution.png")
plt.close()

# 3. Correlation heatmap
print("Creating correlation heatmap...")
plt.figure(figsize=(12, 10))
sns.heatmap(corr_data, annot=True, cmap='coolwarm', center=0, fmt='.3f',
            square=True, linewidths=1, cbar_kws={"shrink": 0.8})
plt.title('Correlation Matrix of Key Domain Metrics')
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/correlation_heatmap.png', dpi=150, bbox_inches='tight')
print(f"Saved: {OUTPUT_DIR}/correlation_heatmap.png")
plt.close()

# 4. Price vs Domain Rating scatter
print("Creating price vs domain rating scatter plot...")
fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# Price vs Ahrefs DR
scatter1 = axes[0].scatter(df['ahrefsDomainRating'], df['price'], alpha=0.3, s=10)
axes[0].set_xlabel('Ahrefs Domain Rating')
axes[0].set_ylabel('Price ($)')
axes[0].set_title('Price vs Ahrefs Domain Rating')
axes[0].set_yscale('log')
axes[0].grid(True, alpha=0.3)

# Price vs Estibot Value
valid_estibot = df[df['estibotValue'] > 0]
scatter2 = axes[1].scatter(valid_estibot['estibotValue'], valid_estibot['price'], alpha=0.3, s=10)
axes[1].set_xlabel('Estibot Value ($)')
axes[1].set_ylabel('Current Price ($)')
axes[1].set_title('Current Price vs Estibot Value')
axes[1].set_xscale('log')
axes[1].set_yscale('log')
axes[1].grid(True, alpha=0.3)

# Add diagonal line for reference
max_val = max(valid_estibot['estibotValue'].max(), valid_estibot['price'].max())
axes[1].plot([0, max_val], [0, max_val], 'r--', alpha=0.5, label='Equal Value')
axes[1].legend()

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/price_vs_metrics.png', dpi=150, bbox_inches='tight')
print(f"Saved: {OUTPUT_DIR}/price_vs_metrics.png")
plt.close()

# 5. Bid count distribution
print("Creating bid count distribution chart...")
plt.figure(figsize=(12, 6))
plt.hist(df['bidCount'], bins=range(0, int(df['bidCount'].max()) + 5, 5),
         edgecolor='black', alpha=0.7, color='lightcoral')
plt.xlabel('Bid Count')
plt.ylabel('Count')
plt.title('Bid Count Distribution')
plt.xlim(0, min(50, df['bidCount'].max()))
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/bid_count_distribution.png', dpi=150, bbox_inches='tight')
print(f"Saved: {OUTPUT_DIR}/bid_count_distribution.png")
plt.close()

# 6. TLD distribution
print("Creating TLD distribution chart...")
plt.figure(figsize=(14, 6))
tld_dist.head(15).plot(kind='bar', color='lightgreen', edgecolor='black')
plt.xlabel('TLD')
plt.ylabel('Count')
plt.title('Top 15 TLDs by Count')
plt.xticks(rotation=45)
plt.grid(True, alpha=0.3, axis='y')
for i, v in enumerate(tld_dist.head(15).values):
    plt.text(i, v + len(df)*0.01, f'{v:,}', ha='center', fontsize=9)
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/tld_distribution.png', dpi=150, bbox_inches='tight')
print(f"Saved: {OUTPUT_DIR}/tld_distribution.png")
plt.close()

# 7. Domain length distribution
print("Creating domain length distribution chart...")
fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# Length histogram
axes[0].hist(df['domain_length'], bins=range(1, int(df['domain_length'].max()) + 2),
             edgecolor='black', alpha=0.7, color='lightblue')
axes[0].set_xlabel('Domain Length (characters)')
axes[0].set_ylabel('Count')
axes[0].set_title('Domain Length Distribution')
axes[0].set_xlim(1, min(50, df['domain_length'].max()))
axes[0].grid(True, alpha=0.3)

# Length category bar chart
length_dist.plot(kind='bar', ax=axes[1], color='lightblue', edgecolor='black')
axes[1].set_xlabel('Length Category')
axes[1].set_ylabel('Count')
axes[1].set_title('Domain Length Category Distribution')
axes[1].tick_params(axis='x', rotation=45)
axes[1].grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/domain_length_distribution.png', dpi=150, bbox_inches='tight')
print(f"Saved: {OUTPUT_DIR}/domain_length_distribution.png")
plt.close()

# 8. Domain age distribution
print("Creating domain age distribution chart...")
fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# Age histogram
axes[0].hist(df['domain_age_years'].dropna(), bins=30, edgecolor='black', alpha=0.7, color='orange')
axes[0].set_xlabel('Domain Age (years)')
axes[0].set_ylabel('Count')
axes[0].set_title('Domain Age Distribution')
axes[0].grid(True, alpha=0.3)

# Age category bar chart
age_dist.plot(kind='bar', ax=axes[1], color='orange', edgecolor='black')
axes[1].set_xlabel('Age Category')
axes[1].set_ylabel('Count')
axes[1].set_title('Domain Age Category Distribution')
axes[1].tick_params(axis='x', rotation=45)
axes[1].grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/domain_age_distribution.png', dpi=150, bbox_inches='tight')
print(f"Saved: {OUTPUT_DIR}/domain_age_distribution.png")
plt.close()

# 9. Backlinks distribution
print("Creating backlinks distribution chart...")
fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# Ahrefs backlinks
valid_ahrefs = df[df['ahrefsBacklinks'] > 0]
axes[0].hist(np.log10(valid_ahrefs['ahrefsBacklinks'] + 1), bins=50, edgecolor='black', alpha=0.7, color='purple')
axes[0].set_xlabel('Log10(Ahrefs Backlinks)')
axes[0].set_ylabel('Count')
axes[0].set_title('Ahrefs Backlinks Distribution (Log Scale)')
axes[0].grid(True, alpha=0.3)

# Backlinks vs Price
valid_price_backlinks = df[(df['ahrefsBacklinks'] > 0) & (df['price'] > 0)]
axes[1].scatter(np.log10(valid_price_backlinks['ahrefsBacklinks'] + 1),
                valid_price_backlinks['price'], alpha=0.3, s=10)
axes[1].set_xlabel('Log10(Ahrefs Backlinks)')
axes[1].set_ylabel('Price ($)')
axes[1].set_title('Price vs Ahrefs Backlinks')
axes[1].set_yscale('log')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/backlinks_analysis.png', dpi=150, bbox_inches='tight')
print(f"Saved: {OUTPUT_DIR}/backlinks_analysis.png")
plt.close()

# 10. Bid count vs Price
print("Creating bid count vs price scatter plot...")
plt.figure(figsize=(10, 6))
valid_bid_price = df[(df['bidCount'] > 0) & (df['price'] > 0)]
plt.scatter(valid_bid_price['bidCount'], valid_bid_price['price'], alpha=0.3, s=10)
plt.xlabel('Bid Count')
plt.ylabel('Price ($)')
plt.title('Price vs Bid Count')
plt.xlim(0, min(50, valid_bid_price['bidCount'].max()))
plt.yscale('log')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/bid_count_vs_price.png', dpi=150, bbox_inches='tight')
print(f"Saved: {OUTPUT_DIR}/bid_count_vs_price.png")
plt.close()

print("\nAll visualizations saved successfully!")

# ============================================================================
# SAVE DETAILED REPORT
# ============================================================================
print("\n" + "=" * 80)
print("SAVING DETAILED REPORT")
print("=" * 80)

report_path = f'{OUTPUT_DIR}/comprehensive_analysis_report.txt'

with open(report_path, 'w', encoding='utf-8') as f:
    f.write("=" * 100 + "\n")
    f.write("NAMECHEAP AUCTION DATA - COMPREHENSIVE ANALYSIS REPORT\n")
    f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Total Domains Analyzed: {len(df):,}\n")
    f.write("=" * 100 + "\n\n")

    # Section 1
    f.write("1. PRICE DISTRIBUTION ANALYSIS\n")
    f.write("-" * 100 + "\n")
    f.write(f"\nBasic Price Statistics:\n")
    f.write(f"  Mean Price: ${price_stats['mean']:,.2f}\n")
    f.write(f"  Median Price: ${price_stats['50%']:,.2f}\n")
    f.write(f"  Min Price: ${price_stats['min']:,.2f}\n")
    f.write(f"  Max Price: ${price_stats['max']:,.2f}\n")
    f.write(f"  Standard Deviation: ${price_stats['std']:,.2f}\n")
    f.write(f"  25th Percentile: ${price_stats['25%']:,.2f}\n")
    f.write(f"  75th Percentile: ${price_stats['75%']:,.2f}\n")

    f.write(f"\nPrice Range Distribution:\n")
    for category, count in price_distribution.items():
        percentage = (count / len(df)) * 100
        f.write(f"  {category}: {count:,} domains ({percentage:.2f}%)\n")

    f.write(f"\nTop 10 Most Common Price Points:\n")
    for price, count in price_counts.items():
        f.write(f"  ${price:.2f}: {count:,} domains\n")

    f.write(f"\nStart Price vs Current Price Analysis:\n")
    f.write(f"  Average Start Price: ${df['startPrice'].mean():,.2f}\n")
    f.write(f"  Average Current Price: ${df['price'].mean():,.2f}\n")
    f.write(f"  Average Price Appreciation Ratio: {valid_ratio.mean():.2f}x\n")
    f.write(f"  Median Price Appreciation Ratio: {valid_ratio.median():.2f}x\n")

    # Section 2
    f.write("\n\n2. DOMAIN QUALITY METRICS CORRELATION\n")
    f.write("-" * 100 + "\n")
    f.write(f"\nCorrelation with Price:\n")
    for col, corr in correlations.items():
        f.write(f"  {col}: {corr:.4f}\n")

    f.write(f"\nStrongest Correlations with Price (Absolute):\n")
    for col, corr in sorted_correlations[:5]:
        f.write(f"  {col}: {corr:.4f}\n")

    # Section 3
    f.write("\n\n3. BEST VALUE OPPORTUNITIES\n")
    f.write("-" * 100 + "\n")

    f.write(f"\nTop 15 Undervalued Domains (Estibot Value >> Price):\n")
    f.write(f"{'Domain':<40} {'Price':>12} {'Estibot':>12} {'Ratio':>8} {'DR':>5} {'Backlinks':>12} {'Age':>6}\n")
    f.write("-" * 100 + "\n")
    for _, row in undervalued_top.iterrows():
        f.write(f"{row['name']:<40} ${row['price']:>10,.2f}  ${row['estibotValue']:>10,.2f}  {row['estibot_price_ratio']:>6.2f}x  {row['ahrefsDomainRating']:>3}  {row['ahrefsBacklinks']:>10,.0f}  {row['domain_age_years']:>4.1f}y\n")

    f.write(f"\nTop 15 High DR Domains with Reasonable Prices (<$1000):\n")
    f.write(f"{'Domain':<40} {'Price':>12} {'DR':>5} {'Backlinks':>12} {'Estibot':>12} {'Age':>6}\n")
    f.write("-" * 100 + "\n")
    for _, row in high_dr_value.iterrows():
        f.write(f"{row['name']:<40} ${row['price']:>10,.2f}  {row['ahrefsDomainRating']:>3}  {row['ahrefsBacklinks']:>10,.0f}  ${row['estibotValue']:>10,.2f}  {row['domain_age_years']:>4.1f}y\n")

    f.write(f"\nTop 15 Domains with Strong Backlinks & Reasonable Prices (<$1000):\n")
    f.write(f"{'Domain':<40} {'Price':>12} {'Backlinks':>12} {'DR':>5} {'Estibot':>12} {'Age':>6}\n")
    f.write("-" * 100 + "\n")
    for _, row in strong_backlinks.iterrows():
        f.write(f"{row['name']:<40} ${row['price']:>10,.2f}  {row['ahrefsBacklinks']:>10,.0f}  {row['ahrefsDomainRating']:>3}  ${row['estibotValue']:>10,.2f}  {row['domain_age_years']:>4.1f}y\n")

    # Section 4
    f.write("\n\n4. AUCTION COMPETITIVENESS ANALYSIS\n")
    f.write("-" * 100 + "\n")
    f.write(f"\nBid Count Statistics:\n")
    f.write(f"  Mean Bids: {bid_stats['mean']:.2f}\n")
    f.write(f"  Median Bids: {bid_stats['50%']:.2f}\n")
    f.write(f"  Max Bids: {int(bid_stats['max'])}\n")

    f.write(f"\nBid Count Distribution:\n")
    for category, count in bid_distribution.items():
        percentage = (count / len(df)) * 100
        f.write(f"  {category} bids: {count:,} domains ({percentage:.2f}%)\n")

    f.write(f"\nBid Count vs Price Relationship:\n")
    f.write(f"  Correlation: {bid_price_corr:.4f}\n")

    f.write(f"\nTop 15 Most Contested Auctions (Highest Bid Counts):\n")
    f.write(f"{'Domain':<40} {'Bids':>6} {'Price':>12} {'Start':>12} {'DR':>5} {'Estibot':>12} {'Age':>6}\n")
    f.write("-" * 100 + "\n")
    for _, row in most_contested.iterrows():
        f.write(f"{row['name']:<40} {int(row['bidCount']):>4}  ${row['price']:>10,.2f}  ${row['startPrice']:>10,.2f}  {row['ahrefsDomainRating']:>3}  ${row['estibotValue']:>10,.2f}  {row['domain_age_years']:>4.1f}y\n")

    f.write(f"\nTop 15 Highly Contested with Reasonable Prices (<$1000):\n")
    f.write(f"{'Domain':<40} {'Bids':>6} {'Price':>12} {'DR':>5} {'Estibot':>12} {'Backlinks':>12}\n")
    f.write("-" * 100 + "\n")
    for _, row in contested_value.iterrows():
        f.write(f"{row['name']:<40} {int(row['bidCount']):>4}  ${row['price']:>10,.2f}  {row['ahrefsDomainRating']:>3}  ${row['estibotValue']:>10,.2f}  {row['ahrefsBacklinks']:>10,.0f}\n")

    # Section 5
    f.write("\n\n5. DOMAIN CHARACTERISTICS ANALYSIS\n")
    f.write("-" * 100 + "\n")

    f.write(f"\nTop 20 TLDs by Count:\n")
    for tld, count in tld_dist.items():
        percentage = (count / len(df)) * 100
        f.write(f"  .{tld}: {count:,} domains ({percentage:.2f}%)\n")

    f.write(f"\nDomain Length Statistics:\n")
    f.write(f"  Mean Length: {length_stats['mean']:.2f} characters\n")
    f.write(f"  Median Length: {int(length_stats['50%'])} characters\n")
    f.write(f"  Min Length: {int(length_stats['min'])} characters\n")
    f.write(f"  Max Length: {int(length_stats['max'])} characters\n")

    f.write(f"\nDomain Length Distribution:\n")
    for category, count in length_dist.items():
        percentage = (count / len(df)) * 100
        f.write(f"  {category} chars: {count:,} domains ({percentage:.2f}%)\n")

    f.write(f"\nDomain Age Statistics:\n")
    f.write(f"  Mean Age: {age_stats['mean']:.2f} years\n")
    f.write(f"  Median Age: {age_stats['50%']:.2f} years\n")
    f.write(f"  Min Age: {age_stats['min']:.2f} years\n")
    f.write(f"  Max Age: {age_stats['max']:.2f} years\n")

    f.write(f"\nDomain Age Distribution:\n")
    for category, count in age_dist.items():
        percentage = (count / len(df)) * 100
        f.write(f"  {category}: {count:,} domains ({percentage:.2f}%)\n")

    f.write(f"\nTop 10 Registration Years:\n")
    for year, count in year_dist.items():
        percentage = (count / len(df[df['reg_year'].notna()])) * 100
        f.write(f"  {year}: {count:,} domains ({percentage:.2f}%)\n")

    # Summary and Key Findings
    f.write("\n\n6. KEY FINDINGS AND ACTIONABLE INSIGHTS\n")
    f.write("-" * 100 + "\n")

    # Price insights
    f.write(f"\nPrice Insights:\n")
    f.write(f"  • The median price of ${price_stats['50%']:,.2f} suggests most domains are accessible\n")
    f.write(f"  • Premium domains ($5k+) represent {price_distribution.get('Premium ($5k+)', 0)/len(df)*100:.2f}% of the market\n")
    f.write(f"  • Average price appreciation is {valid_ratio.mean():.1f}x from start price, indicating active bidding\n")

    # Quality correlations
    f.write(f"\nQuality Metrics Correlation:\n")
    strongest_metric = sorted_correlations[0] if sorted_correlations else (None, 0)
    f.write(f"  • {strongest_metric[0]} has the strongest correlation with price ({strongest_metric[1]:.4f})\n")
    if 'estibotValue' in correlations:
        estibot_corr = correlations['estibotValue']
        f.write(f"  • Estibot Value correlation of {estibot_corr:.4f} suggests moderate pricing accuracy\n")
    if 'ahrefsDomainRating' in correlations:
        dr_corr = correlations['ahrefsDomainRating']
        f.write(f"  • Domain Rating correlation of {dr_corr:.4f} indicates SEO value impacts pricing\n")

    # Value opportunities
    f.write(f"\nValue Opportunities:\n")
    f.write(f"  • Found {len(undervalued_top)} domains with high Estibot-to-price ratios indicating potential undervaluation\n")
    f.write(f"  • {len(high_dr_value)} high DR domains under $1000 offer strong SEO value at reasonable prices\n")
    f.write(f"  • {len(strong_backlinks)} domains with strong backlink profiles priced under $1000 represent good opportunities\n")

    # Competitiveness
    f.write(f"\nAuction Competitiveness:\n")
    f.write(f"  • Average of {bid_stats['mean']:.1f} bids per domain indicates moderate competition\n")
    f.write(f"  • Maximum of {int(bid_stats['max'])} bids shows some highly contested auctions\n")
    f.write(f"  • Bid count to price correlation of {bid_price_corr:.4f} indicates {'some' if abs(bid_price_corr) > 0.3 else 'limited'} relationship between competition and price\n")

    # Domain characteristics
    f.write(f"\nDomain Characteristics:\n")
    top_tld = tld_dist.index[0] if len(tld_dist) > 0 else 'N/A'
    f.write(f"  • .{top_tld} is the dominant TLD with {tld_dist.iloc[0]:,} domains ({tld_dist.iloc[0]/len(df)*100:.1f}% of market)\n")
    f.write(f"  • Median domain length of {int(length_stats['50%'])} characters suggests preference for concise names\n")
    f.write(f"  • Median age of {age_stats['50%']:.1f} years indicates mix of established and newer domains\n")

    f.write("\n" + "=" * 100 + "\n")
    f.write("END OF REPORT\n")
    f.write("=" * 100 + "\n")

print(f"Report saved to: {report_path}")

# ============================================================================
# SAVE TOP OPPORTUNITIES CSV
# ============================================================================
print("\n" + "=" * 80)
print("SAVING TOP OPPORTUNITIES CSV")
print("=" * 80)

# Combine all opportunity domains
opportunities = pd.DataFrame()

# Undervalued
undervalued_export = undervalued_top.copy()
undervalided_export = undervalued_export[['name', 'price', 'estibotValue', 'estibot_price_ratio',
                                            'ahrefsDomainRating', 'ahrefsBacklinks', 'domain_age_years']]
undervalided_export['opportunity_type'] = 'Undervalued (High Estibot Ratio)'
opportunities = pd.concat([opportunities, undervalided_export], ignore_index=True)

# High DR
high_dr_export = high_dr_value.copy()
high_dr_export = high_dr_export[['name', 'price', 'ahrefsDomainRating', 'ahrefsBacklinks',
                                 'estibotValue', 'domain_age_years']]
high_dr_export['opportunity_type'] = 'High DR Under $1k'
opportunities = pd.concat([opportunities, high_dr_export], ignore_index=True)

# Strong backlinks
strong_backlinks_export = strong_backlinks.copy()
strong_backlinks_export = strong_backlinks_export[['name', 'price', 'ahrefsBacklinks',
                                                    'ahrefsDomainRating', 'estibotValue', 'domain_age_years']]
strong_backlinks_export['opportunity_type'] = 'Strong Backlinks Under $1k'
opportunities = pd.concat([opportunities, strong_backlinks_export], ignore_index=True)

# Most contested
contested_export = most_contested.copy()
contested_export = contested_export[['name', 'bidCount', 'price', 'startPrice',
                                     'ahrefsDomainRating', 'estibotValue', 'domain_age_years']]
contested_export['opportunity_type'] = 'Most Contested'
opportunities = pd.concat([opportunities, contested_export], ignore_index=True)

# Highly contested reasonable price
contested_value_export = contested_value.copy()
contested_value_export = contested_value_export[['name', 'bidCount', 'price', 'ahrefsDomainRating',
                                                  'estibotValue', 'ahrefsBacklinks']]
contested_value_export['opportunity_type'] = 'Contested Value Under $1k'
opportunities = pd.concat([opportunities, contested_value_export], ignore_index=True)

opportunities_path = f'{OUTPUT_DIR}/top_opportunities.csv'
opportunities.to_csv(opportunities_path, index=False, encoding='utf-8')
print(f"Top opportunities saved to: {opportunities_path}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("ANALYSIS COMPLETE!")
print("=" * 80)
print(f"\nAll outputs saved to: {OUTPUT_DIR}/")
print("  • comprehensive_analysis_report.txt - Full detailed report")
print("  • top_opportunities.csv - Combined list of all opportunity domains")
print("  • price_distribution.png - Price distribution visualizations")
print("  • price_category_distribution.png - Price category breakdown")
print("  • correlation_heatmap.png - Correlation matrix of key metrics")
print("  • price_vs_metrics.png - Price vs Domain Rating and Estibot Value")
print("  • bid_count_distribution.png - Bid count distribution")
print("  • tld_distribution.png - TLD distribution")
print("  • domain_length_distribution.png - Domain length analysis")
print("  • domain_age_distribution.png - Domain age analysis")
print("  • backlinks_analysis.png - Backlinks distribution and correlation")
print("  • bid_count_vs_price.png - Bid count vs price relationship")
print("\nTotal domains analyzed: {:,}".format(len(df)))
print("Analysis completed successfully!")
print("=" * 80)
