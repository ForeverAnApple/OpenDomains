#!/usr/bin/env python3
"""Analyze auction domains to find undervalued gems (supports Namecheap and GoDaddy CSV formats)."""

import argparse
import csv
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from src.scoring.scorer import DomainScorer

# Default CSV file path (can be overridden with --csv argument)
DEFAULT_AUCTION_CSV = Path("data/auctions/namecheap_market_sales_2026_01_01.csv")

# Column mapping for different CSV formats
NAMECHEAP_COLUMNS = {
    'name': 'name',
    'price': 'price',
    'estibotValue': 'estibotValue',
    'goValue': 'goValue',
    'ahrefsDomainRating': 'ahrefsDomainRating',
    'ahrefsBacklinks': 'ahrefsBacklinks',
    'majesticTrustFlow': 'majesticTrustFlow',
    'bidCount': 'bidCount',
}

GODADDY_COLUMNS = {
    'Domain Name': 'name',
    'Price': 'price',
    'Estimated Value': 'estibotValue',
    'Majestic TF': 'majesticTrustFlow',
    'Backlinks': 'ahrefsBacklinks',
    'Bids': 'bidCount',
}

# Tacky/cringe patterns to filter out (case-insensitive)
TACKY_PATTERNS = [
    'juicer', 'hub', 'ninja', 'guru', 'master', 'pro', 'zone', 'spot', 'lab', 'hq',
    'ify', 'io$',  # io suffix
    'techy', 'startup', 'growth', 'hack', 'buddy', 'pal', 'mate',
    'boost', 'rocket', 'rocket$', 'blast', 'fire', 'fire$', 'explosive',
    'awesome', 'epic', 'super', 'ultra', 'mega', 'hyper', 'turbo',
    'wiz', 'whiz', 'expert', 'ace', 'champ', 'hero', 'star',
    'works', 'systems', 'solutions', 'services', 'company',
]

# Industry-specific patterns to filter out (avoid overly specific niches)
INDUSTRY_PATTERNS = [
    'health', 'pharma', 'medic', 'medical', 'wellness', 'fitness',
    'crypto', 'bitcoin', 'blockchain', 'trading', 'forex',
    'invest', 'finance', 'financial', 'banking',
    'insurance', 'realestate', 'realtor', 'property',
    'legal', 'lawyer', 'attorney', 'attorneys',
    'accounting', 'tax', 'taxes',
]

# Elegant suffixes that add premium feel
ELEGANT_SUFFIXES = ['ia$', 'a$', 'o$', 'e$', 'y$', 'i$']
ELEGANT_PATTERNS = ['on$', 'or$', 'ar$', 'er$', 'el$', 'et$']


def parse_price(value: str) -> float:
    """Parse price from string (may include $ sign)."""
    if not value or value.strip() == '':
        return 0.0
    try:
        return float(str(value).replace('$', '').replace(',', '').strip())
    except (ValueError, AttributeError):
        return 0.0


def matches_any_pattern(domain: str, patterns: list[str]) -> bool:
    """Check if domain matches any of the given patterns."""
    domain_lower = domain.lower()
    for pattern in patterns:
        if pattern.endswith('$'):
            # Exact suffix match
            if domain_lower.endswith(pattern[:-1]):
                return True
        else:
            # Contains match
            if pattern in domain_lower:
                return True
    return False


def calculate_elegance_bonus(domain: str) -> float:
    """Calculate elegance bonus score based on name characteristics."""
    domain_name = domain.rsplit('.', 1)[0].lower()  # Remove TLD
    bonus = 0.0

    # Bonus for short length (5-8 chars ideal)
    length = len(domain_name)
    if 5 <= length <= 8:
        bonus += 10.0
    elif 4 <= length <= 9:
        bonus += 5.0
    elif length <= 10:
        bonus += 2.0

    # Bonus for elegant suffixes
    for suffix in ELEGANT_SUFFIXES:
        if domain_name.endswith(suffix[:-1]):
            bonus += 5.0
            break

    # Bonus for elegant patterns
    for pattern in ELEGANT_PATTERNS:
        if domain_name.endswith(pattern[:-1]):
            bonus += 3.0
            break

    # Bonus for being a single word (no hyphens or numbers)
    if '-' not in domain_name and not any(c.isdigit() for c in domain_name):
        bonus += 5.0

    return bonus


def has_awkward_patterns(domain_name: str) -> bool:
    """Check for awkward consonant clusters and repeated consonants."""
    # Check for 3+ consecutive consonants
    consecutive_consonants = 0
    for char in domain_name:
        if char.lower() in 'bcdfghjklmnpqrstvwxyz':
            consecutive_consonants += 1
            if consecutive_consonants >= 3:
                return True
        else:
            consecutive_consonants = 0

    # Check for double letters that look weird (except common doubles like ll, tt, ss, ee)
    weird_doubles = ['bb', 'cc', 'dd', 'ff', 'gg', 'hh', 'jj', 'kk', 'mm', 'nn', 'pp', 'qq', 'rr', 'vv', 'ww', 'xx', 'yy', 'zz']
    for double in weird_doubles:
        if double in domain_name:
            return True

    # Check for 3+ of the same consonant (e.g., 'aaa' would be caught as 3 consonants if 'a' is considered vowel, but this is for consonants)
    from collections import Counter
    char_count = Counter(domain_name)
    for char, count in char_count.items():
        if char.lower() in 'bcdfghjklmnpqrstvwxyz' and count >= 3:
            return True

    return False


def has_brandable_ending(domain_name: str) -> bool:
    """Check if domain has elegant, brandable ending."""
    brandable_endings = ['a', 'o', 'i', 'er', 'ly', 'ia', 'io', 'al', 'en', 'ar', 'el', 'um']
    for ending in brandable_endings:
        if domain_name.endswith(ending):
            return True
    return False


def detect_csv_format(headers: list[str]) -> str:
    """Detect CSV format based on column headers."""
    header_set = set(h.strip() for h in headers)
    namecheap_headers = set(NAMECHEAP_COLUMNS.keys())
    godaddy_headers = set(GODADDY_COLUMNS.keys())

    # Check for exact matches
    if header_set >= namecheap_headers:
        return 'namecheap'
    elif header_set >= godaddy_headers:
        return 'godaddy'

    # Fallback: check for key identifying columns
    if 'Domain Name' in header_set:
        return 'godaddy'
    elif 'name' in header_set:
        return 'namecheap'

    return 'unknown'


def normalize_row(row: dict, format: str) -> dict:
    """Normalize row data to internal field names based on format."""
    normalized = {}

    if format == 'namecheap':
        column_map = NAMECHEAP_COLUMNS
    elif format == 'godaddy':
        column_map = GODADDY_COLUMNS
    else:
        return row

    # Map columns according to format
    for csv_col, internal_col in column_map.items():
        if csv_col in row:
            normalized[internal_col] = row[csv_col]

    # Set defaults for missing fields
    defaults = {
        'estibotValue': '0',
        'goValue': '0',
        'ahrefsDomainRating': '0',
        'ahrefsBacklinks': '0',
        'majesticTrustFlow': '0',
        'bidCount': '0',
    }

    for field, default_value in defaults.items():
        if field not in normalized:
            normalized[field] = default_value

    return normalized


def analyze_auctions(
    csv_path: Optional[Path] = None,
    min_score: float = 0,
    max_price: Optional[float] = None,
    top_n: int = 20,
    limit: Optional[int] = None,
    vibe: Optional[str] = None,
    max_length: Optional[int] = None,
    real_words: bool = False,
    tld_filter: Optional[str] = None
) -> list[dict]:
    """Analyze auction domains and identify undervalued gems."""
    console = Console()

    # Use provided path or default
    csv_file = csv_path if csv_path else DEFAULT_AUCTION_CSV

    if not csv_file.exists():
        console.print(f"[red]Error: CSV file not found at {csv_file}[/red]")
        sys.exit(1)

    scorer = DomainScorer()

    # Load English words dictionary if real_words or brandable filter is enabled
    english_words: Optional[set[str]] = None
    if real_words or vibe == 'brandable':
        dict_path = Path("data/wordlists/english_words.txt")
        if dict_path.exists():
            with open(dict_path, 'r', encoding='utf-8') as f:
                english_words = set(word.strip().lower() for word in f if word.strip())
            console.print(f"[green]Loaded {len(english_words):,} English words from dictionary[/green]")
        else:
            console.print(f"[yellow]Warning: Dictionary file not found at {dict_path}, skipping real-words filter[/yellow]")

    # Parse TLD filter if provided
    allowed_tlds: Optional[set[str]] = None
    if tld_filter:
        allowed_tlds = set(t.strip().lower() for t in tld_filter.split(','))

    results = []

    # Detect CSV format
    with open(csv_file, 'r', encoding='utf-8') as f:
        # Read first line to detect format
        first_line = f.readline().strip()
        headers = first_line.split(',')

    csv_format = detect_csv_format(headers)
    console.print(f"[green]Detected CSV format: {csv_format.upper()}[/green]")

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Scoring domains...", total=None)
            count = 0

            for row in reader:
                # Normalize row data to internal field names
                normalized_row = normalize_row(row, csv_format)

                domain = normalized_row.get('name', '').strip()
                if not domain:
                    continue

                # Check limit
                count += 1
                if limit is not None and count > limit:
                    break

                # Update progress periodically
                if count % 1000 == 0:
                    progress.update(task, description=f"Scoring domains... ({count:,} processed)")

                # Extract TLD and domain name (without TLD)
                if '.' not in domain:
                    continue
                domain_name = domain.rsplit('.', 1)[0].lower()
                domain_tld = domain.rsplit('.', 1)[1].lower()

                # Filter by TLD if specified
                if allowed_tlds and domain_tld not in allowed_tlds:
                    continue

                # Filter by max length if specified
                if max_length is not None and len(domain_name) > max_length:
                    continue

                # Filter by real English words if specified
                if real_words and english_words and domain_name not in english_words:
                    continue

                # Parse price and valuation fields from normalized row
                price = parse_price(normalized_row.get('price', ''))
                estibot_value = parse_price(normalized_row.get('estibotValue', ''))
                go_value = parse_price(normalized_row.get('goValue', ''))
                ahrefs_rating = parse_price(normalized_row.get('ahrefsDomainRating', ''))
                ahrefs_backlinks = parse_price(normalized_row.get('ahrefsBacklinks', ''))
                majestic_trust = parse_price(normalized_row.get('majesticTrustFlow', ''))
                bid_count = parse_price(normalized_row.get('bidCount', ''))

                # Skip if price is 0 or negative
                if price <= 0:
                    continue

                # Score the domain
                score_result = scorer.score(domain)
                quality_score = score_result.total_score

                # Apply vibe-based filtering
                if vibe:
                    # Filter out tacky patterns for elegant/neutral vibes
                    if vibe in ['elegant', 'neutral']:
                        if matches_any_pattern(domain, TACKY_PATTERNS):
                            continue
                        if matches_any_pattern(domain, INDUSTRY_PATTERNS):
                            continue

                        # Apply elegance bonus
                        quality_score += calculate_elegance_bonus(domain)

                    # Tech vibe: prefer tech-related names (less filtering)
                    elif vibe == 'tech':
                        # Tech vibe allows tech names but filters out very tacky ones
                        pass

                    # Brandable vibe: made-up words that feel like real startup names
                    elif vibe == 'brandable':
                        # Filter out real dictionary words (we want made-up words!)
                        if english_words and domain_name in english_words:
                            continue

                        # Require high pronounceability
                        if score_result.pronounceability < 75:
                            continue

                        # Prefer short names (5-8 chars ideal, max 10)
                        if len(domain_name) > 10:
                            continue

                        # Filter out tacky and industry patterns
                        if matches_any_pattern(domain, TACKY_PATTERNS):
                            continue
                        if matches_any_pattern(domain, INDUSTRY_PATTERNS):
                            continue

                        # Filter out names with numbers or hyphens
                        if '-' in domain_name or any(c.isdigit() for c in domain_name):
                            continue

                        # Filter out awkward consonant patterns
                        if has_awkward_patterns(domain_name):
                            continue

                        # Boost score for brandable endings
                        if has_brandable_ending(domain_name):
                            quality_score += 8.0

                        # Bonus for short (5-8 chars is ideal)
                        if 5 <= len(domain_name) <= 8:
                            quality_score += 10.0
                        elif len(domain_name) <= 10:
                            quality_score += 5.0

                # Skip if below minimum score threshold
                if quality_score < min_score:
                    continue

                # Skip if over maximum price
                if max_price is not None and price > max_price:
                    continue

                # Calculate value ratio (quality per dollar)
                # Higher ratio = better deal (more quality per dollar)
                value_ratio = quality_score / price if price > 0 else 0

                # Calculate potential upside (valuation vs current price)
                # Use highest available valuation
                max_valuation = max(estibot_value, go_value)
                if max_valuation > 0:
                    upside_potential = (max_valuation - price) / price * 100
                else:
                    upside_potential = 0

                results.append({
                    'domain': domain,
                    'price': price,
                    'quality_score': quality_score,
                    'value_ratio': value_ratio,
                    'value_ratio_display': f"{value_ratio:.4f}",
                    'estibot_value': estibot_value,
                    'go_value': go_value,
                    'upside_potential': upside_potential,
                    'ahrefs_rating': ahrefs_rating,
                    'ahrefs_backlinks': ahrefs_backlinks,
                    'majestic_trust': majestic_trust,
                    'bid_count': bid_count,
                    'tld_multiplier': score_result.tld_multiplier,
                    'pronounceability': score_result.pronounceability,
                    'brandability': score_result.brandability,
                    'memorability': score_result.memorability,
                })

            progress.update(task, description=f"Scoring domains... completed ({count:,} processed)")

    # Sort by value ratio (descending) to find best deals
    results.sort(key=lambda x: x['value_ratio'], reverse=True)

    # Return top N results
    return results[:top_n]


def display_results(results: list[dict], show_details: bool = False):
    """Display results in a formatted table."""
    console = Console()

    if not results:
        console.print("[yellow]No domains found matching criteria[/yellow]")
        return

    # Main results table
    table = Table(title="Top Undervalued Domain Gems", show_header=True, header_style="bold magenta")
    table.add_column("Domain", style="cyan", width=30)
    table.add_column("Price", justify="right", width=10)
    table.add_column("Quality", justify="center", width=8)
    table.add_column("Value Ratio", justify="center", width=12)
    table.add_column("Estibot", justify="right", width=10)
    table.add_column("GoValue", justify="right", width=10)
    table.add_column("Upside %", justify="right", width=10)
    table.add_column("DR", justify="center", width=5)
    table.add_column("BL", justify="center", width=8)

    for result in results:
        price_str = f"${result['price']:,.0f}"
        quality_str = f"{result['quality_score']:.1f}"

        # Color code value ratio
        ratio = result['value_ratio']
        if ratio > 0.05:
            ratio_style = "[bold green]"
        elif ratio > 0.02:
            ratio_style = "[yellow]"
        else:
            ratio_style = ""

        ratio_str = f"{ratio_style}{result['value_ratio_display']}[/]" if ratio_style else result['value_ratio_display']

        # Upside potential
        upside = result['upside_potential']
        if upside > 0:
            upside_str = f"[green]+{upside:.0f}%[/]"
        else:
            upside_str = f"[red]{upside:.0f}%[/]"

        estibot_str = f"${result['estibot_value']:,.0f}" if result['estibot_value'] > 0 else "-"
        govalue_str = f"${result['go_value']:,.0f}" if result['go_value'] > 0 else "-"

        dr_str = f"{result['ahrefs_rating']:.0f}" if result['ahrefs_rating'] > 0 else "-"
        bl_str = f"{result['ahrefs_backlinks']:,.0f}" if result['ahrefs_backlinks'] > 0 else "-"

        table.add_row(
            result['domain'],
            price_str,
            quality_str,
            ratio_str,
            estibot_str,
            govalue_str,
            upside_str,
            dr_str,
            bl_str
        )

    console.print(table)

    # Print summary stats
    console.print("\n[bold]Summary Statistics:[/bold]")
    avg_price = sum(r['price'] for r in results) / len(results)
    avg_quality = sum(r['quality_score'] for r in results) / len(results)

    # Calculate average upside potential (handle case when all are 0)
    positive_upside = [r['upside_potential'] for r in results if r['upside_potential'] > 0]
    if positive_upside:
        avg_upside = sum(positive_upside) / len(positive_upside)
        console.print(f"  Average upside potential: +{avg_upside:.0f}%")
    else:
        console.print("  Average upside potential: N/A (no valuation data)")

    # Detailed breakdown if requested
    if show_details and len(results) > 0:
        console.print("\n[bold]Top Domain Details:[/bold]")
        top = results[0]
        detail_table = Table(show_header=True)
        detail_table.add_column("Metric", style="cyan")
        detail_table.add_column("Value")

        detail_table.add_row("Domain", top['domain'])
        detail_table.add_row("Price", f"${top['price']:,.0f}")
        detail_table.add_row("Quality Score", f"{top['quality_score']:.2f}")
        detail_table.add_row("Value Ratio", f"{top['value_ratio']:.6f}")
        detail_table.add_row("TLD Multiplier", f"{top['tld_multiplier']:.2f}x")
        detail_table.add_row("Pronounceability", f"{top['pronounceability']}/100")
        detail_table.add_row("Brandability", f"{top['brandability']}/100")
        detail_table.add_row("Memorability", f"{top['memorability']}/100")

        if top['estibot_value'] > 0:
            detail_table.add_row("Estibot Value", f"${top['estibot_value']:,.0f}")
        if top['go_value'] > 0:
            detail_table.add_row("GoValue", f"${top['go_value']:,.0f}")
        if top['ahrefs_rating'] > 0:
            detail_table.add_row("Ahrefs DR", f"{top['ahrefs_rating']:.0f}")
        if top['ahrefs_backlinks'] > 0:
            detail_table.add_row("Ahrefs Backlinks", f"{top['ahrefs_backlinks']:,.0f}")
        if top['majestic_trust'] > 0:
            detail_table.add_row("Majestic Trust Flow", f"{top['majestic_trust']:.0f}")
        if top['bid_count'] > 0:
            detail_table.add_row("Bid Count", f"{top['bid_count']:.0f}")

        console.print(detail_table)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze auction domains to find undervalued gems (supports Namecheap and GoDaddy CSV formats)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
 Examples:
   # Show top 20 undervalued domains
   python analyze_auctions.py

   # Analyze GoDaddy auction CSV
   python analyze_auctions.py --csv data/auctions/gd_auctions_export.csv

   # Find domains with quality score >= 60 and price <= $500
   python analyze_auctions.py --min-score 60 --max-price 500

   # Show top 50 results with detailed breakdown
   python analyze_auctions.py --top 50 --details

   # Filter for elegant, premium names (notion, linear, vercel style)
   python analyze_auctions.py --vibe elegant

     # Filter for neutral names, avoiding tacky patterns
     python analyze_auctions.py --vibe neutral

     # Filter for brandable made-up words (figma, vercel, supabase style)
     python analyze_auctions.py --vibe brandable

     # Filter for short real English words (max 7 chars, .com only)
     python analyze_auctions.py --real-words --max-length 7 --tld com

    # Filter for short real words across multiple TLDs
    python analyze_auctions.py --real-words --max-length 5 --tld com,io,net
        """
    )

    parser.add_argument(
        '--min-score',
        type=float,
        default=50.0,
        help='Minimum quality score (default: 50.0)'
    )

    parser.add_argument(
        '--max-price',
        type=float,
        default=None,
        help='Maximum price filter (default: no limit)'
    )

    parser.add_argument(
        '--top',
        type=int,
        default=20,
        help='Number of top results to show (default: 20)'
    )

    parser.add_argument(
        '--details',
        action='store_true',
        help='Show detailed breakdown of top domain'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit processing to N domains for testing (default: process all)'
    )

    parser.add_argument(
        '--vibe',
        type=str,
        choices=['elegant', 'neutral', 'tech', 'brandable'],
        default=None,
        help='Filter by name vibe (default: no filter). '
             'elegant: short, clean, premium names (notion, linear, vercel style). '
             'neutral: avoid tacky patterns and industry-specific names. '
             'tech: tech-focused names with minimal filtering. '
             'brandable: made-up words that feel premium (figma, vercel, supabase style) - short, pronounceable, not real words.'
    )

    parser.add_argument(
        '--max-length',
        type=int,
        default=None,
        help='Maximum domain name length (excluding TLD) (default: no limit)'
    )

    parser.add_argument(
        '--real-words',
        action='store_true',
        help='Filter to only real English dictionary words from data/wordlists/english_words.txt'
    )

    parser.add_argument(
        '--tld',
        type=str,
        default=None,
        help='Filter by TLD (comma-separated, e.g. "com" or "com,io") (default: all TLDs)'
    )

    parser.add_argument(
        '--csv',
        type=str,
        default=None,
        help=f'Path to CSV file (default: {DEFAULT_AUCTION_CSV})'
    )

    args = parser.parse_args()

    # Resolve CSV path
    csv_path = Path(args.csv) if args.csv else DEFAULT_AUCTION_CSV

    console = Console()
    console.print(f"[bold]Analyzing auction domains from:[/bold] {csv_path}")
    console.print(f"  Min quality score: {args.min_score}")
    console.print(f"  Max price: ${args.max_price if args.max_price else 'no limit'}")
    console.print(f"  Top results: {args.top}")
    console.print(f"  Vibe filter: {args.vibe if args.vibe else 'none'}")
    if args.max_length:
        console.print(f"  Max length: {args.max_length} chars")
    if args.real_words:
        console.print(f"  Real words only: yes")
    if args.tld:
        console.print(f"  TLD filter: {args.tld}")
    if args.limit:
        console.print(f"  Processing limit: {args.limit:,} domains")
    console.print("")

    results = analyze_auctions(
        csv_path=csv_path,
        min_score=args.min_score,
        max_price=args.max_price,
        top_n=args.top,
        limit=args.limit,
        vibe=args.vibe,
        max_length=args.max_length,
        real_words=args.real_words,
        tld_filter=args.tld
    )

    display_results(results, show_details=args.details)


if __name__ == "__main__":
    main()
